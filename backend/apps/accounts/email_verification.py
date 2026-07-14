from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.accounts.models import EmailVerificationOTP, User


def send_registration_otp(user: User) -> EmailVerificationOTP:
    """Create and send a fresh registration verification OTP."""
    code = _generate_otp()
    now = timezone.now()
    otp = EmailVerificationOTP.objects.create(
        user=user,
        code_hash=_hash_otp(code),
        sent_to_email=user.email,
        expires_at=now + timedelta(minutes=settings.EMAIL_VERIFICATION_OTP_TTL_MINUTES),
    )
    send_mail(
        subject="Your Zeitgeist verification code",
        message=(
            f"Your Zeitgeist verification code is {code}.\n\n"
            f"This code expires in {settings.EMAIL_VERIFICATION_OTP_TTL_MINUTES} minutes."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    return otp


def verify_registration_otp(*, email: str, code: str) -> User:
    """Validate an OTP and mark the matching user's email as verified."""
    normalized_email = email.strip().lower()
    try:
        user = User.objects.get(email=normalized_email)
    except User.DoesNotExist as exc:
        raise EmailVerificationError("Invalid or expired verification code.") from exc

    if user.is_email_verified:
        return user

    otp = (
        EmailVerificationOTP.objects.filter(
            user=user,
            consumed_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if otp is None or otp.expires_at <= timezone.now():
        raise EmailVerificationError("Invalid or expired verification code.")

    if otp.attempts >= settings.EMAIL_VERIFICATION_MAX_ATTEMPTS:
        raise EmailVerificationError("Invalid or expired verification code.")

    otp.attempts += 1
    otp.save(update_fields=["attempts"])

    if not constant_time_compare(otp.code_hash, _hash_otp(code.strip())):
        raise EmailVerificationError("Invalid or expired verification code.")

    now = timezone.now()
    otp.consumed_at = now
    otp.save(update_fields=["consumed_at"])
    user.email_verified_at = now
    user.save(update_fields=["email_verified_at"])
    return user


def maybe_resend_registration_otp(email: str) -> bool:
    """Resend an OTP for an unverified account, returning whether one was sent."""
    normalized_email = email.strip().lower()
    user = User.objects.filter(email=normalized_email).first()
    if user is None or user.is_email_verified:
        return False

    latest_otp = (
        EmailVerificationOTP.objects.filter(user=user)
        .order_by("-created_at")
        .first()
    )
    if latest_otp is not None:
        cooldown_cutoff = timezone.now() - timedelta(
            seconds=settings.EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS
        )
        if latest_otp.created_at > cooldown_cutoff:
            raise EmailVerificationError("Please wait before requesting another code.")

    send_registration_otp(user)
    return True


class EmailVerificationError(ValueError):
    pass


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp(code: str) -> str:
    return salted_hmac("accounts.email_verification_otp", code).hexdigest()
