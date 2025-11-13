# Notifications API

FastAPI-based notifications service with PostgreSQL stored procedures.

## Features

- JWT authentication
- Structured logging with correlation IDs
- Health check endpoint
- Docker containerization
- 9 RESTful endpoints

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Local Development

1. Copy environment file:
```bash
cp .env.example .env
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run database migrations (create stored procedures):
```bash
# Connect to PostgreSQL and run stored procedure scripts
psql -h localhost -U api_user -d activity_platform -f migrations/notifications_procedures.sql
```

4. Start API:
```bash
uvicorn app.main:app --reload
```

### Docker

```bash
docker-compose up -d
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc

## Endpoints

### User Endpoints (JWT Required)
- `GET /api/v1/notifications` - List notifications
- `GET /api/v1/notifications/{id}` - Get single notification
- `PATCH /api/v1/notifications/{id}/read` - Mark as read
- `POST /api/v1/notifications/mark-read` - Bulk mark read
- `DELETE /api/v1/notifications/{id}` - Archive/delete
- `GET /api/v1/notifications/unread/count` - Get unread counts
- `GET /api/v1/notifications/settings` - Get settings
- `PATCH /api/v1/notifications/settings` - Update settings

### Internal Endpoints (Service Token Required)
- `POST /api/v1/notifications` - Create notification

### Health Check
- `GET /health` - Health status

## Testing

```bash
pytest
```

## Environment Variables

See `.env.example` for all required variables.
