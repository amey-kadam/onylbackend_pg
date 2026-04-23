import random
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.utils.auth import hash_password
from app.utils.logger import logger
from app.utils.limiter import limiter

router = APIRouter(prefix="/api/auth", tags=["Password Reset"])
settings = get_settings()


class ForgotPasswordRequest(BaseModel):
    phone: str


class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str
    new_password: str


def _generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def _send_otp_email(to_email: str, otp: str) -> bool:
    """Send OTP via Resend. Returns True on success."""
    try:
        import resend
        resend.api_key = settings.RESEND_API_KEY
        params: resend.Emails.SendParams = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": "Your Password Reset OTP – JMD Nest",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:32px;background:#f9f9f9;border-radius:12px;">
              <h2 style="color:#6366f1;margin-bottom:8px;">Password Reset</h2>
              <p style="color:#555;">Use the OTP below to reset your password. It is valid for <strong>10 minutes</strong>.</p>
              <div style="font-size:36px;font-weight:700;letter-spacing:8px;color:#1e293b;background:#fff;border:2px solid #e2e8f0;border-radius:8px;padding:20px;text-align:center;margin:24px 0;">
                {otp}
              </div>
              <p style="color:#888;font-size:12px;">If you did not request this, please ignore this email.</p>
            </div>
            """,
        }
        resend.Emails.send(params)
        return True
    except Exception as e:
        logger.error(f"[Resend] Error sending OTP email to {to_email}: {e}")
        return False


@router.post("/forgot-password", status_code=200)
@limiter.limit("3/minute")
def forgot_password(request: Request, data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Send OTP to registered email for password reset, using phone number to identify user."""
    user = db.query(User).filter(User.phone == data.phone).first()
    if not user or not user.email:
        logger.warning(f"Forgot password requested for phone {data.phone} but user/email not found.")
        # Return generic message to prevent enumeration
        return {"message": "If this phone is registered and has an email, an OTP has been sent."}

    otp = _generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # Try sending the email FIRST — only persist OTP if it succeeds
    sent = _send_otp_email(user.email, otp)
    if not sent:
        logger.error(f"Failed to send OTP to {user.email}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send OTP email. Please check your email address or try again later.",
        )

    # Invalidate previous OTPs for this email
    db.execute(
        text("UPDATE password_reset_otps SET used=1 WHERE email=:email AND used=0"),
        {"email": user.email},
    )

    # Insert new OTP
    db.execute(
        text(
            "INSERT INTO password_reset_otps (email, otp, expires_at) VALUES (:email, :otp, :expires_at)"
        ),
        {"email": user.email, "otp": otp, "expires_at": expires_at},
    )
    db.commit()

    logger.info(f"OTP successfully generated and sent for phone {data.phone}")
    return {"message": "If this phone is registered and has an email, an OTP has been sent."}


@router.post("/reset-password", status_code=200)
@limiter.limit("5/minute")
def reset_password(request: Request, data: VerifyOtpRequest, db: Session = Depends(get_db)):
    """Verify OTP and reset password."""
    # Look up user via ORM by phone
    user = db.query(User).filter(User.phone == data.phone).first()
    if not user or not user.email:
        raise HTTPException(status_code=404, detail="User not found or no email registered.")

    row = db.execute(
        text(
            "SELECT id, expires_at, used FROM password_reset_otps "
            "WHERE email=:email AND otp=:otp ORDER BY id DESC LIMIT 1"
        ),
        {"email": user.email, "otp": data.otp},
    ).fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="Invalid OTP.")

    if row.used:
        raise HTTPException(status_code=400, detail="OTP has already been used.")

    expires_at = row.expires_at
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)

    if datetime.utcnow() > expires_at:
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # Mark OTP as used
    db.execute(
        text("UPDATE password_reset_otps SET used=1 WHERE id=:id"),
        {"id": row.id},
    )

    # Update password via ORM
    new_password = data.new_password.strip()  # strip accidental whitespace
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)

    logger.info(f"Password reset successfully for phone {data.phone}")
    return {"message": "Password reset successfully. You can now log in with your new password."}
