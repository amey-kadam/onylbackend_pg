from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User, UserRole
from app.models.pg import PG
from app.models.pg_staff import PGStaff
from app.utils.auth import hash_password
from app.utils.dependencies import require_owner, get_current_user

router = APIRouter(prefix="/api/staff", tags=["Staff"])


class StaffCreate(BaseModel):
    name: str
    phone: str
    password: str
    pg_id: int


class StaffResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    role: str
    pg_id: int
    pg_name: str

    class Config:
        from_attributes = True


class PGModelResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    owner_id: int

    class Config:
        from_attributes = True


@router.get("", response_model=List[StaffResponse])
def list_staff(pg_id: Optional[int] = None, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """List all staff for the owner's PGs."""
    query = db.query(PGStaff).join(PG, PGStaff.pg_id == PG.id).filter(PG.owner_id == owner.id)
    if pg_id:
        query = query.filter(PGStaff.pg_id == pg_id)
    records = query.all()

    result = []
    for r in records:
        if r.user:
            result.append(StaffResponse(
                id=r.user.id,
                name=r.user.name,
                phone=r.user.phone,
                email=r.user.email,
                role=r.user.role.value,
                pg_id=r.pg_id,
                pg_name=r.pg.name if r.pg else "",
            ))
    return result


@router.post("", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(data: StaffCreate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Create a new staff user account and assign to a PG."""
    # Verify PG belongs to owner
    pg = db.query(PG).filter(PG.id == data.pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=404, detail="PG not found or not owned by you")

    # Check phone uniqueness
    existing = db.query(User).filter(User.phone == data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")

    user = User(
        name=data.name,
        phone=data.phone,
        role=UserRole.STAFF,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()

    pg_staff = PGStaff(pg_id=data.pg_id, user_id=user.id)
    db.add(pg_staff)
    db.commit()
    db.refresh(user)

    return StaffResponse(
        id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        role=user.role.value,
        pg_id=data.pg_id,
        pg_name=pg.name,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_staff(user_id: int, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Remove a staff member from all of this owner's PGs and delete their account."""
    # Find all pg_staff records for this user under owner's PGs
    records = (
        db.query(PGStaff)
        .join(PG, PGStaff.pg_id == PG.id)
        .filter(PG.owner_id == owner.id, PGStaff.user_id == user_id)
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail="Staff member not found")

    for r in records:
        db.delete(r)

    # Delete the user account itself if they have no remaining staff assignments
    remaining = db.query(PGStaff).filter(PGStaff.user_id == user_id).count()
    if remaining == 0:
        user = db.query(User).filter(User.id == user_id, User.role == UserRole.STAFF).first()
        if user:
            db.delete(user)

    db.commit()


@router.get("/my-pgs", response_model=List[PGModelResponse])
def get_my_pgs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Staff member fetches PGs they are assigned to."""
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Only staff can use this endpoint")
    records = db.query(PGStaff).filter(PGStaff.user_id == current_user.id).all()
    return [
        PGModelResponse(
            id=r.pg.id,
            name=r.pg.name,
            address=r.pg.address,
            owner_id=r.pg.owner_id,
        )
        for r in records if r.pg
    ]
