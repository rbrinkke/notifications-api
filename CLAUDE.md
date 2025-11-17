# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Notifications API** is a FastAPI-based microservice for managing user notifications in the Activity Platform. It follows a stored procedure architecture pattern, connecting to the centralized PostgreSQL database (`activitydb`) and using the `activity` schema for all database operations.

**Key Characteristics:**
- **Architecture**: Stored procedure-only pattern (database team owns schema)
- **Authentication**: JWT token validation + service-to-service tokens
- **Database**: Centralized PostgreSQL (`activity-postgres-db` container)
- **Caching**: Shared Redis (`auth-redis` container)
- **Logging**: Structured JSON logging with correlation IDs
- **Port**: 8006 (external) → 8000 (internal)
- **Network**: `activity-network` (shared with other services)

## Quick Start

### Prerequisites

The **infrastructure must be running first**:
```bash
# From repository root (/mnt/d/activity/)
./scripts/start-infra.sh
```

This starts:
- PostgreSQL (`activity-postgres-db` on port 5441)
- Redis (`auth-redis` on port 6379)
- MailHog (optional email testing)

### Build and Start

```bash
# Build fresh image (CRITICAL after code changes)
docker compose build --no-cache

# Start service
docker compose up -d

# View logs
docker compose logs -f notifications-api

# Check health
curl http://localhost:8006/health
```

### Access API Documentation

Once running:
- **Swagger UI**: http://localhost:8006/docs
- **ReDoc**: http://localhost:8006/redoc
- **Health Check**: http://localhost:8006/health

### Local Development (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Edit .env with correct database credentials
# Ensure DB_HOST=localhost (not activity-postgres-db)

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Architecture Patterns

### Stored Procedure Pattern

**All database operations** go through PostgreSQL stored procedures in the `activity` schema:

```python
# Service layer calls stored procedures
result = await db.execute_sp(
    "activity.sp_get_user_notifications",
    user_id,
    status_str,
    type_str,
    limit,
    offset,
    include_premium_only
)
```

**Why stored procedures?**
- Database team controls schema evolution
- Better for CQRS architecture
- Easier auditing and optimization
- Implementation changes don't require API changes

**Available stored procedures** (defined in `sqlschema.sql`):
- `activity.sp_get_user_notifications` - Paginated notification list
- `activity.sp_get_notification_by_id` - Single notification retrieval
- `activity.sp_mark_notification_as_read` - Mark single as read
- `activity.sp_mark_notifications_as_read_bulk` - Bulk mark read
- `activity.sp_delete_notification` - Archive/delete notification
- `activity.sp_get_unread_count` - Count unread by type
- `activity.sp_create_notification` - Create notification (internal)
- `activity.sp_get_user_notification_settings` - Get user preferences
- `activity.sp_update_user_notification_settings` - Update preferences

### JWT Authentication Flow

**User Endpoints** (8 endpoints):
```python
from app.core.security import get_current_user, TokenData

@router.get("/notifications")
async def get_notifications(
    current_user: TokenData = Depends(get_current_user)
):
    user_id = UUID(current_user.user_id)
    subscription_level = current_user.subscription_level
    # subscription_level determines access to premium features
```

**Service Endpoints** (1 endpoint):
```python
from app.core.security import verify_service_token

@router.post("/notifications")
async def create_notification(
    authorization: str = Header(None)
):
    # Verify service token
    token = authorization.replace("Bearer ", "")
    if not verify_service_token(token):
        raise UnauthorizedException()
```

**Critical Environment Variables**:
```bash
JWT_SECRET=dev-secret-key-change-in-production  # MUST match auth-api
JWT_ALGORITHM=HS256
SERVICE_TOKEN=shared-secret-token-change-in-production
```

### Subscription-Based Features

The API respects user subscription levels extracted from JWT tokens:

```python
# Premium features (profile_view, new_favorite notifications)
is_premium = current_user.subscription_level in ["club", "premium"]

# Only premium users see premium-exclusive notification types
notifications, total = await notification_service.get_user_notifications(
    user_id=user_id,
    include_premium_only=is_premium,
    ...
)
```

**Subscription Levels**:
- `free`: Standard notifications only
- `club`: All notifications (premium features enabled)
- `premium`: All notifications (premium features enabled)

### Structured Logging

All logging uses `structlog` with JSON output in production:

```python
import structlog
logger = structlog.get_logger()

# Structured logging with context
logger.info(
    "notifications_retrieved",
    user_id=str(user_id),
    count=len(notifications),
    total=total_count
)

# Correlation IDs automatically injected by middleware
# X-Correlation-ID header tracks requests across services
```

**Log Aggregation**: Logs are collected by Promtail and sent to Loki (observability stack).

## Database Configuration

### Connection Details

**Production/Docker**:
```bash
DB_HOST=activity-postgres-db  # Container name
DB_PORT=5432                   # Internal port
DB_NAME=activitydb
DB_USER=postgres
DB_PASSWORD=postgres_secure_password_change_in_prod
```

**Local Development**:
```bash
DB_HOST=localhost              # Direct connection
DB_PORT=5441                   # External port mapping
# Other settings same as above
```

### Database Schema

The service uses these tables from the `activity` schema:

**Primary Tables**:
- `activity.notifications` (12 columns) - Core notification data
  - `notification_id`, `user_id`, `actor_user_id`, `notification_type`
  - `target_type`, `target_id`, `title`, `message`, `status`
  - `created_at`, `read_at`, `payload` (JSONB)

- `activity.notification_preferences` (8 columns) - User notification settings
  - `user_id`, `email_enabled`, `push_enabled`, `in_app_enabled`
  - `enabled_types` (JSONB array), `quiet_hours_start`, `quiet_hours_end`

**Referenced Tables**:
- `activity.users` (34 columns) - User information for actor details
- `activity.user_settings` (14 columns) - User preferences

### Connection Pool

Configured in `app/core/database.py`:
```python
self.pool = await asyncpg.create_pool(
    database_url,
    min_size=10,      # Minimum connections
    max_size=100,     # Maximum connections
    command_timeout=60  # Query timeout in seconds
)
```

## API Endpoints

### User Endpoints (JWT Required)

**List Notifications**:
```bash
GET /api/v1/notifications
Query params: ?status=unread&type=comment&limit=20&offset=0
```

**Get Single Notification**:
```bash
GET /api/v1/notifications/{notification_id}
```

**Mark as Read**:
```bash
PATCH /api/v1/notifications/{notification_id}/read
```

**Bulk Mark Read**:
```bash
POST /api/v1/notifications/mark-read
Body: {"notification_ids": [...], "notification_type": "comment"}
```

**Delete/Archive**:
```bash
DELETE /api/v1/notifications/{notification_id}?permanent=false
```

**Unread Count**:
```bash
GET /api/v1/notifications/unread/count
```

**Get Settings**:
```bash
GET /api/v1/notifications/settings
```

**Update Settings**:
```bash
PATCH /api/v1/notifications/settings
Body: {"email_enabled": true, "enabled_types": [...]}
```

### Internal Endpoints (Service Token Required)

**Create Notification**:
```bash
POST /api/v1/notifications
Header: Authorization: Bearer {SERVICE_TOKEN}
Body: {
  "user_id": "...",
  "actor_user_id": "...",
  "notification_type": "comment",
  "target_type": "post",
  "target_id": "...",
  "title": "New comment",
  "message": "..."
}
```

### Health Check

```bash
GET /health
Response: {"status": "healthy", "database": "connected"}
```

## Testing API Endpoints

### Generate Test JWT

```bash
# Generate JWT token for testing (requires python-jose)
python3 -c "
import jwt
from datetime import datetime, timedelta

secret = 'dev-secret-key-change-in-production'
payload = {
    'sub': 'test-user-uuid',
    'email': 'test@example.com',
    'subscription_level': 'premium',
    'exp': datetime.utcnow() + timedelta(days=1)
}
token = jwt.encode(payload, secret, algorithm='HS256')
print(token)
"
```

### Test User Endpoints

```bash
# Set token
export TOKEN="your-jwt-token-here"

# Get notifications
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8006/api/v1/notifications?limit=10"

# Get unread count
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8006/api/v1/notifications/unread/count"

# Mark notification as read
curl -X PATCH \
  -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8006/api/v1/notifications/{id}/read"
```

### Test Service Endpoints

```bash
# Set service token
export SERVICE_TOKEN="shared-secret-token-change-in-production"

# Create notification (internal service call)
curl -X POST \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-uuid",
    "notification_type": "comment",
    "target_type": "post",
    "target_id": "post-uuid",
    "title": "New comment on your post",
    "message": "Someone commented on your post"
  }' \
  "http://localhost:8006/api/v1/notifications"
```

## Development Workflow

### After Code Changes

**CRITICAL**: Docker restart doesn't pick up code changes. You MUST rebuild:

```bash
# Wrong (uses old code)
docker compose restart notifications-api

# Right (builds with new code)
docker compose build --no-cache notifications-api
docker compose restart notifications-api

# Or full rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Adding New Stored Procedures

1. **Database team adds procedure** to `sqlschema.sql`
2. **Apply to database**:
   ```bash
   docker exec -it activity-postgres-db psql -U postgres -d activitydb < sqlschema.sql
   ```
3. **Add service method** in `app/services/notification_service.py`:
   ```python
   async def new_operation(self, user_id: UUID, ...):
       result = await db.execute_sp(
           "activity.sp_new_procedure",
           user_id,
           other_params
       )
       return format_result(result)
   ```
4. **Add route** in `app/routes/notifications.py`
5. **Rebuild container**: `docker compose build --no-cache`

### Adding New Endpoints

1. **Define schema** in `app/schemas/notifications.py`:
   ```python
   class NewRequest(BaseModel):
       field: str

   class NewResponse(BaseModel):
       result: str
   ```
2. **Add route** in `app/routes/notifications.py`:
   ```python
   @router.post("/new-endpoint", response_model=NewResponse)
   async def new_endpoint(
       request: NewRequest,
       current_user: TokenData = Depends(get_current_user)
   ):
       # Implementation
   ```
3. **Test endpoint** via Swagger UI or curl
4. **Rebuild container** if running in Docker

### Debugging Connection Issues

```bash
# Check database connection
docker exec activity-postgres-db psql -U postgres -d activitydb -c "SELECT 1;"

# Check Redis connection
docker exec auth-redis redis-cli --no-auth-warning ping

# Check network connectivity
docker network ls | grep activity-network
docker network inspect activity-network

# View service logs
docker compose logs -f notifications-api

# Check environment variables
docker exec notifications-api env | grep DB_
```

### Working with Structured Logs

```bash
# View all logs
docker compose logs -f notifications-api

# Filter by log level
docker compose logs -f notifications-api | grep ERROR

# Filter by event
docker compose logs -f notifications-api | grep "notification_created"

# With Loki (via Grafana)
# Query: {service_name="notifications-api"} |= "ERROR"
# Query: {service_name="notifications-api"} | json | user_id="specific-uuid"
```

## Common Issues and Solutions

### Database Connection Failures

**Symptom**: `connection refused` or `database_connection_failed`

**Solution**:
```bash
# Ensure infrastructure is running
docker ps | grep activity-postgres-db

# If not running, start infrastructure
cd /mnt/d/activity
./scripts/start-infra.sh

# Check connection from service
docker exec notifications-api env | grep DB_HOST
# Should be: activity-postgres-db
```

### JWT Validation Errors

**Symptom**: `Invalid authentication credentials` (401)

**Solution**:
```bash
# Verify JWT_SECRET matches auth-api
cd /mnt/d/activity/auth-api
cat .env | grep JWT_SECRET_KEY

cd /mnt/d/activity/notifications-api
cat docker-compose.yml | grep JWT_SECRET

# They MUST be identical!
# If different, update docker-compose.yml and rebuild
```

### Service Token Failures

**Symptom**: `Unauthorized` when calling POST /notifications

**Solution**:
```bash
# Check SERVICE_TOKEN in docker-compose.yml
cat docker-compose.yml | grep SERVICE_TOKEN

# Use same token in Authorization header
curl -H "Authorization: Bearer shared-secret-token-change-in-production" ...
```

### Port Conflicts

**Symptom**: `port is already allocated`

**Solution**:
```bash
# Check what's using port 8006
netstat -tuln | grep 8006

# Stop conflicting service or change port in docker-compose.yml
ports:
  - "8007:8000"  # Use different external port
```

### Stored Procedure Not Found

**Symptom**: `function activity.sp_xxx does not exist`

**Solution**:
```bash
# Apply SQL schema to database
docker exec -i activity-postgres-db psql -U postgres -d activitydb < sqlschema.sql

# Verify procedure exists
docker exec activity-postgres-db psql -U postgres -d activitydb \
  -c "\df activity.sp_*"
```

## Configuration

### Environment Variables

Required in `docker-compose.yml` or `.env`:

```bash
# Database
DB_HOST=activity-postgres-db
DB_PORT=5432
DB_NAME=activitydb
DB_USER=postgres
DB_PASSWORD=postgres_secure_password_change_in_prod

# Authentication
JWT_SECRET=dev-secret-key-change-in-production  # MUST match auth-api
JWT_ALGORITHM=HS256
SERVICE_TOKEN=shared-secret-token-change-in-production

# Redis
REDIS_HOST=auth-redis
REDIS_PORT=6379
REDIS_DB=0

# API
API_V1_PREFIX=/api/v1
PROJECT_NAME=Notifications API
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=*
ENABLE_DOCS=true

# Optional integrations
EMAIL_API_URL=http://email-api:8000
EMAIL_API_KEY=optional-api-key
```

### Notification Types

Defined in `activity.notification_type` enum:
- `activity_invite` - Invitation to activity
- `activity_reminder` - Activity reminder
- `activity_update` - Activity details changed
- `community_invite` - Community invitation
- `new_member` - New community member
- `new_post` - New community post
- `comment` - Comment on content
- `reaction` - Reaction to content
- `mention` - User mention
- `profile_view` - Profile view (premium only)
- `new_favorite` - New favorite (premium only)
- `system` - System notification

### Notification Status

- `unread` - Not yet read by user
- `read` - Read by user (read_at timestamp set)
- `archived` - Archived/deleted by user

## Integration with Other Services

### Service Discovery

Services communicate via container names on `activity-network`:
- **auth-api**: `http://auth-api:8000`
- **email-service**: `http://email-api:8000`
- **community-api**: `http://community-api:8000`
- etc.

### Creating Notifications from Other Services

Other services call POST `/api/v1/notifications` with service token:

```python
import httpx

async def send_notification(user_id: str, notification_type: str, ...):
    response = await httpx.post(
        "http://notifications-api:8000/api/v1/notifications",
        headers={
            "Authorization": f"Bearer {SERVICE_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "user_id": user_id,
            "notification_type": notification_type,
            "target_type": "post",
            "target_id": target_id,
            "title": "Notification title",
            "message": "Optional message"
        }
    )
    return response.json()
```

### User Preference Checking

Notifications respect user preferences (stored procedures handle this):
- If user disabled notification type → notification not created
- If quiet hours active → notification queued/delayed
- Email/push preferences respected

## Production Deployment

### Pre-Deployment Checklist

- [ ] Change `JWT_SECRET` to strong random string (32+ chars)
- [ ] Change `SERVICE_TOKEN` to secure random string
- [ ] Change `DB_PASSWORD` to secure password
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Set `LOG_LEVEL=INFO` or `WARNING`
- [ ] Configure proper `CORS_ORIGINS` (not `*`)
- [ ] Set `ENABLE_DOCS=false` (disable Swagger UI)
- [ ] Configure email service integration
- [ ] Setup monitoring alerts (Grafana/Prometheus)

### Security Best Practices

1. **Token Security**: Rotate JWT_SECRET and SERVICE_TOKEN regularly
2. **Database Access**: Use connection pooling limits (already configured)
3. **Rate Limiting**: Redis-based rate limiting (future enhancement)
4. **CORS**: Restrict to known origins in production
5. **Logging**: Avoid logging sensitive user data
6. **API Docs**: Disable in production (`ENABLE_DOCS=false`)

### Monitoring

**Health Check**: Monitor `GET /health` endpoint
**Metrics**: Prometheus metrics available at `/metrics` (future enhancement)
**Logs**: Structured logs sent to Loki for aggregation
**Alerts**: Configure Grafana alerts for:
- Database connection failures
- High error rates
- Slow query performance

## Dependencies

From `requirements.txt`:
- `fastapi==0.104.1` - Web framework
- `uvicorn[standard]==0.24.0` - ASGI server
- `pydantic==2.5.0` - Data validation
- `pydantic-settings==2.1.0` - Configuration management
- `asyncpg==0.29.0` - PostgreSQL async driver
- `python-jose[cryptography]==3.3.0` - JWT handling
- `structlog==23.2.0` - Structured logging
- `slowapi==0.1.9` - Rate limiting (future use)
- `redis==5.0.1` - Redis client
- `python-multipart==0.0.6` - Multipart form support

## Documentation

Additional documentation:
- `README.md` - Basic setup instructions
- `MIGRATION_TO_CENTRAL_DB.md` - Migration details and port allocations
- `PRODUCTION.md` - Production deployment guide (if exists)
- `QUALITY_CHECK_REPORT.md` - Code quality analysis (if exists)
- `sqlschema.sql` - Complete database schema with stored procedures

## Related Services

Part of the Activity Platform microservices:
- **auth-api** (8000): User authentication and JWT issuance
- **moderation-api** (8002): Content moderation
- **community-api** (8003): Communities and posts
- **participation-api** (8004): Activity participation
- **social-api** (8005): Social features
- **notifications-api** (8006): This service
- **email-service** (8010): Email dispatch
