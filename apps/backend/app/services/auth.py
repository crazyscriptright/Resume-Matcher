"""Authentication service for user management and JWT tokens."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User

logger = logging.getLogger(__name__)

# JWT configuration
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Bcrypt password length limitation
BCRYPT_MAX_PASSWORD_LENGTH = 72


def _truncate_password(password: str) -> str:
    """Truncate password to bcrypt's 72-byte limit.

    Bcrypt truncates passwords longer than 72 bytes silently. We truncate
    explicitly to ensure consistent hashing and verification.

    Args:
        password: Plain text password

    Returns:
        Password truncated to 72 bytes
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > BCRYPT_MAX_PASSWORD_LENGTH:
        # Truncate bytes to 72, then decode, handling any incomplete multi-byte chars
        truncated_bytes = password_bytes[:BCRYPT_MAX_PASSWORD_LENGTH]
        # Decode with 'ignore' to handle incomplete multi-byte sequences
        return truncated_bytes.decode("utf-8", errors="ignore")
    return password


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password (will be truncated to 72 bytes if longer)

    Returns:
        Hashed password
    """
    truncated = _truncate_password(password)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(truncated.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password (will be truncated to 72 bytes if longer)
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    truncated = _truncate_password(plain_password)
    try:
        return bcrypt.checkpw(truncated.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError) as e:
        logger.warning(f"Password verification error: {e}")
        return False


def create_access_token(user_id: int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        expires_delta: Token expiration time (default: 24 hours)

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=JWT_EXPIRATION_HOURS)

    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"sub": str(user_id), "exp": expire}

    # Use a secret key from settings or generate a default
    secret_key = getattr(settings, "jwt_secret_key", "your-secret-key-change-in-production")

    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> int | None:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        User ID if token is valid, None otherwise
    """
    try:
        secret_key = getattr(settings, "jwt_secret_key", "your-secret-key-change-in-production")
        payload = jwt.decode(token, secret_key, algorithms=[JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")

        if user_id is None:
            logger.warning("Token missing user ID")
            return None

        return int(user_id)
    except JWTError as e:
        logger.warning(f"Invalid token: {e}")
        return None
    except (ValueError, TypeError) as e:
        logger.warning(f"Token decode error: {e}")
        return None


def register_user(session: Session, email: str, password: str) -> User:
    """Register a new user.

    Args:
        session: SQLAlchemy session
        email: User email
        password: Plain text password

    Returns:
        Created User object

    Raises:
        ValueError: If email already exists
    """
    # Check if email already exists
    existing_user = session.query(User).filter(User.email == email).first()
    if existing_user:
        raise ValueError(f"Email already registered: {email}")

    # Create new user
    hashed_password = hash_password(password)
    user = User(email=email, password_hash=hashed_password)

    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"User registered: {email}")
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password.

    Args:
        session: SQLAlchemy session
        email: User email
        password: Plain text password

    Returns:
        User object if authentication successful, None otherwise
    """
    user = session.query(User).filter(User.email == email).first()

    if not user:
        logger.warning(f"Login attempt with non-existent email: {email}")
        return None

    if not verify_password(password, user.password_hash):
        logger.warning(f"Login attempt with wrong password for: {email}")
        return None

    logger.info(f"User authenticated: {email}")
    return user


def get_user_by_id(session: Session, user_id: int) -> User | None:
    """Get user by ID.

    Args:
        session: SQLAlchemy session
        user_id: User ID

    Returns:
        User object if found, None otherwise
    """
    return session.query(User).filter(User.id == user_id).first()
