import hashlib
import secrets
from typing import List, Any, Callable
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ..schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    APIKeyCreate, APIKeyUpdate, APIKeyResponse, APIKeyCreateResponse
)


def create_projects_router(
    user_model: Any,
    project_model: Any,
    api_key_model: Any,
    db_dependency: Any,
    get_current_user_func: Callable,
    prefix: str = "",
    tags: list = None
) -> APIRouter:
    """
    Factory function to create projects router.

    Args:
        user_model: The User model class
        project_model: The Project model class
        api_key_model: The APIKey model class
        db_dependency: Database dependency function
        get_current_user_func: Function to get current user from token
        prefix: Router prefix (optional)
        tags: Router tags (optional)

    Returns:
        Configured FastAPI router
    """

    router = APIRouter(prefix=prefix, tags=tags or ["projects"])

    @router.get("/", response_model=List[ProjectResponse])
    async def list_projects(
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """List all projects for the current user"""
        result = await db.execute(
            select(project_model, func.count(api_key_model.id).label("api_keys_count"))
            .outerjoin(api_key_model)
            .where(project_model.user_id == current_user.id)
            .group_by(project_model.id)
            .order_by(project_model.created_at.desc())
        )

        projects_data = []
        for project, api_keys_count in result.all():
            project_dict = {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "domain": project.domain,
                "is_active": project.is_active,
                "settings": project.settings,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
                "api_keys_count": api_keys_count
            }
            projects_data.append(ProjectResponse(**project_dict))

        return projects_data

    @router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
    async def create_project(
        project_data: ProjectCreate,
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """Create a new project"""
        project = project_model(
            user_id=current_user.id,
            name=project_data.name,
            description=project_data.description,
            domain=project_data.domain,
            settings=project_data.settings or {}
        )

        db.add(project)
        await db.commit()
        await db.refresh(project)

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            domain=project.domain,
            is_active=project.is_active,
            settings=project.settings,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
            api_keys_count=0
        )

    @router.get("/{project_id}", response_model=ProjectResponse)
    async def get_project(
        project_id: str,
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """Get a specific project"""
        result = await db.execute(
            select(project_model, func.count(api_key_model.id).label("api_keys_count"))
            .outerjoin(api_key_model)
            .where(project_model.id == project_id, project_model.user_id == current_user.id)
            .group_by(project_model.id)
        )

        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")

        project, api_keys_count = row

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            domain=project.domain,
            is_active=project.is_active,
            settings=project.settings,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
            api_keys_count=api_keys_count
        )

    @router.put("/{project_id}", response_model=ProjectResponse)
    async def update_project(
        project_id: str,
        project_data: ProjectUpdate,
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """Update a project"""
        result = await db.execute(
            select(project_model).where(project_model.id == project_id, project_model.user_id == current_user.id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Update fields
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        await db.commit()
        await db.refresh(project)

        # Get API keys count
        api_keys_result = await db.execute(
            select(func.count(api_key_model.id)).where(api_key_model.project_id == project.id)
        )
        api_keys_count = api_keys_result.scalar()

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            domain=project.domain,
            is_active=project.is_active,
            settings=project.settings,
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
            api_keys_count=api_keys_count
        )

    @router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(
        project_id: str,
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """Delete a project"""
        result = await db.execute(
            select(project_model).where(project_model.id == project_id, project_model.user_id == current_user.id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        await db.delete(project)
        await db.commit()

    # API Key endpoints
    @router.get("/{project_id}/api-keys", response_model=List[APIKeyResponse])
    async def list_api_keys(
        project_id: str,
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """List API keys for a project"""
        # Verify project ownership
        project_result = await db.execute(
            select(project_model).where(project_model.id == project_id, project_model.user_id == current_user.id)
        )
        if not project_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

        result = await db.execute(
            select(api_key_model).where(api_key_model.project_id == project_id).order_by(api_key_model.created_at.desc())
        )

        api_keys = []
        for api_key in result.scalars():
            api_keys.append(APIKeyResponse(
                id=str(api_key.id),
                project_id=str(api_key.project_id),
                name=api_key.name,
                key_prefix=api_key.key_prefix,
                permissions=api_key.permissions,
                rate_limit=api_key.rate_limit,
                is_active=api_key.is_active,
                last_used_at=api_key.last_used_at.isoformat() if api_key.last_used_at else None,
                expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
                created_at=api_key.created_at.isoformat()
            ))

        return api_keys

    @router.post("/{project_id}/api-keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
    async def create_api_key(
        project_id: str,
        api_key_data: APIKeyCreate,
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """Create a new API key for a project"""
        # Verify project ownership
        project_result = await db.execute(
            select(project_model).where(project_model.id == project_id, project_model.user_id == current_user.id)
        )
        if not project_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

        # Generate API key
        api_key_value = f"ska_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key_value.encode()).hexdigest()
        key_prefix = api_key_value[:8]

        api_key = api_key_model(
            project_id=project_id,
            name=api_key_data.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=api_key_data.permissions,
            rate_limit=api_key_data.rate_limit,
            expires_at=api_key_data.expires_at
        )

        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)

        return APIKeyCreateResponse(
            id=str(api_key.id),
            project_id=str(api_key.project_id),
            name=api_key.name,
            key=api_key_value,  # Only time we show the full key
            key_prefix=api_key.key_prefix,
            permissions=api_key.permissions,
            rate_limit=api_key.rate_limit,
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,
            created_at=api_key.created_at.isoformat()
        )

    @router.delete("/{project_id}/api-keys/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_api_key(
        project_id: str,
        api_key_id: str,
        current_user: Any = Depends(get_current_user_func),
        db: AsyncSession = Depends(db_dependency)
    ):
        """Delete an API key"""
        # Verify project ownership
        project_result = await db.execute(
            select(project_model).where(project_model.id == project_id, project_model.user_id == current_user.id)
        )
        if not project_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Project not found")

        # Get API key
        result = await db.execute(
            select(api_key_model).where(api_key_model.id == api_key_id, api_key_model.project_id == project_id)
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")

        await db.delete(api_key)
        await db.commit()

    return router