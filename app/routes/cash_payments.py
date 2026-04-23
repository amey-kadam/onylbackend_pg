import random
import string
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant, TenantStatus
from app.models.payment import Payment, PaymentStatus
from app.models.cash_payment_request import CashPaymentRequest, CashRequestStatus
from app.models.pg import PG
from app.schemas.cash_payment import (
    CashPaymentInitiate, CashPaymentVerify,
    CashPaymentRequestResponse, StaffListResponse,
)
from app.models.pg_staff import PGStaff
from app.utils.dependencies import get_current_user, require_owner, require_owner_or_staff
from datetime import date

router = APIRouter(prefix="/api/cash-payments", tags=["Cash Payments"])


def _gen_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))


def _build_request_response(req: CashPaymentRequest, include_otp: bool = False) -> CashPaymentRequestResponse:
    tenant_name = None
    if req.tenant and req.tenant.user:
        tenant_name = req.tenant.user.name
    receiver_name = req.receiver.name if req.receiver else None
    return CashPaymentRequestResponse(
        id=req.id,
        tenant_id=req.tenant_id,
        tenant_name=tenant_name,
        receiver_user_id=req.receiver_user_id,
        receiver_name=receiver_name,
        amount=req.amount,
        month_year=req.month_year,
        otp=req.otp if include_otp else None,
        status=req.status.value,
        notes=req.notes,
        expires_at=req.expires_at,
        created_at=req.created_at,
    )


@router.get("/staff", response_model=List[StaffListResponse])
def get_staff_list(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Tenant calls this to see who they can pay cash to (PG owners)."""
    if current_user.role != UserRole.TENANT:
        raise HTTPException(status_code=403, detail="Only tenants can list staff")

    tenant = db.query(Tenant).filter(
        Tenant.user_id == current_user.id,
        Tenant.status == TenantStatus.ACTIVE,
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant profile not found")

    pg = db.query(PG).filter(PG.id == tenant.pg_id).first()
    if not pg:
        raise HTTPException(status_code=404, detail="PG not found")

    owner = db.query(User).filter(User.id == pg.owner_id).first()
    result = []
    if owner:
        result.append(StaffListResponse(id=owner.id, name=owner.name, phone=owner.phone, role=owner.role.value))

    # Also include actual staff members assigned to this PG
    staff_records = db.query(PGStaff).filter(PGStaff.pg_id == tenant.pg_id).all()
    for sr in staff_records:
        if sr.user:
            result.append(StaffListResponse(id=sr.user.id, name=sr.user.name, phone=sr.user.phone, role=sr.user.role.value))

    return result


@router.post("/initiate", response_model=CashPaymentRequestResponse, status_code=status.HTTP_201_CREATED)
def initiate_cash_payment(
    data: CashPaymentInitiate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tenant initiates a cash payment request. OTP is generated and sent to owner."""
    if current_user.role != UserRole.TENANT:
        raise HTTPException(status_code=403, detail="Only tenants can initiate cash payments")

    tenant = db.query(Tenant).filter(
        Tenant.user_id == current_user.id,
        Tenant.status == TenantStatus.ACTIVE,
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant profile not found")

    pg = db.query(PG).filter(PG.id == tenant.pg_id).first()
    if not pg:
        raise HTTPException(status_code=404, detail="PG not found")

    # Receiver must be the PG owner or assigned staff
    is_owner = pg.owner_id == data.receiver_user_id
    is_staff = db.query(PGStaff).filter(
        PGStaff.pg_id == pg.id, PGStaff.user_id == data.receiver_user_id
    ).first() is not None
    if not (is_owner or is_staff):
        raise HTTPException(status_code=400, detail="Invalid receiver — must be your PG owner or staff")

    otp = _gen_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    req = CashPaymentRequest(
        tenant_id=tenant.id,
        receiver_user_id=data.receiver_user_id,
        amount=data.amount,
        month_year=data.month_year,
        otp=otp,
        status=CashRequestStatus.PENDING,
        notes=data.notes,
        expires_at=expires_at,
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    return _build_request_response(req, include_otp=False)


@router.post("/verify", response_model=dict)
def verify_cash_payment(
    data: CashPaymentVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tenant submits OTP they received from staff to confirm the payment."""
    if current_user.role != UserRole.TENANT:
        raise HTTPException(status_code=403, detail="Only tenants can verify cash payments")

    tenant = db.query(Tenant).filter(
        Tenant.user_id == current_user.id,
        Tenant.status == TenantStatus.ACTIVE,
    ).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant profile not found")

    req = db.query(CashPaymentRequest).filter(
        CashPaymentRequest.id == data.request_id,
        CashPaymentRequest.tenant_id == tenant.id,
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Cash payment request not found")

    if req.status != CashRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Request is already {req.status.value}")

    now = datetime.now(timezone.utc)
    if req.expires_at.tzinfo is None:
        expires_at = req.expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = req.expires_at

    if now > expires_at:
        req.status = CashRequestStatus.EXPIRED
        db.commit()
        raise HTTPException(status_code=400, detail="OTP has expired. Please initiate a new request.")

    if req.otp != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    # OTP correct — create the payment record
    payment = Payment(
        tenant_id=tenant.id,
        amount=req.amount,
        status=PaymentStatus.PAID,
        payment_date=date.today(),
        month_year=req.month_year,
        notes=req.notes or "Cash payment verified via OTP",
        payment_method="cash",
        collected_by_user_id=req.receiver_user_id,
    )
    db.add(payment)

    req.status = CashRequestStatus.VERIFIED
    db.commit()

    return {"message": "Payment verified and recorded successfully", "payment_id": payment.id if payment.id else None}


@router.get("/pending", response_model=List[CashPaymentRequestResponse])
def get_pending_requests(
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner_or_staff),
):
    """Owner or staff sees pending cash payment requests addressed to them (with OTPs)."""
    requests = db.query(CashPaymentRequest).filter(
        CashPaymentRequest.receiver_user_id == owner.id,
        CashPaymentRequest.status == CashRequestStatus.PENDING,
    ).order_by(CashPaymentRequest.created_at.desc()).all()

    return [_build_request_response(r, include_otp=True) for r in requests]


@router.get("/history", response_model=List[CashPaymentRequestResponse])
def get_request_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get cash payment request history for the current user."""
    if current_user.role == UserRole.TENANT:
        tenant = db.query(Tenant).filter(Tenant.user_id == current_user.id).first()
        if not tenant:
            return []
        requests = db.query(CashPaymentRequest).filter(
            CashPaymentRequest.tenant_id == tenant.id
        ).order_by(CashPaymentRequest.created_at.desc()).all()
    else:
        requests = db.query(CashPaymentRequest).filter(
            CashPaymentRequest.receiver_user_id == current_user.id
        ).order_by(CashPaymentRequest.created_at.desc()).all()

    return [_build_request_response(r, include_otp=(current_user.role != UserRole.TENANT)) for r in requests]
