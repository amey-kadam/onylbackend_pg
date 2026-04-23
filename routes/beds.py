from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.bed import Bed, BedStatus
from app.models.tenant import Tenant
from app.schemas.bed import BedCreate, BedUpdate, BedResponse
from app.utils.dependencies import require_owner

router = APIRouter(prefix="/api/beds", tags=["Beds"])


@router.post("", response_model=BedResponse, status_code=status.HTTP_201_CREATED)
def create_bed(data: BedCreate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Create a new bed in a room. Owner only."""
    bed = Bed(room_id=data.room_id, bed_number=data.bed_number, status=BedStatus.VACANT)
    db.add(bed)
    db.commit()
    db.refresh(bed)
    return _build_bed_response(bed)


@router.put("/{bed_id}", response_model=BedResponse)
def update_bed(bed_id: int, data: BedUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Update bed status, price, or assign/unassign tenant. Owner only."""
    bed = db.query(Bed).filter(Bed.id == bed_id).first()
    if not bed:
        raise HTTPException(status_code=404, detail="Bed not found")

    if data.status:
        bed.status = BedStatus(data.status)

    if data.price_per_bed is not None:
        bed.price_per_bed = data.price_per_bed

    db.commit()
    db.refresh(bed)
    return _build_bed_response(bed)


@router.get("", response_model=List[BedResponse])
def list_beds(room_id: int = None, status: str = None, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """List beds, optionally filtered by room or status."""
    query = db.query(Bed)
    if room_id:
        query = query.filter(Bed.room_id == room_id)
    if status:
        query = query.filter(Bed.status == BedStatus(status))
    return [_build_bed_response(b) for b in query.all()]


def _build_bed_response(bed: Bed) -> BedResponse:
    tenant_name = None
    if bed.tenant and bed.tenant.user:
        tenant_name = bed.tenant.user.name
    room_number = bed.room.room_number if bed.room else None
    return BedResponse(
        id=bed.id,
        room_id=bed.room_id,
        bed_number=bed.bed_number,
        status=bed.status.value,
        tenant_name=tenant_name,
        room_number=room_number,
        price_per_bed=bed.price_per_bed,
    )
