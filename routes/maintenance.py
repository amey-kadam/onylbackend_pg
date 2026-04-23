from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from app.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant, TenantStatus
from app.models.pg import PG
from app.models.maintenance_bill import MaintenanceBill, MaintenanceStatus
from app.schemas.maintenance_bill import (
    MaintenanceBillCreate, MaintenanceBillUpdate,
    MaintenanceBillResponse, MaintenanceBillListResponse,
)
from app.utils.dependencies import get_current_user, require_owner

router = APIRouter(prefix="/api/maintenance", tags=["Maintenance"])


def _build_response(m: MaintenanceBill) -> MaintenanceBillResponse:
    tenant_name = None
    if m.tenant and m.tenant.user:
        tenant_name = m.tenant.user.name
    return MaintenanceBillResponse(
        id=m.id, pg_id=m.pg_id, tenant_id=m.tenant_id,
        tenant_name=tenant_name, title=m.title,
        description=m.description, amount=m.amount,
        due_date=m.due_date, status=m.status.value,
        month_year=m.month_year, created_at=m.created_at,
    )


@router.post("", response_model=MaintenanceBillResponse, status_code=status.HTTP_201_CREATED)
def create_bill(data: MaintenanceBillCreate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Create a maintenance bill. Owner only."""
    pg = db.query(PG).filter(PG.id == data.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=404, detail="PG not found")

    bill = MaintenanceBill(
        pg_id=data.pg_id,
        tenant_id=data.tenant_id,
        title=data.title,
        description=data.description,
        amount=data.amount,
        due_date=data.due_date,
        month_year=data.month_year,
        status=MaintenanceStatus.PENDING,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return _build_response(bill)


@router.get("", response_model=MaintenanceBillListResponse)
def list_bills(
    pg_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    bill_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List maintenance bills. Owners see all; tenants see their own."""
    query = db.query(MaintenanceBill)

    if current_user.role == UserRole.TENANT:
        tenant = db.query(Tenant).filter(
            Tenant.user_id == current_user.id,
            Tenant.status == TenantStatus.ACTIVE,
        ).first()
        if not tenant:
            return MaintenanceBillListResponse(bills=[], total=0, total_pending=0.0, total_paid=0.0)
        query = query.filter(
            (MaintenanceBill.tenant_id == tenant.id) | (MaintenanceBill.pg_id == tenant.pg_id)
        )
    else:
        if pg_id:
            query = query.filter(MaintenanceBill.pg_id == pg_id)
        if tenant_id:
            query = query.filter(MaintenanceBill.tenant_id == tenant_id)

    if bill_status:
        query = query.filter(MaintenanceBill.status == MaintenanceStatus(bill_status))

    bills = query.order_by(MaintenanceBill.created_at.desc()).all()
    responses = [_build_response(b) for b in bills]

    total_pending = sum(b.amount for b in bills if b.status == MaintenanceStatus.PENDING)
    total_paid = sum(b.amount for b in bills if b.status == MaintenanceStatus.PAID)

    return MaintenanceBillListResponse(
        bills=responses, total=len(bills),
        total_pending=total_pending, total_paid=total_paid,
    )


@router.put("/{bill_id}", response_model=MaintenanceBillResponse)
def update_bill(bill_id: int, data: MaintenanceBillUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Update a maintenance bill. Owner only."""
    bill = db.query(MaintenanceBill).filter(MaintenanceBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    pg = db.query(PG).filter(PG.id == bill.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=403, detail="Not authorized")

    if data.title is not None:
        bill.title = data.title
    if data.description is not None:
        bill.description = data.description
    if data.amount is not None:
        bill.amount = data.amount
    if data.due_date is not None:
        bill.due_date = data.due_date
    if data.status is not None:
        bill.status = MaintenanceStatus(data.status)

    db.commit()
    db.refresh(bill)
    return _build_response(bill)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bill(bill_id: int, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Delete a maintenance bill. Owner only."""
    bill = db.query(MaintenanceBill).filter(MaintenanceBill.id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    pg = db.query(PG).filter(PG.id == bill.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(bill)
    db.commit()
