# 🚀 Quick Start: Seed 1000 Notifications

## ⚡ Fastest Method (Pick One)

### Option 1: Auto-Magic Script 🎯
```bash
./seed_quick.sh
```
**Auto-detects your environment and chooses the best method!**

---

### Option 2: SQL Direct (Fastest) ⚡
```bash
# Local database
psql -U api_user -d activity_platform -f seed_notifications.sql

# Docker database
docker exec -i notifications-api-postgres psql -U api_user -d activity_platform < seed_notifications.sql
```

---

### Option 3: Python Script 🐍
```bash
# First time only
pip install psycopg2-binary python-dotenv

# Run it
python seed_notifications.py
```

---

## 📊 What You Get

- ✅ **30 test users** (testuser1@test.local ... testuser30@test.local)
- ✅ **1000 notifications** with realistic distribution
- ✅ **12 notification types** (comment, reaction, activity_invite, etc.)
- ✅ **3 statuses** (75% unread, 20% read, 5% archived)
- ✅ **90 days** of historical data
- ✅ **Rich JSONB payloads** for each notification

## 🧪 Test It

```sql
-- See total count
SELECT COUNT(*) FROM activity.notifications;

-- See distribution
SELECT notification_type, COUNT(*)
FROM activity.notifications
GROUP BY notification_type
ORDER BY COUNT(*) DESC;

-- See recent notifications
SELECT notification_type, title, status, created_at
FROM activity.notifications
ORDER BY created_at DESC
LIMIT 10;
```

## 🧹 Clean Up

```sql
-- Remove all test data
DELETE FROM activity.notifications
WHERE user_id IN (
    SELECT user_id FROM activity.users
    WHERE email LIKE '%@test.local'
);

DELETE FROM activity.users WHERE email LIKE '%@test.local';
```

---

**Need more details?** See [TEST_DATA_README.md](TEST_DATA_README.md)
