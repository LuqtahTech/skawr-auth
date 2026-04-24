import hashlib
import logging
from typing import Optional, Tuple, Any
from datetime import datetime
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_api_key_dependencies(
    project_model: Any,
    api_key_model: Any,
    user_model: Any,
    db_dependency: Any
):
    """
    Factory function to create API key authentication dependencies.
    This allows the auth library to work with different database setups.

    Args:
        project_model: The Project model class
        api_key_model: The APIKey model class
        user_model: The User model class
        db_dependency: The database dependency function (e.g., get_db)

    Returns:
        Tuple of dependency functions
    """

    async def require_api_key(
        api_key: Optional[str] = Depends(api_key_header),
        db: AsyncSession = Depends(db_dependency)
    ) -> Tuple[Any, Any]:
        """
        FastAPI dependency that validates X-API-Key header.
        Returns the project and API key if valid.
        """
        if not api_key:
            raise HTTPException(status_code=401, detail="X-API-Key header required")

        # Hash the provided API key for comparison
        provided_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        try:
            # Look up APIKey by hash
            result = await db.execute(
                select(api_key_model, project_model, user_model)
                .join(project_model, api_key_model.project_id == project_model.id)
                .join(user_model, project_model.user_id == user_model.id)
                .where(
                    api_key_model.key_hash == provided_key_hash,
                    api_key_model.is_active == True,
                    project_model.is_active == True,
                    user_model.is_active == True
                )
            )

            row = result.first()
            if not row:
                raise HTTPException(status_code=401, detail="Invalid API Key")

            api_key_obj, project, user = row

            # Check key expiration
            if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
                raise HTTPException(status_code=401, detail="Expired API Key")

            # Update last_used_at timestamp
            api_key_obj.last_used_at = datetime.utcnow()
            await db.commit()

            return project, api_key_obj

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API Key validation error: {e}")
            raise HTTPException(status_code=500, detail="Authentication error")

    def require_api_key_with_permission(permission: str):
        """
        Factory function to create API key dependency with specific permission requirement.
        """
        async def _require_permission(
            api_key: Optional[str] = Depends(api_key_header),
            db: AsyncSession = Depends(db_dependency)
        ) -> Tuple[Any, Any]:
            project, api_key_obj = await require_api_key(api_key, db)

            if permission not in api_key_obj.permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"API key does not have '{permission}' permission"
                )

            return project, api_key_obj

        return _require_permission

    # Common permission dependencies
    require_track_permission = require_api_key_with_permission("track")
    require_query_permission = require_api_key_with_permission("query")

    return (
        require_api_key,
        require_api_key_with_permission,
        require_track_permission,
        require_query_permission
    )