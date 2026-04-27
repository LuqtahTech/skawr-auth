# Skawr Auth - Shared Authentication Library

Shared authentication and API key management system for all Skawr projects.

## Features

- **User Authentication**: JWT-based authentication with signup/login
- **Project Management**: Multi-project support for users
- **API Key System**: Project-scoped API keys with permissions
- **Frontend Components**: React context and hooks
- **Backend Integration**: FastAPI routers and middleware
- **Type Safety**: Full TypeScript support

## Package Structure

```
skawr-auth/
├── backend/           # Python backend components
│   └── skawr_auth/
│       ├── models/    # SQLAlchemy models
│       ├── schemas/   # Pydantic schemas
│       ├── endpoints/ # FastAPI routers
│       ├── middleware/# Auth middleware
│       └── utils/     # Auth utilities
├── frontend/          # React frontend components
│   └── src/
│       ├── types/     # TypeScript types
│       ├── utils/     # Auth client
│       ├── contexts/  # React context
│       └── components/# UI components
└── shared/            # Shared constants/types
```

## Backend Usage

### 1. Install Dependencies

```bash
pip install -e /path/to/skawr-auth/backend
```

### 2. Setup Models

```python
from skawr_auth.models.base import get_base
from skawr_auth.models.user import create_user_models
from skawr_auth.models.project import create_project_models
from sqlalchemy.ext.declarative import declarative_base

# Use your existing Base or create new one
Base = declarative_base()

# Create models with your base
User, UserSession = create_user_models(Base)
Project, APIKey = create_project_models(Base)
```

### 3. Setup Authentication Router

```python
from fastapi import FastAPI
from skawr_auth.endpoints.auth import create_auth_router
from skawr_auth.utils.auth import create_get_current_user_dependency

app = FastAPI()

# Create get_current_user dependency
get_current_user = create_get_current_user_dependency(User, get_db)

# Create auth router
auth_router = create_auth_router(
    user_model=User,
    db_dependency=get_db,
    get_current_user_func=get_current_user,
    tags=["authentication"]
)

app.include_router(auth_router, prefix="/api/v1/auth")
```

### 4. Setup API Key Authentication

```python
from skawr_auth.middleware.api_key_auth import create_api_key_dependencies

# Create API key dependencies
(
    require_api_key,
    require_api_key_with_permission,
    require_track_permission,
    require_query_permission
) = create_api_key_dependencies(Project, APIKey, User, get_db)

@app.post("/track")
async def track_event(
    event_data: dict,
    auth_data: tuple = Depends(require_track_permission)
):
    project, api_key = auth_data
    # Process event for this project
    pass
```

## Frontend Usage

### 1. Install Dependencies

```bash
npm install /path/to/skawr-auth/frontend
```

### 2. Setup Auth Provider

```tsx
import { AuthProvider } from '@skawr/auth-frontend'

function App() {
  return (
    <AuthProvider config={{ apiBaseUrl: 'http://localhost:8000' }}>
      <YourApp />
    </AuthProvider>
  )
}
```

### 3. Use Auth Hook

```tsx
import { useAuth } from '@skawr/auth-frontend'

function LoginForm() {
  const { login, signup, user, isAuthenticated, logout } = useAuth()

  const handleLogin = async (email: string, password: string) => {
    try {
      await login(email, password)
      // Redirect to dashboard
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  if (isAuthenticated) {
    return <div>Welcome, {user?.name}!</div>
  }

  // Render login form
}
```

## Migration Guide

### From Existing Skawr Projects

1. **Install shared auth package**
2. **Replace existing models** with shared ones
3. **Update imports** to use shared schemas
4. **Replace auth routers** with factory functions
5. **Update frontend** to use shared components

### Example Migration

Before:
```python
from app.models.user import User
from app.api.auth import router
```

After:
```python
from skawr_auth.models.user import User
from skawr_auth.endpoints.auth import create_auth_router

router = create_auth_router(User, get_db, get_current_user)
```

## Development

### Backend Development
```bash
cd backend
pip install -e .
pytest
```

### Frontend Development
```bash
cd frontend
npm install
npm run build
npm test
```

## Benefits

- ✅ **DRY**: No duplicate authentication code
- ✅ **Consistency**: Same auth UX across all Skawr products
- ✅ **Security**: Centralized security updates
- ✅ **Maintenance**: Single place to fix auth bugs
- ✅ **Type Safety**: Full TypeScript support
- ✅ **Flexibility**: Works with existing database setups