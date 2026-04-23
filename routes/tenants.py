from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User, UserRole
from app.models.tenant import Tenant, TenantStatus
from app.models.bed import Bed, BedStatus
from app.models.pg import PG
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantListResponse, LedgerEntry, LedgerResponse, CheckoutRequest
from app.utils.auth import hash_password
from app.models.pg_staff import PGStaff
from app.utils.dependencies import get_current_user, require_owner, require_owner_or_staff

router = APIRouter(prefix="/api/tenants", tags=["Tenants"])


def _build_tenant_response(tenant: Tenant) -> TenantResponse:
    """Build a TenantResponse from a Tenant model instance."""
    return TenantResponse(
        id=tenant.id,
        user_id=tenant.user_id,
        name=tenant.user.name if tenant.user else "",
        phone=tenant.user.phone if tenant.user else "",
        email=tenant.user.email if tenant.user else None,
        pg_id=tenant.pg_id,
        pg_name=tenant.pg.name if tenant.pg else None,
        bed_id=tenant.bed_id,
        bed_number=tenant.bed.bed_number if tenant.bed else None,
        room_number=tenant.bed.room.room_number if tenant.bed and tenant.bed.room else None,
        join_date=tenant.join_date,
        exit_date=tenant.exit_date,
        move_out_date=getattr(tenant, 'move_out_date', None),
        locking_period=getattr(tenant, 'locking_period', 0),
        notice_period=getattr(tenant, 'notice_period', 30),
        agreement_period=getattr(tenant, 'agreement_period', 11),
        deposit=tenant.deposit,
        monthly_rent=tenant.monthly_rent,
        address=tenant.address,
        id_proof_url=tenant.id_proof_url,
        aadhar_url=tenant.aadhar_url,
        pan_url=tenant.pan_url,
        agreement_url=tenant.agreement_url,
        ledger_url=tenant.ledger_url,
        other_documents_url=tenant.other_documents_url,
        status=tenant.status.value,
        created_at=tenant.created_at,
    )


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(data: TenantCreate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Create a new tenant. Owner only."""
    # Verify PG belongs to owner
    pg = db.query(PG).filter(PG.id == data.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=404, detail="PG not found or not owned by you")

    # Check phone uniqueness
    existing = db.query(User).filter(User.phone == data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Check email uniqueness (only if email provided)
    if data.email:
        existing_email = db.query(User).filter(User.email == data.email).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered with another account")

    # Create user account for tenant
    user = User(
        name=data.name,
        phone=data.phone,
        email=data.email,
        role=UserRole.TENANT,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()

    agreement_url = data.agreement_url
    if not agreement_url:
        from app.utils.pdf_generator import generate_rent_agreement
        
        room_number = "N/A"
        bed_number = "N/A"
        if data.bed_id:
            bed = db.query(Bed).filter(Bed.id == data.bed_id).first()
            if bed:
                bed_number = str(bed.bed_number)
                if bed.room:
                    room_number = str(bed.room.room_number)

        try:
            agreement_url = generate_rent_agreement(
                tenant_name=data.name,
                tenant_address=data.address or "Address not provided",
                owner_name=owner.name,
                owner_address="Address not provided",
                pg_name=pg.name,
                pg_address=pg.address or "Address not provided",
                room_number=room_number,
                bed_number=bed_number,
                start_date=data.join_date,
                monthly_rent=data.monthly_rent,
                security_deposit=data.deposit,
                notice_period=getattr(data, 'notice_period', 30) or 30,
                agreement_period=getattr(data, 'agreement_period', 11) or 11
            )
        except Exception as e:
            import logging
            logging.error(f"Failed to generate agreement: {e}")

    # Create tenant profile
    tenant = Tenant(
        user_id=user.id,
        pg_id=data.pg_id,
        bed_id=data.bed_id,
        join_date=data.join_date,
        deposit=data.deposit,
        monthly_rent=data.monthly_rent,
        address=data.address,
        id_proof_url=data.id_proof_url,
        aadhar_url=data.aadhar_url,
        pan_url=data.pan_url,
        agreement_url=agreement_url,
        ledger_url=data.ledger_url,
        other_documents_url=data.other_documents_url,
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)

    # Update bed status if assigned
    if data.bed_id:
        bed = db.query(Bed).filter(Bed.id == data.bed_id).first()
        if bed:
            bed.status = BedStatus.OCCUPIED

    db.flush() # Ensure tenant ID is generated

    # Record initial deposit payment
    if tenant.deposit and tenant.deposit > 0:
        from app.models.payment import Payment, PaymentStatus
        from datetime import datetime
        
        payment = Payment(
            tenant_id=tenant.id,
            amount=tenant.deposit,
            status=PaymentStatus.PAID,
            month_year=datetime.now().strftime("%Y-%m"),
            payment_method="cash",
            payment_date=datetime.now().date(),
            payment_type="deposit",
            notes="Initial Deposit"
        )
        db.add(payment)

    db.commit()
    db.refresh(tenant)

    return _build_tenant_response(tenant)


@router.get("", response_model=TenantListResponse)
def list_tenants(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=500),
    status: Optional[str] = None,
    search: Optional[str] = None,
    pg_id: Optional[int] = None,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner_or_staff),
):
    """List all tenants. Owner or staff."""
    if owner.role.value == "staff":
        staff_pg_ids = [r.pg_id for r in db.query(PGStaff).filter(PGStaff.user_id == owner.id).all()]
        query = db.query(Tenant).join(Tenant.user).filter(Tenant.pg_id.in_(staff_pg_ids))
    else:
        query = db.query(Tenant).join(Tenant.user).join(Tenant.pg).filter(PG.owner_id == owner.id)

    if pg_id:
        query = query.filter(Tenant.pg_id == pg_id)
    if status:
        query = query.filter(Tenant.status == TenantStatus(status))
    else:
        query = query.filter(Tenant.status != TenantStatus.DELETED)
    if search:
        query = query.filter(User.name.ilike(f"%{search}%"))

    total = query.count()
    tenants = query.offset((page - 1) * per_page).limit(per_page).all()

    return TenantListResponse(
        tenants=[_build_tenant_response(t) for t in tenants],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/me", response_model=TenantResponse)
def get_my_profile(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the currently logged-in tenant's own profile."""
    tenant = db.query(Tenant).filter(Tenant.user_id == current_user.id, Tenant.status == TenantStatus.ACTIVE).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant profile not found")
    return _build_tenant_response(tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(tenant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get tenant profile. Owner sees any tenant, tenant sees own profile."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Authorization
    if current_user.role == UserRole.TENANT and tenant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return _build_tenant_response(tenant)


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int, data: TenantUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)
):
    """Update tenant details. Owner only."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Update user fields
    if data.name:
        tenant.user.name = data.name
    if data.phone:
        tenant.user.phone = data.phone

    update_data = data.model_dump(exclude_unset=True)
    # Handle bed change
    if "bed_id" in update_data and update_data["bed_id"] != tenant.bed_id:
        new_bed_id = update_data["bed_id"]
        # Free old bed
        if tenant.bed_id:
            old_bed = db.query(Bed).filter(Bed.id == tenant.bed_id).first()
            if old_bed:
                old_bed.status = BedStatus.VACANT
        # Assign new bed
        if new_bed_id is not None:
            new_bed = db.query(Bed).filter(Bed.id == new_bed_id).first()
            if new_bed:
                new_bed.status = BedStatus.OCCUPIED
        tenant.bed_id = new_bed_id

    # Update other fields
    if data.deposit is not None:
        tenant.deposit = data.deposit
    if data.monthly_rent is not None:
        tenant.monthly_rent = data.monthly_rent
    if data.address is not None:
        tenant.address = data.address
    if data.id_proof_url is not None:
        tenant.id_proof_url = data.id_proof_url
    if data.aadhar_url is not None:
        tenant.aadhar_url = data.aadhar_url
    if data.pan_url is not None:
        tenant.pan_url = data.pan_url
    if data.agreement_url is not None:
        tenant.agreement_url = data.agreement_url
    if data.ledger_url is not None:
        tenant.ledger_url = data.ledger_url
    if data.other_documents_url is not None:
        tenant.other_documents_url = data.other_documents_url
    if data.status:
        tenant.status = TenantStatus(data.status)
        if data.status == "exited" and tenant.bed_id:
            bed = db.query(Bed).filter(Bed.id == tenant.bed_id).first()
            if bed:
                bed.status = BedStatus.VACANT
            tenant.bed_id = None
    if data.exit_date:
        tenant.exit_date = data.exit_date
    if data.move_out_date is not None:
        tenant.move_out_date = data.move_out_date
    if data.locking_period is not None:
        tenant.locking_period = data.locking_period
    if data.notice_period is not None:
        tenant.notice_period = data.notice_period
    if data.agreement_period is not None:
        tenant.agreement_period = data.agreement_period

    db.commit()
    db.refresh(tenant)

    return _build_tenant_response(tenant)


@router.get("/{tenant_id}/ledger", response_model=LedgerResponse)
def get_tenant_ledger(
    tenant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Get full financial ledger for a tenant (rent + maintenance)."""
    from app.models.payment import Payment, PaymentStatus
    from app.models.maintenance_bill import MaintenanceBill, MaintenanceStatus

    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    if current_user.role == UserRole.TENANT and tenant.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    entries: list[LedgerEntry] = []

    # Deposit entry
    if tenant.deposit > 0:
        entries.append(LedgerEntry(
            id=0, entry_type="deposit", title="Security Deposit",
            amount=tenant.deposit, date=str(tenant.join_date),
            status="paid", month_year=None, notes="Security deposit paid at joining",
        ))

    # Rent & checkout settlement payments
    payments = db.query(Payment).filter(Payment.tenant_id == tenant_id).order_by(Payment.payment_date.desc()).all()
    _checkout_types = {"deposit_refund", "maintenance_deduction", "penalty"}
    _checkout_titles = {
        "deposit_refund": "Deposit Refund",
        "maintenance_deduction": "Maintenance Deduction",
        "penalty": "Penalty",
    }
    for p in payments:
        ptype = getattr(p, 'payment_type', None) or "rent"
        # Skip initial deposit payments — already represented by the manual Security Deposit entry
        if ptype == "deposit" or p.notes == "Initial Deposit":
            continue
        collected_by_name = None
        if getattr(p, 'collected_by_user_id', None):
            from app.models.user import User as UserModel
            u = db.query(UserModel).filter(UserModel.id == p.collected_by_user_id).first()
            if u:
                collected_by_name = u.name
        if ptype in _checkout_types:
            entry_type = ptype
            title = _checkout_titles[ptype]
        else:
            entry_type = "rent"
            title = f"Rent - {p.month_year}"
        entries.append(LedgerEntry(
            id=p.id, entry_type=entry_type, title=title,
            amount=p.amount, date=str(p.payment_date) if p.payment_date else None,
            status=p.status.value, month_year=p.month_year, notes=p.notes,
            payment_method=getattr(p, 'payment_method', 'cash'),
            collected_by=collected_by_name,
        ))

    # Maintenance bills
    maintenance = db.query(MaintenanceBill).filter(
        (MaintenanceBill.tenant_id == tenant_id) | (MaintenanceBill.pg_id == tenant.pg_id)
    ).order_by(MaintenanceBill.created_at.desc()).all()
    for m in maintenance:
        entries.append(LedgerEntry(
            id=m.id, entry_type="maintenance", title=m.title,
            amount=m.amount, date=str(m.due_date) if m.due_date else None,
            status=m.status.value, month_year=m.month_year, notes=m.description,
        ))

    total_paid = sum(e.amount for e in entries if e.entry_type == "rent" and e.status == "paid")
    total_pending = sum(e.amount for e in entries if e.entry_type == "rent" and e.status in ("unpaid", "partial"))
    total_maint_pending = sum(e.amount for e in entries if e.entry_type == "maintenance" and e.status == "pending")

    return LedgerResponse(
        entries=entries,
        total_paid=total_paid,
        total_pending=total_pending,
        total_maintenance_pending=total_maint_pending,
        opening_balance=tenant.deposit,
    )


@router.post("/{tenant_id}/checkout", response_model=TenantResponse)
def checkout_tenant(tenant_id: int, data: CheckoutRequest, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Checkout a tenant: record settlement entries, mark as exited, vacate bed. Payment history is preserved."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    pg = db.query(PG).filter(PG.id == tenant.pg_id).first()
    if not pg or pg.owner_id != owner.id:
        raise HTTPException(status_code=403, detail="Not authorized to checkout this tenant")

    if tenant.status != TenantStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Tenant is not active")

    from datetime import date
    from app.models.payment import Payment, PaymentStatus

    checkout_date = data.checkout_date or date.today()
    month_year = checkout_date.strftime("%Y-%m")

    # Record ONE payment entry for the refund amount actually issued to tenant
    if data.deposit_refund > 0:
        parts = [f"Deposit Refund: ₹{data.deposit_refund:.0f}"]
        if data.maintenance_deduction > 0:
            parts.append(f"Maintenance deducted: ₹{data.maintenance_deduction:.0f}")
        if data.penalty > 0:
            parts.append(f"Penalty deducted: ₹{data.penalty:.0f}")
        notes = " | ".join(parts)
        db.add(Payment(
            tenant_id=tenant.id,
            amount=data.deposit_refund,
            status=PaymentStatus.PAID,
            payment_date=checkout_date,
            month_year=month_year,
            payment_method="cash",
            payment_type="deposit_refund",
            notes=notes,
            collected_by_user_id=owner.id,
        ))

    # Vacate the bed
    if tenant.bed_id:
        bed = db.query(Bed).filter(Bed.id == tenant.bed_id).first()
        if bed:
            bed.status = BedStatus.VACANT
        tenant.bed_id = None

    # Mark as exited with checkout date
    tenant.status = TenantStatus.EXITED
    tenant.exit_date = checkout_date

    db.commit()
    db.refresh(tenant)

    return _build_tenant_response(tenant)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(tenant_id: int, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Delete a tenant. Owner only."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    pg = db.query(PG).filter(PG.id == tenant.pg_id).first()
    if not pg or pg.owner_id != owner.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this tenant")

    # Vacate the bed
    if tenant.bed_id:
        bed = db.query(Bed).filter(Bed.id == tenant.bed_id).first()
        if bed:
            bed.status = BedStatus.VACANT
        tenant.bed_id = None

    # Clear uploaded documents
    tenant.id_proof_url = None
    tenant.aadhar_url = None
    tenant.pan_url = None
    tenant.agreement_url = None
    tenant.ledger_url = None
    tenant.other_documents_url = None

    # Soft delete the tenant
    tenant.status = TenantStatus.DELETED

    # Alter user phone to free up the unique constraint
    import uuid
    if tenant.user:
        tenant.user.phone = f"del_{uuid.uuid4().hex[:8]}_{tenant.user.phone}"

    db.commit()
    return

