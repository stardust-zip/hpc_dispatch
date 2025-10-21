import httpx
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .config import settings
from .database import get_http_client
from .models import User

logger = logging.getLogger(__name__)

MOCK_USERS = {
    "lecturer1": User(
        id=101, full_name="Mock Lecturer 1", user_type="lecturer", is_admin=False
    ),
    "lecturer2": User(
        id=102, full_name="Mock Lecturer 2", user_type="lecturer", is_admin=False
    ),
    "lecturer3": User(
        id=103, full_name="Mock Lecturer 3", user_type="lecturer", is_admin=False
    ),
    "admin": User(
        id=999, full_name="Mock Admin Lecturer", user_type="lecturer", is_admin=True
    ),
}

http_bearer_scheme = HTTPBearer()


async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(http_bearer_scheme),
    client: httpx.AsyncClient = Depends(get_http_client),
) -> User:
    """Dependency to get the current user from token or mock."""
    if settings.MOCK_AUTH_ENABLED:
        token = creds.credentials
        user = MOCK_USERS.get(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid mock user token. Valid are: {list(MOCK_USERS.keys())}",
            )
        return user

    token = creds.credentials
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{settings.HPC_USER_SERVICE_URL}/me", headers=headers
        )
        if response.status_code == 200:
            user_data = response.json()
            if user_data and "data" in user_data and user_data["data"] is not None:
                return User(**user_data["data"])

        logger.warning(
            f"User service validation failed with status {response.status_code}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except httpx.RequestError as e:
        logger.error(f"Could not connect to user service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to user service: {e}",
        )


def get_current_lecturer(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure the user is a lecturer."""
    if user.user_type != "lecturer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only lecturers can perform this action.",
        )
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure the user is an admin."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required.",
        )
    return user
