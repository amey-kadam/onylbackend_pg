from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.config import get_settings
from app.models.client_subscription import ClientSubscription
from app.models.user import User, UserRole
from app.models.pg import PG
from app.schemas.client_subscription import (
    ClientSubscriptionCreate,
    ClientSubscriptionUpdate,
    ClientSubscriptionResponse,
    ClientInfo,
    FeatureFlags,
    SaasStatsResponse,
)

router = APIRouter(prefix="/api/admin/saas", tags=["SaaS Admin"])


# ── Admin Login ───────────────────────────────────────────────────────────────

class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    token: str
    email: str
    message: str


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(data: AdminLoginRequest):
    """Authenticate the SaaS super-admin. Credentials come from server .env."""
    settings = get_settings()
    if data.email != settings.SAAS_ADMIN_EMAIL or data.password != settings.SAAS_ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    # Return a simple static token derived from the secret — no expiry for now.
    import hashlib, hmac
    token = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        f"saas_admin:{data.email}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return AdminLoginResponse(token=token, email=data.email, message="Admin login successful")


def _verify_admin_token(token: str) -> bool:
    """Verify a previously issued admin token."""
    import hashlib, hmac
    settings = get_settings()
    expected = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        f"saas_admin:{settings.SAAS_ADMIN_EMAIL}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(token, expected)


def _build_features(sub: ClientSubscription) -> FeatureFlags:
    return FeatureFlags(
        rent_management=sub.feature_rent_management,
        complaint_management=sub.feature_complaint_management,
        visitor_entry=sub.feature_visitor_entry,
        staff_management=sub.feature_staff_management,
        expense_tracking=sub.feature_expense_tracking,
        analytics=sub.feature_analytics,
        email_alerts=sub.feature_email_alerts,
        whatsapp_alerts=sub.feature_whatsapp_alerts,
        notice_board=sub.feature_notice_board,
        maintenance_tracking=sub.feature_maintenance_tracking,
    )


def _apply_features(sub: ClientSubscription, flags: FeatureFlags):
    sub.feature_rent_management = flags.rent_management
    sub.feature_complaint_management = flags.complaint_management
    sub.feature_visitor_entry = flags.visitor_entry
    sub.feature_staff_management = flags.staff_management
    sub.feature_expense_tracking = flags.expense_tracking
    sub.feature_analytics = flags.analytics
    sub.feature_email_alerts = flags.email_alerts
    sub.feature_whatsapp_alerts = flags.whatsapp_alerts
    sub.feature_notice_board = flags.notice_board
    sub.feature_maintenance_tracking = flags.maintenance_tracking


def _plan_defaults(plan: str) -> FeatureFlags:
    """Return the default feature set for a given plan."""
    if plan == "basic":
        return FeatureFlags(
            rent_management=True, complaint_management=True, notice_board=True,
            maintenance_tracking=True, visitor_entry=False, staff_management=False,
            expense_tracking=False, analytics=False, email_alerts=False, whatsapp_alerts=False,
        )
    if plan == "standard":
        return FeatureFlags(
            rent_management=True, complaint_management=True, notice_board=True,
            maintenance_tracking=True, staff_management=True, visitor_entry=True,
            expense_tracking=False, analytics=False, email_alerts=True, whatsapp_alerts=False,
        )
    if plan == "premium":
        return FeatureFlags(
            rent_management=True, complaint_management=True, notice_board=True,
            maintenance_tracking=True, staff_management=True, visitor_entry=True,
            expense_tracking=True, analytics=True, email_alerts=True, whatsapp_alerts=True,
        )
    # custom — all on by default
    return FeatureFlags(
        rent_management=True, complaint_management=True, notice_board=True,
        maintenance_tracking=True, staff_management=True, visitor_entry=True,
        expense_tracking=True, analytics=True, email_alerts=True, whatsapp_alerts=True,
    )


def _to_response(sub: ClientSubscription, db: Session) -> ClientSubscriptionResponse:
    user = db.query(User).filter(User.id == sub.user_id).first()
    pgs = db.query(PG).filter(PG.owner_id == sub.user_id).all()
    pg_name = pgs[0].name if pgs else None
    return ClientSubscriptionResponse(
        id=sub.id,
        user_id=sub.user_id,
        plan=sub.plan,
        status=sub.status,
        expiry_date=sub.expiry_date,
        notes=sub.notes,
        features=_build_features(sub),
        created_at=sub.created_at,
        updated_at=sub.updated_at,
        client=ClientInfo(
            id=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            pg_name=pg_name,
            pg_count=len(pgs),
        ),
    )


@router.get("/stats", response_model=SaasStatsResponse)
def get_saas_stats(db: Session = Depends(get_db)):
    """Overview stats for the SaaS admin dashboard."""
    subs = db.query(ClientSubscription).all()
    enabled = 0
    for s in subs:
        flags = _build_features(s)
        enabled += sum([
            flags.rent_management, flags.complaint_management, flags.visitor_entry,
            flags.staff_management, flags.expense_tracking, flags.analytics,
            flags.email_alerts, flags.whatsapp_alerts, flags.notice_board,
            flags.maintenance_tracking,
        ])
    return SaasStatsResponse(
        total_clients=len(subs),
        active_clients=sum(1 for s in subs if s.status == "active"),
        expired_clients=sum(1 for s in subs if s.status == "expired"),
        suspended_clients=sum(1 for s in subs if s.status == "suspended"),
        trial_clients=sum(1 for s in subs if s.status == "trial"),
        basic_plan=sum(1 for s in subs if s.plan == "basic"),
        standard_plan=sum(1 for s in subs if s.plan == "standard"),
        premium_plan=sum(1 for s in subs if s.plan == "premium"),
        custom_plan=sum(1 for s in subs if s.plan == "custom"),
        total_features_enabled=enabled,
    )


@router.get("/clients", response_model=List[ClientSubscriptionResponse])
def list_clients(
    search: Optional[str] = None,
    plan: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all owner clients with their subscriptions; auto-create if missing."""
    owners = db.query(User).filter(User.role == UserRole.OWNER).all()

    # Auto-provision subscriptions for owners that don't have one yet
    for owner in owners:
        existing = db.query(ClientSubscription).filter(ClientSubscription.user_id == owner.id).first()
        if not existing:
            sub = ClientSubscription(user_id=owner.id)
            _apply_features(sub, _plan_defaults("basic"))
            db.add(sub)
    db.commit()

    query = db.query(ClientSubscription).join(User, ClientSubscription.user_id == User.id)
    if plan:
        query = query.filter(ClientSubscription.plan == plan)
    if status:
        query = query.filter(ClientSubscription.status == status)
    if search:
        term = f"%{search}%"
        query = query.filter(User.name.ilike(term) | User.email.ilike(term) | User.phone.ilike(term))

    subs = query.all()
    return [_to_response(s, db) for s in subs]


@router.get("/clients/{user_id}", response_model=ClientSubscriptionResponse)
def get_client(user_id: int, db: Session = Depends(get_db)):
    sub = db.query(ClientSubscription).filter(ClientSubscription.user_id == user_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return _to_response(sub, db)


@router.post("/clients", response_model=ClientSubscriptionResponse)
def create_client_subscription(data: ClientSubscriptionCreate, db: Session = Depends(get_db)):
    existing = db.query(ClientSubscription).filter(ClientSubscription.user_id == data.user_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Subscription already exists for this user")
    sub = ClientSubscription(
        user_id=data.user_id,
        plan=data.plan,
        status=data.status,
        expiry_date=data.expiry_date,
        notes=data.notes,
    )
    _apply_features(sub, data.features)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _to_response(sub, db)


@router.put("/clients/{user_id}", response_model=ClientSubscriptionResponse)
def update_client_subscription(user_id: int, data: ClientSubscriptionUpdate, db: Session = Depends(get_db)):
    sub = db.query(ClientSubscription).filter(ClientSubscription.user_id == user_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    if data.plan is not None:
        sub.plan = data.plan
    if data.status is not None:
        sub.status = data.status
    if data.expiry_date is not None:
        sub.expiry_date = data.expiry_date
    if data.notes is not None:
        sub.notes = data.notes
    if data.features is not None:
        _apply_features(sub, data.features)
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return _to_response(sub, db)


@router.put("/clients/{user_id}/apply-plan", response_model=ClientSubscriptionResponse)
def apply_plan_defaults(user_id: int, plan: str, db: Session = Depends(get_db)):
    """Apply default feature set for a plan (resets custom toggles to plan defaults)."""
    if plan not in ("basic", "standard", "premium", "custom"):
        raise HTTPException(status_code=400, detail="Invalid plan name")
    sub = db.query(ClientSubscription).filter(ClientSubscription.user_id == user_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    sub.plan = plan
    _apply_features(sub, _plan_defaults(plan))
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return _to_response(sub, db)


@router.delete("/clients/{user_id}")
def delete_client_subscription(user_id: int, db: Session = Depends(get_db)):
    sub = db.query(ClientSubscription).filter(ClientSubscription.user_id == user_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    db.delete(sub)
    db.commit()
    return {"detail": "Subscription removed"}
