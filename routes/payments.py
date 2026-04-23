from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.payment import Payment, PaymentStatus
from app.models.tenant import Tenant
from app.models.pg import PG
from app.schemas.payment import PaymentCreate, PaymentResponse, PaymentListResponse
from app.models.pg_staff import PGStaff
from app.utils.dependencies import get_current_user, require_owner, require_owner_or_staff

router = APIRouter(prefix="/api/payments", tags=["Payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(data: PaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Record a payment. Owner can record any, Tenant can record pending for themselves."""
    tenant = db.query(Tenant).filter(Tenant.id == data.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if current_user.role == UserRole.TENANT:
        if tenant.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to submit payment for another tenant")
        if data.status != "pending":
            raise HTTPException(status_code=403, detail="Tenants can only submit pending payments")

    payment = Payment(
        tenant_id=data.tenant_id,
        amount=data.amount,
        status=PaymentStatus(data.status),
        payment_date=data.payment_date or date.today(),
        month_year=data.month_year,
        notes=data.notes,
        payment_method=data.payment_method or "cash",
        collected_by_user_id=data.collected_by_user_id,
        transaction_id=data.transaction_id,
        screenshot_path=data.screenshot_path,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return _build_payment_response(payment)


@router.get("/{tenant_id}", response_model=PaymentListResponse)
def get_payments(
    tenant_id: int,
    month_year: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get payment history for a tenant."""
    # Authorization: owner can see any, tenant can see own
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if current_user.role == UserRole.TENANT and tenant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    query = db.query(Payment).filter(Payment.tenant_id == tenant_id)
    if month_year:
        query = query.filter(Payment.month_year == month_year)

    payments = query.order_by(Payment.created_at.desc()).all()

    _refund_types = {"deposit_refund", "deposit"}
    total_collected = sum(p.amount for p in payments if p.status == PaymentStatus.PAID and getattr(p, 'payment_type', None) not in _refund_types)
    total_pending = sum(p.amount for p in payments if p.status in [PaymentStatus.UNPAID, PaymentStatus.PARTIAL])
    total_refunded = sum(p.amount for p in payments if getattr(p, 'payment_type', None) == "deposit_refund")

    return PaymentListResponse(
        payments=[_build_payment_response(p) for p in payments],
        total=len(payments),
        total_collected=total_collected,
        total_pending=total_pending,
        total_refunded=total_refunded,
    )


@router.get("", response_model=PaymentListResponse)
def list_all_payments(
    month_year: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    pg_id: Optional[int] = None,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner_or_staff),
):
    """List all payments across all tenants. Owner or staff."""
    if owner.role.value == "staff":
        staff_pg_ids = [r.pg_id for r in db.query(PGStaff).filter(PGStaff.user_id == owner.id).all()]
        query = db.query(Payment).join(Payment.tenant).filter(Tenant.pg_id.in_(staff_pg_ids))
    else:
        query = db.query(Payment).join(Payment.tenant).join(Tenant.pg).filter(PG.owner_id == owner.id)

    if month_year:
        query = query.filter(Payment.month_year == month_year)
    if status_filter:
        query = query.filter(Payment.status == PaymentStatus(status_filter))
    if pg_id:
        query = query.filter(Tenant.pg_id == pg_id)

    payments = query.order_by(Payment.created_at.desc()).all()

    _refund_types = {"deposit_refund", "deposit"}
    total_collected = sum(p.amount for p in payments if p.status == PaymentStatus.PAID and getattr(p, 'payment_type', None) not in _refund_types)
    total_pending = sum(p.amount for p in payments if p.status in [PaymentStatus.UNPAID, PaymentStatus.PARTIAL])
    total_refunded = sum(p.amount for p in payments if getattr(p, 'payment_type', None) == "deposit_refund")

    return PaymentListResponse(
        payments=[_build_payment_response(p) for p in payments],
        total=len(payments),
        total_collected=total_collected,
        total_pending=total_pending,
        total_refunded=total_refunded,
    )


def _build_payment_response(p: Payment) -> PaymentResponse:
    from app.models.user import User as UserModel
    tenant_name = None
    if p.tenant and p.tenant.user:
        tenant_name = p.tenant.user.name
    collected_by = None
    if getattr(p, 'collected_by_user_id', None):
        from app.database import SessionLocal
        db2 = SessionLocal()
        try:
            u = db2.query(UserModel).filter(UserModel.id == p.collected_by_user_id).first()
            if u:
                collected_by = u.name
        finally:
            db2.close()
    return PaymentResponse(
        id=p.id,
        tenant_id=p.tenant_id,
        tenant_name=tenant_name,
        amount=p.amount,
        status=p.status.value,
        payment_date=p.payment_date,
        month_year=p.month_year,
        notes=p.notes,
        payment_method=getattr(p, 'payment_method', 'cash'),
        collected_by=collected_by,
        transaction_id=getattr(p, 'transaction_id', None),
        screenshot_path=getattr(p, 'screenshot_path', None),
        payment_type=getattr(p, 'payment_type', None),
        created_at=p.created_at,
    )
