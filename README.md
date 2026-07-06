# Skawr Auth — Unified Identity Library

Centralized authentication, authorization, and identity management for all Skawr products. One user account works across Analytics, Search SaaS, Client Dashboard, Admin Dashboard, and Marketplace.

## What's New (Unified Auth v2)

- **Single identity** — One user account across all Skawr products
- **Product enrollments** — Users are enrolled in products with roles (admin/member/viewer)
- **Cross-product SSO** — Log in once, access all enrolled products
- **Connected stores** — Salla/Shopify OAuth data lives in a dedicated table
- **Dual-auth transition** — Legacy tokens from analytics and indexer continue working for 90 days
- **Sync + async support** — Works with both async (analytics) and sync (indexer) SQLAlchemy
- **Key generation** — Built-in CLI for generating deployment secrets
- **Role-based access** — Per-product role hierarchy (admin > member > viewer)

## Quick Start

### Generate Deployment Keys

```bash
# Install the package
pip install -e backend/

# Generate all required keys
python -m skawr_auth --env

# Or use the CLI command
skawr-keygen --env
```

Output:
```
SKAWR_AUTH_SECRET_KEY=<64-char-hex>
SKAWR_AUTH_STORE_ENCRYPTION_KEY=<fernet-key>
```

Add both to your `.env` file. **All services must use the same `SKAWR_AUTH_SECRET_KEY`.**

### Run Migrations

```bash
cd backend
SKAWR_AUTH_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/skawr \
  alembic -c alembic.ini upgrade head
```

## Package Structure

```
skawr-auth/
├── backend/
│   ├── skawr_auth/
│   │   ├── models/           # SQLAlchemy models (User, Enrollment, ConnectedStore, etc.)
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── endpoints/        # FastAPI routers (auth, projects, subscription)
│   │   ├── services/         # Business logic (enrollment, sessions, guest claim)
│   │   ├── middleware/       # API key auth middleware
│   │   ├── utils/            # JWT, config, CORS, roles, resource resolver, keygen
│   │   └── alembic/          # Database migrations
│   ├── tests/                # pytest test suite
│   ├── alembic.ini           # Alembic configuration
│   └── pyproject.toml        # Python package config
├── frontend/
│   └── src/
│       ├── types/            # TypeScript interfaces (User, ProductEnrollment, etc.)
│       ├── utils/            # AuthClient class
│       ├── contexts/         # React AuthProvider + useAuth hook
│       └── components/       # ProductSwitcher, SharedLoginPage
└── .kiro/specs/              # Feature specification docs
```

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SKAWR_AUTH_SECRET_KEY` | **Yes** | — | JWT signing key (generate with `skawr-keygen`) |
| `SKAWR_AUTH_STORE_ENCRYPTION_KEY` | **Yes** | — | Fernet key for encrypting OAuth tokens |
| `SKAWR_AUTH_DATABASE_URL` | **Yes** | — | PostgreSQL connection string |
| `SKAWR_AUTH_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `SKAWR_AUTH_ACCESS_EXPIRE_MINUTES` | No | `15` | Access token lifetime |
| `SKAWR_AUTH_REFRESH_EXPIRE_DAYS` | No | `30` | Refresh token lifetime |
| `SKAWR_AUTH_ALLOWED_ORIGINS` | No | (auto) | CORS origins (JSON array) |
| `SKAWR_AUTH_LEGACY_TOKEN_DEADLINE` | No | — | ISO date after which legacy tokens are rejected |
| `SECRET_KEY` | No | — | Legacy alias for `SKAWR_AUTH_SECRET_KEY` |
| `JWT_SECRET_KEY` | No | — | Legacy alias (indexer compat) |

## Backend Usage

### For Async Services (Analytics)

```python
from skawr_auth.models.user import create_user_models
from skawr_auth.models.enrollment import create_enrollment_models
from skawr_auth.endpoints.auth import create_auth_router
from skawr_auth.utils.auth import create_get_current_user_dependency_async
from skawr_auth.utils.roles import require_product_role, Product, Role

from app.database import Base, get_db

# Create models
User, UserSession = create_user_models(Base)

# Create dependency (with product enrollment check)
get_current_user = create_get_current_user_dependency_async(User, get_db, product="analytics")

# Create router (tokens now include product_enrollments claim)
auth_router = create_auth_router(User, get_db, get_current_user, tags=["auth"])

# Protect endpoints by role
@app.get("/admin/settings")
async def admin_settings(role: str = Depends(require_product_role(Product.ANALYTICS, Role.ADMIN))):
    return {"message": "admin only"}
```

### For Sync Services (Indexer)

```python
from skawr_auth.utils.auth import create_get_current_user_dependency_sync
from skawr_auth.utils.resource_resolver import get_current_user_resources_sync, resolve_legacy_client_to_user_sync

# Sync dependency for the indexer
get_current_user = create_get_current_user_dependency_sync(User, get_db, product="search_saas")

# Resolve user's connected stores
resources = get_current_user_resources_sync(db, user.id, "search_saas")
# resources.connected_stores → [ConnectedStore(...)]
# resources.api_keys → [APIKey(...)]
```

### Dual-Auth (Transition Period)

During migration, the indexer accepts both legacy and unified tokens:

```python
from skawr_auth.utils.auth import verify_token_for_product, detect_token_format

# verify_token_for_product handles all three formats:
# - "unified": checks product_enrollments claim
# - "legacy_indexer": returns "admin" (legacy clients were always admins)
# - "legacy_analytics": returns "member" (enrolled everywhere)
role = verify_token_for_product(token, "search_saas")
```

### Guest Claim Flow

```python
from skawr_auth.services.guest_claim import claim_guest_account

# When a guest client (no email) later adds credentials:
result = await claim_guest_account(
    db,
    legacy_client_id=guest_uuid,
    email="merchant@example.com",
    password="secure_password",
    name="Merchant Name",
)
# result.user_id, result.is_new_user, result.enrollment_created
```

### Subscription Tier Management

```python
from skawr_auth.endpoints.subscription import create_subscription_router

# Internal endpoint for payment system (Polar.sh) to update tiers
subscription_router = create_subscription_router(
    user_model=User,
    audit_model=SubscriptionTierAudit,
    db_dependency=get_db,
    require_service_api_key=my_service_key_dependency,
)
# PUT /internal/subscription-tier/{user_id} {"tier": "growth"}
```

## Frontend Usage

### AuthProvider with Product Context

```tsx
import { AuthProvider, useAuth, ProductSwitcher, SharedLoginPage } from '@skawr/auth-frontend'

function App() {
  return (
    <AuthProvider config={{ apiBaseUrl: 'https://analytics-api.ziyad.one', product: 'analytics' }}>
      <Dashboard />
    </AuthProvider>
  )
}
```

### Product-Aware Auth Hook

```tsx
import { useAuth } from '@skawr/auth-frontend'

function Dashboard() {
  const { user, isAuthenticated, getEnrolledProducts, hasProductAccess } = useAuth()

  // Check if user has access to search SaaS
  if (hasProductAccess('search_saas')) {
    // Show link to SaaS dashboard
  }

  // Get all enrolled products for the product switcher
  const products = getEnrolledProducts()
  // → [{ product: "analytics", role: "admin" }, { product: "search_saas", role: "member" }]
}
```

### Product Switcher

```tsx
import { ProductSwitcher } from '@skawr/auth-frontend'

<ProductSwitcher
  products={getEnrolledProducts()}
  currentProduct="analytics"
  onSwitch={(product) => window.location.href = productUrls[product]}
/>
```

### Shared Login Page

```tsx
import { SharedLoginPage } from '@skawr/auth-frontend'

function LoginPage() {
  return (
    <SharedLoginPage
      config={{ apiBaseUrl: 'https://analytics-api.ziyad.one' }}
      redirectProduct="analytics"
      onSuccess={(user) => router.push('/dashboard')}
      title="Sign in to Skawr Analytics"
    />
  )
}
```

## Database Schema

Core tables managed by this library:

| Table | Purpose |
|-------|---------|
| `users` | Single identity across all products |
| `user_sessions` | Refresh token tracking + device/IP/product metadata |
| `product_enrollments` | User ↔ product membership with roles |
| `connected_stores` | Salla/Shopify OAuth tokens + store metadata |
| `api_keys` | Product-scoped API keys with resource binding |
| `projects` | Analytics project ownership |
| `organizations` | (dormant) Team/org support |
| `organization_members` | (dormant) Org membership |
| `user_identity_providers` | (dormant) OAuth social login links |
| `subscription_tier_audit` | Tier change history for billing audit |

## Key Generation

The `skawr-keygen` CLI generates cryptographically secure keys:

```bash
# Generate all keys in .env format
skawr-keygen --env

# Generate only the JWT secret
skawr-keygen --jwt-only

# Generate only the encryption key
skawr-keygen --encryption-only

# Or via python module
python -m skawr_auth --env
python -m skawr_auth.utils.keygen --env
```

## Development

```bash
# Backend
cd backend
pip install -e ".[dev]"
pytest

# Frontend
cd frontend
npm install
npm run build
npm test
```

## Migration from Previous Version

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed steps on migrating from the per-product auth setup to unified auth.

Key changes:
- `SECRET_KEY` → `SKAWR_AUTH_SECRET_KEY` (aliases still work for 90 days)
- `create_get_current_user_dependency()` → now accepts optional `product` parameter
- Tokens now include `product_enrollments` claim (old tokens still work for 90 days)
- API keys gain `user_id`, `product`, `resource_id`, `resource_type` columns
