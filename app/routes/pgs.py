from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User
from app.models.pg import PG
from app.schemas.pg import PGCreate, PGResponse
from app.utils.dependencies import require_owner

router = APIRouter(prefix="/api/pgs", tags=["Properties"])

@router.get("", response_model=List[PGResponse])
def get_properties(db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Get all properties (PGs) owned by the current owner."""
    pgs = db.query(PG).filter(PG.owner_id == owner.id).all()
    return pgs

@router.post("", response_model=PGResponse, status_code=status.HTTP_201_CREATED)
def create_property(
    data: PGCreate,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    """Create a new PG property for the current owner."""
    # Check for duplicate name under the same owner
    existing = db.query(PG).filter(PG.owner_id == owner.id, PG.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A property with this name already exists.",
        )
    pg = PG(
        name=data.name,
        address=data.address,
        owner_id=owner.id,
    )
    db.add(pg)
    db.commit()
    db.refresh(pg)
    return pg

@router.delete("/{pg_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(
    pg_id: int,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    """Delete a PG property owned by the current owner."""
    pg = db.query(PG).filter(PG.id == pg_id, PG.owner_id == owner.id).first()
    if not pg:
        raise HTTPException(status_code=404, detail="Property not found.")
    db.delete(pg)
    db.commit()
