from typing import Annotated
from fastapi import Depends, HTTPException, status
from app.auth import get_current_user


def require_admin(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Dependency — allows only users with role 'Admin'."""
    if current_user.get("role", "").lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return current_user


def build_pinecone_filter(department: str) -> dict:
    """Build Pinecone metadata filter so results only include chunks the user's department can access."""
    return {"allowed_departments": {"$in": [department]}}
