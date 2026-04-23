from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date
from app.database import get_db
from app.models.user import User
from app.models.room import Room
from app.models.bed import Bed, BedStatus
from app.models.pg import PG
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse, BedInfo
from app.utils.dependencies import require_owner, get_current_user

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(data: RoomCreate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Create a room with optional auto-bed creation. Owner only."""
    pg = db.query(PG).filter(PG.id == data.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=404, detail="PG not found or not owned by you")

    room = Room(
        pg_id=data.pg_id,
        room_number=data.room_number,
        floor=data.floor,
        room_type=data.room_type,
        sharing_type=data.sharing_type,
        daily_stay_charges=data.daily_stay_charges,
        is_available_for_rent=data.is_available_for_rent,
        facilities=data.facilities,
    )
    db.add(room)
    db.flush()

    # Auto-create beds
    num_beds = data.num_beds or 1
    for i in range(1, num_beds + 1):
        bed = Bed(room_id=room.id, bed_number=f"B{i}", status=BedStatus.VACANT)
        db.add(bed)

    db.commit()
    db.refresh(room)

    return _build_room_response(room)


@router.get("", response_model=List[RoomResponse])
def list_rooms(pg_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all rooms, optionally filtered by PG."""
    query = db.query(Room)
    if pg_id:
        query = query.filter(Room.pg_id == pg_id)
    rooms = query.all()
    return [_build_room_response(r) for r in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get room details with beds."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return _build_room_response(room)


@router.put("/{room_id}", response_model=RoomResponse)
def update_room(room_id: int, data: RoomUpdate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Update room details. Owner only."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verify ownership via PG
    pg = db.query(PG).filter(PG.id == room.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=403, detail="Not authorized to edit this room")

    if data.room_number is not None:
        room.room_number = data.room_number
    if data.floor is not None:
        room.floor = data.floor
    if data.room_type is not None:
        room.room_type = data.room_type
    if data.sharing_type is not None:
        room.sharing_type = data.sharing_type
    if data.daily_stay_charges is not None:
        room.daily_stay_charges = data.daily_stay_charges
    if data.is_available_for_rent is not None:
        room.is_available_for_rent = data.is_available_for_rent
    if data.facilities is not None:
        room.facilities = data.facilities

    db.commit()
    db.refresh(room)
    return _build_room_response(room)


def _compute_in_notice_period(tenant) -> bool:
    if tenant is None:
        return False
    notice_days = getattr(tenant, 'notice_period', 30) or 30
    ref_raw = getattr(tenant, 'move_out_date', None) or getattr(tenant, 'exit_date', None)
    if ref_raw is None:
        return False
    try:
        ref_date = ref_raw if isinstance(ref_raw, date) else date.fromisoformat(str(ref_raw))
        today = date.today()
        delta = (ref_date - today).days
        return 0 <= delta <= notice_days
    except (ValueError, TypeError):
        return False


def _build_room_response(room: Room) -> RoomResponse:
    beds = []
    for bed in room.beds:
        tenant_name = None
        in_notice = False
        move_out_date = None
        if bed.tenant and bed.tenant.user:
            tenant_name = bed.tenant.user.name
            in_notice = _compute_in_notice_period(bed.tenant)
            move_out_date = bed.tenant.move_out_date or bed.tenant.exit_date
        beds.append(BedInfo(
            id=bed.id,
            bed_number=bed.bed_number,
            status=bed.status.value,
            tenant_name=tenant_name,
            price_per_bed=bed.price_per_bed,
            in_notice_period=in_notice,
            move_out_date=move_out_date,
        ))
    return RoomResponse(
        id=room.id,
        pg_id=room.pg_id,
        room_number=room.room_number,
        floor=room.floor,
        room_type=room.room_type,
        sharing_type=getattr(room, 'sharing_type', None),
        daily_stay_charges=getattr(room, 'daily_stay_charges', None),
        is_available_for_rent=getattr(room, 'is_available_for_rent', True),
        facilities=getattr(room, 'facilities', None),
        created_at=room.created_at,
        beds=beds,
    )


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Delete a room and all its beds. Owner only."""
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Verify ownership via PG
    pg = db.query(PG).filter(PG.id == room.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=403, detail="Not authorized to delete this room")

    # Prevent deletion if any bed has an active tenant
    occupied = [b for b in room.beds if b.tenant is not None]
    if occupied:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete room with {len(occupied)} active tenant(s). Please vacate all beds first.",
        )

    db.delete(room)
    db.commit()
