from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.user import User
from app.models.bed import Bed, BedStatus
from app.models.tenant import Tenant, TenantStatus
from app.models.payment import Payment, PaymentStatus
from app.models.complaint import Complaint, ComplaintStatus
from app.models.pg import PG
from app.models.room import Room
from app.schemas.dashboard import DashboardSummary, ComplaintSummary
from app.models.pg_staff import PGStaff
from app.utils.dependencies import require_owner_or_staff

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(pg_id: int = None, db: Session = Depends(get_db), owner: User = Depends(require_owner_or_staff)):
    """Get dashboard metrics. Owner or staff."""
    current_month = datetime.now().strftime("%Y-%m")

    # Get accessible PGs based on role
    if owner.role.value == "staff":
        all_pg_ids = [r.pg_id for r in db.query(PGStaff).filter(PGStaff.user_id == owner.id).all()]
        if pg_id and pg_id in all_pg_ids:
            pg_ids = [pg_id]
        else:
            pg_ids = all_pg_ids
    else:
        query = db.query(PG).filter(PG.owner_id == owner.id)
        if pg_id:
            query = query.filter(PG.id == pg_id)
        pg_ids = [pg.id for pg in query.all()]

    if not pg_ids:
        return DashboardSummary(current_month=current_month)

    # Bed stats
    total_beds = db.query(Bed).join(Bed.room).filter(Room.pg_id.in_(pg_ids)).count()
    occupied_beds = db.query(Bed).join(Bed.room).filter(
        Room.pg_id.in_(pg_ids), Bed.status == BedStatus.OCCUPIED
    ).count()
    vacant_beds = total_beds - occupied_beds

    # Tenant stats
    total_tenants = db.query(Tenant).filter(Tenant.pg_id.in_(pg_ids)).count()
    active_tenants = db.query(Tenant).filter(
        Tenant.pg_id.in_(pg_ids), Tenant.status == TenantStatus.ACTIVE
    ).count()

    # Payment stats for current month
    payments = db.query(Payment).join(Payment.tenant).filter(
        Tenant.pg_id.in_(pg_ids), Payment.month_year == current_month
    ).all()

    active_tenants_list = db.query(Tenant).filter(
        Tenant.pg_id.in_(pg_ids), Tenant.status == TenantStatus.ACTIVE
    ).all()

    rent_collected = 0.0
    rent_pending = 0.0

    tenant_payments_this_month = {p.tenant_id: p for p in payments}

    for t in active_tenants_list:
        monthly_rent = t.monthly_rent
        payment = tenant_payments_this_month.get(t.id)

        if payment:
            if payment.status == PaymentStatus.PAID:
                rent_collected += payment.amount
            elif payment.status == PaymentStatus.PARTIAL:
                rent_collected += payment.amount
                # Assuming payment.amount is what was paid, the rest is pending
                rent_pending += max(0, monthly_rent - payment.amount)
            else: # UNPAID
                rent_pending += monthly_rent
        else:
            rent_pending += monthly_rent

    # Complaint stats
    active_complaints_query = db.query(Complaint).filter(
        Complaint.pg_id.in_(pg_ids),
        Complaint.status.in_([ComplaintStatus.PENDING, ComplaintStatus.IN_PROGRESS]),
    )
    active_complaints = active_complaints_query.count()

    recent_complaints = active_complaints_query.order_by(Complaint.created_at.desc()).limit(5).all()
    recent_complaint_summaries = []
    for c in recent_complaints:
        tenant_name = c.tenant.user.name if c.tenant and c.tenant.user else None
        recent_complaint_summaries.append(ComplaintSummary(
            id=c.id, title=c.title, status=c.status.value, tenant_name=tenant_name
        ))

    occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0.0

    return DashboardSummary(
        total_beds=total_beds,
        occupied_beds=occupied_beds,
        vacant_beds=vacant_beds,
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        rent_collected=rent_collected,
        rent_pending=rent_pending,
        active_complaints=active_complaints,
        recent_complaints=recent_complaint_summaries,
        occupancy_rate=round(occupancy_rate, 1),
        current_month=current_month,
    )
