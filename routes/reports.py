from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime
from app.database import get_db
from app.models.user import User
from app.models.payment import Payment, PaymentStatus
from app.models.tenant import Tenant, TenantStatus
from app.models.maintenance_bill import MaintenanceBill, MaintenanceStatus
from app.models.pg import PG
from app.utils.dependencies import require_owner

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/summary")
def get_report_summary(
    pg_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    month_year: Optional[str] = None,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    """Generate a report summary for a given PG and date range or month."""
    pg = db.query(PG).filter(PG.id == pg_id, PG.owner_id == owner.id).first()
    if not pg:
        return {"error": "PG not found"}

    # Resolve date range from month_year if provided
    if month_year and not (start_date and end_date):
        try:
            dt = datetime.strptime(month_year, "%Y-%m")
            start_date = dt.date().replace(day=1)
            import calendar
            last_day = calendar.monthrange(dt.year, dt.month)[1]
            end_date = dt.date().replace(day=last_day)
        except Exception:
            pass

    # ── Payments ────────────────────────────────────────────────────
    pay_q = (
        db.query(Payment)
        .join(Payment.tenant)
        .filter(Tenant.pg_id == pg_id)
    )
    if start_date:
        pay_q = pay_q.filter(Payment.payment_date >= start_date)
    if end_date:
        pay_q = pay_q.filter(Payment.payment_date <= end_date)

    all_payments = pay_q.all()

    _refund_types = {"deposit_refund", "deposit"}
    rent_payments = [
        p for p in all_payments
        if p.status == PaymentStatus.PAID
        and getattr(p, "payment_type", None) not in _refund_types
    ]
    refund_payments = [
        p for p in all_payments
        if getattr(p, "payment_type", None) == "deposit_refund"
    ]
    pending_payments = [
        p for p in all_payments
        if p.status in (PaymentStatus.UNPAID, PaymentStatus.PARTIAL)
        and getattr(p, "payment_type", None) not in _refund_types
    ]

    total_collected = sum(p.amount for p in rent_payments)
    total_refunded = sum(p.amount for p in refund_payments)
    total_pending = sum(p.amount for p in pending_payments)

    # Payment breakdown list
    payment_records = []
    for p in sorted(all_payments, key=lambda x: x.payment_date or date.today(), reverse=True):
        tenant_name = p.tenant.user.name if p.tenant and p.tenant.user else "Unknown"
        ptype = getattr(p, "payment_type", "rent") or "rent"
        payment_records.append({
            "tenant_name": tenant_name,
            "amount": p.amount,
            "status": p.status.value,
            "payment_type": ptype,
            "payment_date": str(p.payment_date) if p.payment_date else None,
            "month_year": p.month_year,
        })

    # ── Tenants ─────────────────────────────────────────────────────
    all_tenants_q = db.query(Tenant).filter(
        Tenant.pg_id == pg_id,
        Tenant.status != TenantStatus.DELETED,
    )
    all_tenants = all_tenants_q.all()

    active_count = sum(1 for t in all_tenants if t.status == TenantStatus.ACTIVE)

    new_tenants = []
    if start_date and end_date:
        for t in all_tenants:
            try:
                jd = date.fromisoformat(str(t.join_date)) if t.join_date else None
                if jd and start_date <= jd <= end_date:
                    name = t.user.name if t.user else "Unknown"
                    new_tenants.append({
                        "name": name,
                        "join_date": str(jd),
                        "monthly_rent": t.monthly_rent,
                        "room": t.bed.room.room_number if t.bed and t.bed.room else None,
                    })
            except Exception:
                pass

    checkout_tenants = []
    if start_date and end_date:
        for t in all_tenants:
            try:
                ed = date.fromisoformat(str(t.exit_date)) if t.exit_date else None
                if ed and start_date <= ed <= end_date:
                    name = t.user.name if t.user else "Unknown"
                    checkout_tenants.append({
                        "name": name,
                        "exit_date": str(ed),
                        "deposit": t.deposit,
                        "room": t.bed.room.room_number if t.bed and t.bed.room else None,
                    })
            except Exception:
                pass

    # ── Maintenance ──────────────────────────────────────────────────
    maint_q = db.query(MaintenanceBill).filter(MaintenanceBill.pg_id == pg_id)
    if start_date:
        maint_q = maint_q.filter(MaintenanceBill.due_date >= start_date)
    if end_date:
        maint_q = maint_q.filter(MaintenanceBill.due_date <= end_date)

    all_maint = maint_q.all()
    maint_paid = sum(m.amount for m in all_maint if m.status == MaintenanceStatus.PAID)
    maint_pending = sum(m.amount for m in all_maint if m.status == MaintenanceStatus.PENDING)

    maint_records = []
    for m in all_maint:
        tenant_name = m.tenant.user.name if m.tenant and m.tenant.user else "General"
        maint_records.append({
            "title": m.title,
            "tenant_name": tenant_name,
            "amount": m.amount,
            "status": m.status.value,
            "due_date": str(m.due_date) if m.due_date else None,
        })

    # ── Occupancy ────────────────────────────────────────────────────
    from app.models.bed import Bed
    from app.models.room import Room
    total_beds = db.query(Bed).join(Room).filter(Room.pg_id == pg_id).count()
    occupied_beds = db.query(Bed).join(Room).filter(
        Room.pg_id == pg_id, Bed.status == "occupied"
    ).count()
    occupancy_rate = round((occupied_beds / total_beds * 100) if total_beds > 0 else 0, 1)

    return {
        "pg_name": pg.name,
        "pg_address": pg.address or "",
        "owner_name": owner.name,
        "period": {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
            "month_year": month_year,
        },
        "revenue": {
            "total_collected": total_collected,
            "total_pending": total_pending,
            "total_refunded": total_refunded,
            "net_revenue": total_collected - total_refunded,
        },
        "tenants": {
            "active_count": active_count,
            "new_count": len(new_tenants),
            "checkout_count": len(checkout_tenants),
            "new_tenants": new_tenants,
            "checkout_tenants": checkout_tenants,
        },
        "maintenance": {
            "total_paid": maint_paid,
            "total_pending": maint_pending,
            "records": maint_records,
        },
        "occupancy": {
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "occupancy_rate": occupancy_rate,
        },
        "payment_records": payment_records,
    }
