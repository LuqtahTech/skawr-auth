# Skawr Shared Authentication Migration Guide

This guide explains how to migrate existing Skawr projects to use the shared authentication library, and how to integrate shared auth into new projects.

## Overview

The shared authentication library (`skawr-auth`) provides:
- **Backend**: User authentication, project/API key management, FastAPI routers and dependencies
- **Frontend**: React authentication context and hooks for Next.js applications
- **Factory Pattern**: Flexible integration with existing SQLAlchemy setups

## Prerequisites

- Python 3.9+ for backend projects
- Node.js 18+ for frontend projects
- Existing SQLAlchemy setup (for backend integration)

## Backend Migration

### Step 1: Install the Shared Auth Package

```bash
# Install in development mode (recommended for Skawr projects)
pip install -e /path/to/skawr-auth/backend

# Or install from package index when published
pip install skawr-auth
```

### Step 2: Create Integration File

Create a new file `app/shared_auth.py` (or similar) to integrate with your existing setup:

```python
"""Shared authentication integration for your-project.

This module integrates the shared skawr-auth library with your project,
providing authentication models and dependencies that work with the existing database setup.
"""

from skawr_auth.models.base import get_base
from skawr_auth.models.user import create_user_models
from skawr_auth.models.project import create_project_models
from skawr_auth.endpoints.auth import create_auth_router
from skawr_auth.endpoints.projects import create_projects_router
from skawr_auth.dependencies.auth import create_auth_dependencies
from skawr_auth.dependencies.projects import create_project_dependencies

from app.database import Base, get_db  # Your existing database setup

# Initialize shared auth with your project's Base
get_base(Base)

# Create auth models using shared library
User, UserSession = create_user_models(Base)
Project, APIKey = create_project_models(Base)

# Create auth dependencies
auth_deps = create_auth_dependencies(User, UserSession, get_db)
project_deps = create_project_dependencies(Project, APIKey, get_db)

# Extract individual dependencies for convenience
get_current_user = auth_deps["get_current_user"]
get_optional_user = auth_deps["get_optional_user"]
get_current_project = project_deps["get_current_project"]
get_optional_project = project_deps["get_optional_project"]

# Create routers
auth_router = create_auth_router(
    user_model=User,
    user_session_model=UserSession,
    db_dependency=get_db,
    get_current_user_func=get_current_user,
    prefix="/auth",
    tags=["authentication"]
)

projects_router = create_projects_router(
    project_model=Project,
    api_key_model=APIKey,
    db_dependency=get_db,
    get_current_user_func=get_current_user,
    prefix="/projects",
    tags=["projects"]
)

# Export all models and dependencies for use throughout your project
__all__ = [
    "User",
    "UserSession",
    "Project",
    "APIKey",
    "get_current_user",
    "get_optional_user",
    "get_current_project",
    "get_optional_project",
    "auth_router",
    "projects_router",
]
```

### Step 3: Update Existing Imports

Replace your existing auth model imports throughout your codebase:

**Before:**
```python
from app.models import User, UserSession, APIClient, APIKey
```

**After:**
```python
from app.shared_auth import User, UserSession, Project as APIClient, APIKey
```

**Note**: If your project uses `APIClient` as the project model name, alias `Project` to maintain compatibility.

### Step 4: Add Routers to Main Application

Update your main FastAPI application file:

```python
from app.shared_auth import auth_router, projects_router

app = FastAPI(...)

# Include shared auth routers
app.include_router(auth_router)
app.include_router(projects_router)
```

### Step 5: Run Database Migrations

The shared auth models are designed to be compatible with existing auth table structures. However, you may need to run migrations if there are schema differences:

```bash
# Generate migration (if using Alembic)
alembic revision --autogenerate -m "Migrate to shared auth"

# Review the generated migration and apply
alembic upgrade head
```

## Frontend Migration

### Step 1: Install Shared Auth Frontend Package

```bash
npm install @skawr/auth-frontend
```

### Step 2: Update Layout/App Root

Replace your existing auth provider with the shared one:

**Before:**
```tsx
import { AuthProvider } from '@/contexts/AuthContext'
```

**After:**
```tsx
import { AuthProvider } from '@skawr/auth-frontend'

const authConfig = {
  apiBaseUrl: process.env.NODE_ENV === 'production'
    ? 'https://your-production-api.com'
    : 'http://localhost:8000'
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider config={authConfig}>
          {children}
        </AuthProvider>
      </body>
    </html>
  )
}
```

### Step 3: Update Component Imports

Replace existing auth hook imports:

**Before:**
```tsx
import { useAuth } from '@/contexts/AuthContext'
```

**After:**
```tsx
import { useAuth } from '@skawr/auth-frontend'
```

## New Project Setup

For new projects, follow these steps to integrate shared auth from the start:

### Backend Setup

1. Install the shared auth package
2. Create the integration file (as shown above)
3. Include the routers in your FastAPI app
4. Run initial database migrations

### Frontend Setup

1. Install the frontend package
2. Add the AuthProvider to your app root
3. Use the shared auth hooks in your components

## Common Issues and Solutions

### Python Version Compatibility

**Issue**: `skawr-auth` requires Python 3.9+ but your project uses an older version.

**Solution**: Update your project to Python 3.9+ or request a compatible version of the shared library.

### Import Errors

**Issue**: `ModuleNotFoundError: No module named 'skawr_auth'`

**Solution**:
- Ensure the package is installed in the correct virtual environment
- Use pip list to verify installation
- Reinstall with `pip install -e /path/to/skawr-auth/backend --force-reinstall`

### Database Schema Conflicts

**Issue**: Existing auth tables have different schemas than shared models.

**Solution**:
- Review the shared auth models in `skawr_auth/models/`
- Create Alembic migrations to align schemas
- Consider gradual migration approach

### Virtual Environment Issues

**Issue**: Package installed but not found in virtual environment.

**Solution**:
- Verify virtual environment activation: `which python`
- Check Python path includes venv: `python -c "import sys; print(sys.path)"`
- Reinstall package in correct environment

## Migration Checklist

### Backend Migration
- [ ] Install skawr-auth package
- [ ] Create integration file (`app/shared_auth.py`)
- [ ] Update all model imports
- [ ] Add routers to main application
- [ ] Run database migrations
- [ ] Test authentication endpoints
- [ ] Verify existing functionality still works

### Frontend Migration
- [ ] Install @skawr/auth-frontend package
- [ ] Update AuthProvider in app root
- [ ] Update auth hook imports
- [ ] Test login/logout functionality
- [ ] Verify protected routes work
- [ ] Test authentication state persistence

### Testing
- [ ] Start backend server successfully
- [ ] Start frontend application successfully
- [ ] Authentication endpoints respond
- [ ] Login/logout flow works
- [ ] Protected routes require authentication
- [ ] API calls include proper authentication

## Best Practices

1. **Test in Development First**: Always test the migration in a development environment before applying to production.

2. **Gradual Migration**: For large projects, consider migrating one module at a time.

3. **Database Backups**: Always backup your database before running migrations.

4. **Version Pinning**: Pin the shared auth package version in your requirements for stability.

5. **Documentation**: Update your project's README to reflect the shared auth usage.

## Getting Help

If you encounter issues during migration:

1. Check this guide for common solutions
2. Review the shared auth library documentation
3. Examine the successful migrations in skawr-analytics and skawr-indexer
4. Create an issue in the skawr-auth repository

## Example Projects

See these projects for reference implementations:

- **skawr-analytics**: Full stack application with frontend and backend integration
- **skawr-indexer**: Backend-only service integration
- **skawr-auth**: The shared library itself with example usage

---

*Last Updated: April 2026*
*Version: 1.0*