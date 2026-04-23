from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.user import User, UserRole
from app.models.notice import Notice
from app.models.tenant import Tenant
from app.models.pg import PG
from app.schemas.notice import NoticeCreate, NoticeResponse, NoticeListResponse
from app.utils.dependencies import get_current_user, require_owner

router = APIRouter(prefix="/api/notices", tags=["Notices"])


@router.post("", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
def create_notice(data: NoticeCreate, db: Session = Depends(get_db), owner: User = Depends(require_owner)):
    """Post a notice. Owner only."""
    # If pg_id not provided, use the first PG owned by the user
    pg_id = data.pg_id
    if not pg_id:
        pg = db.query(PG).filter(PG.owner_id == owner.id).first()
        if not pg:
            raise HTTPException(status_code=404, detail="No PG found. Create a PG first.")
        pg_id = pg.id

    notice = Notice(
        pg_id=pg_id,
        title=data.title,
        message=data.message,
        priority=data.priority,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)

    return NoticeResponse.model_validate(notice)


@router.get("", response_model=NoticeListResponse)
def list_notices(pg_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List notices. Both owner and tenant can view."""
    if current_user.role == UserRole.OWNER:
        query = db.query(Notice).join(Notice.pg).filter(PG.owner_id == current_user.id)
    else:
        tenant = db.query(Tenant).filter(Tenant.user_id == current_user.id).first()
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant profile not found")
        query = db.query(Notice).filter(Notice.pg_id == tenant.pg_id)

    if pg_id:
        query = query.filter(Notice.pg_id == pg_id)

    notices = query.order_by(Notice.created_at.desc()).all()

    return NoticeListResponse(
        notices=[NoticeResponse.model_validate(n) for n in notices],
        total=len(notices),
    )
