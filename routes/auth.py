from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserRegister, UserLogin, UserResponse, TokenResponse, UserUpdate, ChangePassword
from app.utils.auth import hash_password, verify_password, create_access_token
from app.utils.limiter import limiter
from app.utils.logger import logger

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user (owner or tenant)."""
    # Check if phone already exists
    existing = db.query(User).filter(User.phone == data.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already registered",
        )

    # Check email uniqueness if provided
    if data.email:
        existing_email = db.query(User).filter(User.email == data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    user = User(
        name=data.name,
        phone=data.phone,
        email=data.email,
        role=UserRole(data.role),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"user_id": user.id, "role": user.role.value})
    logger.info(f"New user registered: {user.phone} ({user.role.value})")

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, data: UserLogin, db: Session = Depends(get_db)):
    """Login with phone and password."""
    user = db.query(User).filter(User.phone == data.phone).first()
    if not user:
        logger.warning(f"Failed login attempt for unknown phone: {data.phone}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
        )
    
    is_valid = verify_password(data.password, user.password_hash)
    if not is_valid:
        logger.warning(f"Failed login attempt (wrong password) for phone: {data.phone}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password",
        )

    token = create_access_token({"user_id": user.id, "role": user.role.value})
    logger.info(f"User logged in: {user.phone} ({user.role.value})")

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_me(
    db: Session = Depends(get_db),
    credentials=Depends(__import__("app.utils.dependencies", fromlist=["get_current_user"]).get_current_user),
):
    """Get current user profile."""
    return UserResponse.model_validate(credentials)


@router.put("/me", response_model=UserResponse)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(__import__("app.utils.dependencies", fromlist=["get_current_user"]).get_current_user),
):
    """Update current user profile."""
    # Check if phone is being updated and if it belongs to another user
    if data.phone and data.phone != current_user.phone:
        existing = db.query(User).filter(User.phone == data.phone).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered by another user",
            )
        current_user.phone = data.phone

    # Check if email is being updated and if it belongs to another user
    if data.email and data.email != current_user.email:
        existing = db.query(User).filter(User.email == data.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered by another user",
            )
        current_user.email = data.email

    if data.name:
        current_user.name = data.name

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.put("/me/password")
@limiter.limit("5/minute")
def change_password(
    request: Request,
    data: ChangePassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(__import__("app.utils.dependencies", fromlist=["get_current_user"]).get_current_user),
):
    """Change current user password."""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password",
        )
    
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
