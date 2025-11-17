# Migratie naar Centrale Database

**Datum:** 2025-11-13
**Status:** ✅ Compleet

## Wijzigingen

### 1. Docker Compose Configuratie

**Voor:**
- Eigen PostgreSQL container (postgres:15-alpine)
- Eigen Redis container (redis:7-alpine)
- Eigen netwerk (app-network)
- Port 8003

**Na:**
- ✅ Gebruikt centrale `activity-postgres-db` container
- ✅ Gebruikt gedeelde `auth-redis` container
- ✅ Gebruikt `activity-network` netwerk
- ✅ Port 8006 (om conflicten te voorkomen)

### 2. Database Configuratie

**Database Connectie:**
```
Host: activity-postgres-db
Port: 5432
Database: activitydb
User: postgres
Password: postgres_secure_password_change_in_prod
```

**Belangrijke punten:**
- Host: `activity-postgres-db` (centrale database container)
- Database: `activitydb` (met alle 40 tabellen)
- Schema: `activity` (automatisch via migraties)

### 3. Redis Configuratie

**Redis Connectie:**
```
Host: auth-redis
Port: 6379
DB: 0
```

Gebruikt dezelfde Redis instance als andere APIs voor:
- Rate limiting
- Caching
- Real-time notifications

### 4. Netwerk Configuratie

Gebruikt `activity-network` external network:
- Alle activity services in zelfde netwerk
- Direct communicatie tussen services
- Geen port mapping conflicts

### 5. Container Naam

Container naam: `notifications-api`
- Makkelijk te identificeren
- Consistent met andere services
- Gebruikt in logs en monitoring

## Database Schema

De notifications-api gebruikt tabellen uit het centrale schema:

**Notification Tabellen:**
- `notifications` (12 kolommen) - Notification data
- `notification_preferences` (8 kolommen) - User preferences

**User Tabellen:**
- `users` (34 kolommen) - User info
- `user_settings` (14 kolommen) - User preferences

## Deployment

### Starten

```bash
cd /mnt/d/activity/notifications-api
docker compose build
docker compose up -d
```

### Logs Checken

```bash
docker compose logs -f notifications-api
```

### Health Check

```bash
curl http://localhost:8006/health
```

### Stoppen

```bash
docker compose down
```

## Belangrijke Opmerkingen

1. **Geen eigen database meer** - Alle data in centrale database
2. **Gedeelde Redis** - Rate limiting gedeeld met andere APIs
3. **Port 8006** - Om conflict met andere APIs te voorkomen
4. **External network** - Moet `activity-network` netwerk bestaan
5. **Email API integratie** - Voor email notifications

## Port Overzicht

| Service | Port | Functie |
|---------|------|---------|
| auth-api | 8000 | Authenticatie & gebruikers |
| moderation-api | 8002 | Content moderatie |
| community-api | 8003 | Communities & posts |
| participation-api | 8004 | Activity deelname |
| social-api | 8005 | Social features |
| notifications-api | 8006 | Notificaties |

## Verificatie

Checklist na deployment:
- [ ] Container start zonder errors
- [ ] Database connectie succesvol
- [ ] Redis connectie succesvol
- [ ] Health endpoint reageert
- [ ] Auth-API communicatie werkt
- [ ] Notification endpoints werken

## Rollback

Als er problemen zijn:
```bash
cd /mnt/d/activity/notifications-api
docker compose down
# Fix issues
docker compose up -d
```

---

**Status:** ✅ Klaar voor gebruik met centrale database
