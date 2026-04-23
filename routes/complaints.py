from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.complaint import Complaint, ComplaintStatus
from app.models.tenant import Tenant
from app.models.pg import PG
from app.models.pg_staff import PGStaff
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate, ComplaintResponse, ComplaintListResponse
from app.utils.dependencies import get_current_user, require_owner, require_owner_or_staff

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(data: ComplaintCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Raise a complaint. Tenant only."""
    if current_user.role != UserRole.TENANT:
        raise HTTPException(status_code=403, detail="Only tenants can raise complaints")

    tenant = db.query(Tenant).filter(Tenant.user_id == current_user.id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant profile not found")

    pg_id = data.pg_id or tenant.pg_id

    complaint = Complaint(
        tenant_id=tenant.id,
        pg_id=pg_id,
        title=data.title,
        description=data.description,
        category=data.category,
        status=ComplaintStatus.PENDING,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return _build_complaint_response(complaint)


@router.get("", response_model=ComplaintListResponse)
def list_complaints(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    pg_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List complaints. Owner/staff sees all for their PG, tenant sees own."""
    if current_user.role == UserRole.OWNER:
        query = db.query(Complaint).join(Complaint.pg).filter(PG.owner_id == current_user.id)
    elif current_user.role == UserRole.STAFF:
        staff_pg_ids = [
            r.pg_id for r in db.query(PGStaff).filter(PGStaff.user_id == current_user.id).all()
        ]
        query = db.query(Complaint).filter(Complaint.pg_id.in_(staff_pg_ids))
    else:
        tenant = db.query(Tenant).filter(Tenant.user_id == current_user.id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant profile not found")
        query = db.query(Complaint).filter(Complaint.tenant_id == tenant.id)

    if status_filter:
        try:
            query = query.filter(Complaint.status == ComplaintStatus(status_filter))
        except ValueError:
            pass
    if category and category != "All":
        query = query.filter(Complaint.category == category)
    if pg_id:
        query = query.filter(Complaint.pg_id == pg_id)

    complaints = query.order_by(Complaint.created_at.desc()).all()

    pending = sum(1 for c in complaints if c.status == ComplaintStatus.PENDING)
    in_progress = sum(1 for c in complaints if c.status == ComplaintStatus.IN_PROGRESS)
    resolved = sum(1 for c in complaints if c.status == ComplaintStatus.RESOLVED)

    return ComplaintListResponse(
        complaints=[_build_complaint_response(c) for c in complaints],
        total=len(complaints),
        pending=pending,
        in_progress=in_progress,
        resolved=resolved,
    )


@router.put("/{complaint_id}", response_model=ComplaintResponse)
def update_complaint(
    complaint_id: int, data: ComplaintUpdate, db: Session = Depends(get_db),
    current_user: User = Depends(require_owner_or_staff)
):
    """Update complaint status. Owner or staff only."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    complaint.status = ComplaintStatus(data.status)
    db.commit()
    db.refresh(complaint)

    return _build_complaint_response(complaint)


def _build_complaint_response(c: Complaint) -> ComplaintResponse:
    tenant_name = None
    if c.tenant and c.tenant.user:
        tenant_name = c.tenant.user.name
    return ComplaintResponse(
        id=c.id,
        tenant_id=c.tenant_id,
        tenant_name=tenant_name,
        pg_id=c.pg_id,
        title=c.title,
        description=c.description,
        category=c.category,
        status=c.status.value,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )
