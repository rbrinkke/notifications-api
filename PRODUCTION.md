# PRODUCTION DEPLOYMENT CHECKLIST

## ⚠️ CRITICAL SECURITY CHECKS

### Before Deploying to Production

- [ ] **Change all default secrets in .env**
  - [ ] Generate strong `JWT_SECRET` (min 32 characters)
  - [ ] Generate unique `SERVICE_TOKEN` (min 32 characters)
  - [ ] Set strong `DB_PASSWORD`
  - [ ] Set `REDIS_PASSWORD` if Redis requires auth

- [ ] **Configure CORS properly**
  - [ ] Set `CORS_ORIGINS` to specific domains (NOT "*")
  - Example: `CORS_ORIGINS=https://app.example.com,https://admin.example.com`

- [ ] **Disable API documentation in production**
  - [ ] Set `ENABLE_DOCS=false` in production environment

- [ ] **Set production environment variables**
  - [ ] `ENVIRONMENT=production`
  - [ ] `DEBUG=false`
  - [ ] `LOG_LEVEL=WARNING` or `ERROR`

## 🗄️ DATABASE SETUP

### 1. Create Database User
```sql
CREATE USER api_user WITH PASSWORD 'your-secure-password';
GRANT CONNECT ON DATABASE activity_platform TO api_user;
GRANT USAGE ON SCHEMA activity TO api_user;
```

### 2. Create All 10 Stored Procedures

The following stored procedures MUST be created before the API will work:

1. **activity.sp_get_user_notifications** - Get paginated notifications
2. **activity.sp_get_notification_by_id** - Get single notification
3. **activity.sp_mark_notification_as_read** - Mark as read
4. **activity.sp_mark_notifications_as_read_bulk** - Bulk mark read
5. **activity.sp_delete_notification** - Delete/archive notification
6. **activity.sp_get_unread_count** - Get unread counts
7. **activity.sp_create_notification** - Create notification (internal)
8. **activity.sp_get_notification_settings** - Get user settings
9. **activity.sp_update_notification_settings** - Update settings

**Location:** See `notifications-api-specifications.md` for complete stored procedure definitions.

### 3. Grant Permissions
```sql
-- Grant execute permissions on all stored procedures
GRANT EXECUTE ON FUNCTION activity.sp_get_user_notifications TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_get_notification_by_id TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_mark_notification_as_read TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_mark_notifications_as_read_bulk TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_delete_notification TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_get_unread_count TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_create_notification TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_get_notification_settings TO api_user;
GRANT EXECUTE ON FUNCTION activity.sp_update_notification_settings TO api_user;
```

## 🐳 DOCKER DEPLOYMENT

### Option 1: Docker Compose (Recommended for Development)
```bash
# 1. Copy environment file
cp .env.example .env

# 2. Edit .env with production values
vim .env

# 3. Start services
docker-compose up -d

# 4. Check logs
docker-compose logs -f notifications-api
```

### Option 2: Kubernetes (Production)
```bash
# 1. Create secrets
kubectl create secret generic notifications-api-secrets \
  --from-literal=jwt-secret=YOUR_JWT_SECRET \
  --from-literal=service-token=YOUR_SERVICE_TOKEN \
  --from-literal=db-password=YOUR_DB_PASSWORD

# 2. Apply deployment
kubectl apply -f k8s/deployment.yaml

# 3. Apply service
kubectl apply -f k8s/service.yaml
```

## 🔍 HEALTH CHECKS

### API Health Check
```bash
curl http://localhost:8003/health
```

Expected response (healthy):
```json
{
  "status": "ok",
  "checks": {
    "api": "ok",
    "database": "ok"
  }
}
```

### Database Connection Test
```bash
# Test stored procedure access
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT * FROM activity.sp_get_unread_count('user-id-here', false);"
```

## 📊 MONITORING

### Key Metrics to Monitor

1. **API Response Time**
   - Endpoint: All `/api/v1/notifications/*` endpoints
   - Target: p95 < 200ms

2. **Database Connection Pool**
   - Monitor pool exhaustion
   - Alert if active connections > 80

3. **Error Rate**
   - Monitor 4xx and 5xx responses
   - Alert if error rate > 1%

4. **Health Check**
   - Monitor `/health` endpoint
   - Alert if status != "ok" for > 30 seconds

### Logs to Track

- `notification_created` - New notifications
- `notification_marked_read` - User engagement
- `settings_updated` - Settings changes
- `database_exception` - Database errors
- `invalid_jwt_token` - Auth failures

## 🔒 SECURITY BEST PRACTICES

### 1. JWT Token Management
- Use strong secrets (min 256 bits)
- Implement token rotation
- Set appropriate expiration times

### 2. Service Token
- Use strong random token for internal service-to-service calls
- Rotate regularly
- Never expose in logs

### 3. Database Security
- Use separate database user with minimal permissions
- Enable SSL/TLS for database connections
- Regular security patches

### 4. Network Security
- Use HTTPS only (TLS 1.2+)
- Implement rate limiting (via Redis)
- Use firewall rules to restrict access

## 🚀 DEPLOYMENT PROCESS

### 1. Pre-Deployment
```bash
# Run linting
flake8 app/

# Run tests
pytest

# Build Docker image
docker build -t notifications-api:latest .
```

### 2. Deployment
```bash
# Tag image
docker tag notifications-api:latest registry.example.com/notifications-api:v1.0.0

# Push to registry
docker push registry.example.com/notifications-api:v1.0.0

# Deploy (example for Kubernetes)
kubectl set image deployment/notifications-api notifications-api=registry.example.com/notifications-api:v1.0.0
```

### 3. Post-Deployment
```bash
# Check health
curl https://api.example.com/health

# Check logs
kubectl logs -f deployment/notifications-api

# Monitor errors
kubectl logs deployment/notifications-api | grep ERROR
```

## 🔄 ROLLBACK PROCEDURE

If deployment fails:

```bash
# 1. Rollback Kubernetes deployment
kubectl rollout undo deployment/notifications-api

# 2. Check rollback status
kubectl rollout status deployment/notifications-api

# 3. Verify health
curl https://api.example.com/health
```

## 📞 TROUBLESHOOTING

### Common Issues

#### 1. Database Connection Fails
```bash
# Check connection
psql -h $DB_HOST -U $DB_USER -d $DB_NAME

# Check stored procedures exist
\df activity.sp_*
```

#### 2. Authentication Fails
- Verify JWT_SECRET matches Auth API
- Check token expiration
- Verify user exists in database

#### 3. High Response Times
- Check database connection pool
- Review slow query log
- Monitor database CPU/memory

## 📝 PRODUCTION ENVIRONMENT VARIABLES

```bash
# Database
DB_HOST=production-db.example.com
DB_PORT=5432
DB_NAME=activity_platform
DB_USER=api_user
DB_PASSWORD=<STRONG_PASSWORD>

# JWT (MUST match Auth API)
JWT_SECRET=<STRONG_SECRET_MIN_32_CHARS>
JWT_ALGORITHM=HS256

# Internal Service Auth
SERVICE_TOKEN=<STRONG_RANDOM_TOKEN>

# Redis
REDIS_HOST=redis.example.com
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<REDIS_PASSWORD>

# API Settings
API_V1_PREFIX=/api/v1
PROJECT_NAME=Notifications API
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
CORS_ORIGINS=https://app.example.com,https://admin.example.com
ENABLE_DOCS=false

# Email API (optional)
EMAIL_API_URL=https://email-api.example.com
EMAIL_API_KEY=<EMAIL_API_KEY>
```

## ✅ FINAL CHECKLIST

Before going live:

- [ ] All 10 stored procedures created and tested
- [ ] All secrets changed from defaults
- [ ] CORS configured for specific domains
- [ ] API documentation disabled (`ENABLE_DOCS=false`)
- [ ] Environment set to `production`
- [ ] Debug mode disabled (`DEBUG=false`)
- [ ] Logging level set to `WARNING` or `ERROR`
- [ ] Health check endpoint responding
- [ ] Database connection working
- [ ] JWT validation working
- [ ] Service token validation working
- [ ] All 9 endpoints tested
- [ ] Monitoring configured
- [ ] Backup strategy in place
- [ ] Rollback procedure documented
