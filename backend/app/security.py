"""Password hashing (argon2), JWT issue/verify, share-token generation, dice."""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .config import settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def generate_share_token() -> str:
    """URL-safe, unguessable token for a player share link."""
    return secrets.token_urlsafe(24)


# --- Dice ------------------------------------------------------------------

_DICE_RE = re.compile(r"^\s*(\d*)d(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)
_MAX_DICE = 100
_MAX_SIDES = 1000


class DiceError(ValueError):
    pass


def roll_formula(formula: str) -> dict:
    """Parse and roll a simple formula like '2d6+3'. Returns a detail dict.

    Kept deliberately small for v1 (single dice group + flat modifier). Extend
    to multi-group formulas later.
    """
    m = _DICE_RE.match(formula)
    if not m:
        raise DiceError(f"Unsupported dice formula: {formula!r}")

    count = int(m.group(1)) if m.group(1) else 1
    sides = int(m.group(2))
    modifier = int(m.group(3).replace(" ", "")) if m.group(3) else 0

    if not (1 <= count <= _MAX_DICE):
        raise DiceError(f"Dice count must be 1..{_MAX_DICE}")
    if not (2 <= sides <= _MAX_SIDES):
        raise DiceError(f"Dice sides must be 2..{_MAX_SIDES}")

    rolls = [secrets.randbelow(sides) + 1 for _ in range(count)]
    total = sum(rolls) + modifier
    return {
        "formula": formula.strip(),
        "count": count,
        "sides": sides,
        "modifier": modifier,
        "rolls": rolls,
        "total": total,
    }
