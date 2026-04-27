"""JWT authentication for the Aegis customer-facing API.

Provides token creation, validation, and FastAPI dependency injection
for per-customer scoped authentication.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)

_DEFAULT_SECRET = "aegis-dev-secret-change-in-production"
_ALGORITHM = "HS256"
_DEFAULT_EXPIRY_HOURS = 24

_security = HTTPBearer()


class CustomerClaims(BaseModel):
    """Claims embedded in a customer JWT."""

    model_config = ConfigDict(frozen=True)

    customer_id: str
    customer_name: str
    allowed_cohorts: list[str] | None = None
    rate_limit_qps: int = 10
    llm_budget_cents: int = 1000


class TokenPayload(BaseModel):
    """Decoded JWT token payload."""

    model_config = ConfigDict(frozen=True)

    sub: str
    customer_name: str
    allowed_cohorts: list[str] | None
    rate_limit_qps: int
    llm_budget_cents: int
    exp: datetime
    iat: datetime


def _resolve_secret(secret: str | None) -> str:
    return secret or os.environ.get("AEGIS_JWT_SECRET", _DEFAULT_SECRET)


def create_token(
    claims: CustomerClaims,
    *,
    secret: str | None = None,
    expiry_hours: int = _DEFAULT_EXPIRY_HOURS,
) -> str:
    """Create a signed JWT from customer claims."""
    now = datetime.now(UTC)
    payload = {
        "sub": claims.customer_id,
        "customer_name": claims.customer_name,
        "allowed_cohorts": claims.allowed_cohorts,
        "rate_limit_qps": claims.rate_limit_qps,
        "llm_budget_cents": claims.llm_budget_cents,
        "exp": now + timedelta(hours=expiry_hours),
        "iat": now,
    }
    return jwt.encode(payload, _resolve_secret(secret), algorithm=_ALGORITHM)


def decode_token(token: str, *, secret: str | None = None) -> TokenPayload:
    """Decode and validate a JWT, returning the token payload."""
    try:
        decoded = jwt.decode(
            token, _resolve_secret(secret), algorithms=[_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    return TokenPayload(
        sub=decoded["sub"],
        customer_name=decoded["customer_name"],
        allowed_cohorts=decoded.get("allowed_cohorts"),
        rate_limit_qps=decoded.get("rate_limit_qps", 10),
        llm_budget_cents=decoded.get("llm_budget_cents", 1000),
        exp=datetime.fromtimestamp(decoded["exp"], tz=UTC),
        iat=datetime.fromtimestamp(decoded["iat"], tz=UTC),
    )


def get_current_customer(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_security)],
) -> TokenPayload:
    """FastAPI dependency: extract and validate customer from bearer token."""
    return decode_token(credentials.credentials)


def require_cohort_access(customer: TokenPayload, cohort: str | None) -> None:
    """Enforce cohort-level access restrictions.

    Raises HTTPException 403 if the customer's token restricts cohorts
    and the requested cohort is not in the allowed list.
    """
    if customer.allowed_cohorts is not None and cohort is not None:
        if cohort not in customer.allowed_cohorts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for cohort: {cohort}",
            )
