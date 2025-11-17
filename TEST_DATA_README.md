# 📊 Notifications Test Data Generator

Generate 1000 realistic notification records for testing the Notifications API.

## 🎯 Features

- ✅ **1000 realistic notifications** with proper type distribution
- ✅ **30 test users** automatically created
- ✅ **Weighted distribution** matching real-world usage patterns
- ✅ **Temporal spread** over 90 days (weighted towards recent)
- ✅ **Proper status distribution** (75% unread, 20% read, 5% archived)
- ✅ **JSONB payloads** with contextual data
- ✅ **UUIDv7** for chronological ordering
- ✅ **Foreign key safe** - creates dependencies automatically

## 📈 Data Distribution

### Notification Types
| Type              | Count | % | Description |
|-------------------|-------|---|-------------|
| comment           | 250   | 25% | Most common interaction |
| reaction          | 200   | 20% | Very active feature |
| activity_invite   | 150   | 15% | Core platform feature |
| new_post          | 120   | 12% | Community engagement |
| activity_reminder | 100   | 10% | Automated reminders |
| activity_update   | 80    | 8%  | Organizer updates |
| mention           | 50    | 5%  | Social mentions |
| profile_view      | 20    | 2%  | Premium feature |
| new_favorite      | 10    | 1%  | Premium feature |
| community_invite  | 10    | 1%  | Growth |
| new_member        | 5     | 0.5% | Community activity |
| system            | 5     | 0.5% | Admin notifications |

### Status Distribution
- **75% unread** (750 records) - Users don't read everything
- **20% read** (200 records) - Recently read
- **5% archived** (50 records) - Cleaned up

### Temporal Distribution
- Spread over **last 90 days**
- **Exponentially weighted** towards recent dates
- Realistic user behavior simulation

## 🚀 Usage

### Option 1: SQL Script (Recommended)

**Fastest and simplest approach**

```bash
# If database is local
psql -U api_user -d activity_platform -f seed_notifications.sql

# If using Docker
docker exec -i notifications-api-postgres psql -U api_user -d activity_platform < seed_notifications.sql
```

### Option 2: Python Script

**More flexible, easier to customize**

```bash
# Install dependencies
pip install psycopg2-binary python-dotenv

# Make sure .env file exists with DB credentials
cp .env.example .env
# Edit .env with your database credentials

# Run the script
python seed_notifications.py

# Or make it executable
chmod +x seed_notifications.py
./seed_notifications.py
```

## 📋 Prerequisites

### For SQL Script
- PostgreSQL client (`psql`)
- Access to the database
- Database already set up with schema

### For Python Script
- Python 3.7+
- `psycopg2-binary` library
- `.env` file with database credentials

## 🗄️ Database Requirements

The script expects these tables to exist:
- `activity.users` - User accounts
- `activity.notifications` - Notifications table

ENUMs must be defined:
- `activity.notification_type`
- `activity.notification_status`
- `activity.subscription_level`
- `activity.user_status`

## 📊 What Gets Created

### Test Users (30 accounts)
- **Emails**: `testuser1@test.local` through `testuser30@test.local`
- **Usernames**: `testuser1` through `testuser30`
- **Password**: `test123` (hash: `$2b$12$LQv3c1yqBWVHxkd0LHAkCO...`)
- **Names**: Realistic first/last name combinations
- **Subscriptions**: Mixed (free, club, premium)

### Notifications (1000 records)
Each notification includes:
- ✅ Unique `notification_id` (UUIDv7)
- ✅ Random `user_id` (recipient)
- ✅ Random `actor_user_id` (80% filled, 20% NULL for system)
- ✅ Realistic `notification_type` (weighted distribution)
- ✅ Appropriate `target_type` and `target_id`
- ✅ Context-specific `title` and `message`
- ✅ Realistic `status` (unread/read/archived)
- ✅ `created_at` spread over 90 days
- ✅ `read_at` for read/archived notifications
- ✅ Rich `payload` JSONB with contextual data

## 🎨 Example Generated Notifications

```json
{
  "notification_id": "01932c4e-8b2a-7890-abcd-1234567890ab",
  "user_id": "user-uuid-123",
  "actor_user_id": "user-uuid-456",
  "notification_type": "comment",
  "target_type": "post",
  "target_id": "post-uuid-789",
  "title": "New comment on your post",
  "message": "Someone commented on your post",
  "status": "unread",
  "created_at": "2025-10-15T14:30:00Z",
  "read_at": null,
  "payload": {
    "comment_text": "Great photo! Where was this taken?",
    "post_title": "Amazing sunset hike"
  }
}
```

## 🧹 Cleanup

To remove all test data:

```sql
-- Remove test notifications
DELETE FROM activity.notifications
WHERE user_id IN (
    SELECT user_id FROM activity.users
    WHERE email LIKE '%@test.local'
);

-- Remove test users
DELETE FROM activity.users
WHERE email LIKE '%@test.local';
```

Or using the Python script (future enhancement):
```bash
python seed_notifications.py --clean
```

## 🔄 Re-running

Both scripts can be run multiple times safely:
- **SQL**: Creates users with `ON CONFLICT DO NOTHING`
- **Python**: Uses `ON CONFLICT DO NOTHING` for users
- Each run adds 1000 more notifications

## 📈 Verification

After running, verify the data:

```sql
-- Total notifications
SELECT COUNT(*) FROM activity.notifications;

-- Distribution by type
SELECT notification_type, COUNT(*)
FROM activity.notifications
GROUP BY notification_type
ORDER BY COUNT(*) DESC;

-- Distribution by status
SELECT status, COUNT(*)
FROM activity.notifications
GROUP BY status;

-- Recent notifications
SELECT notification_type, title, status, created_at
FROM activity.notifications
ORDER BY created_at DESC
LIMIT 10;
```

## 🛠️ Customization

### Change notification count

**SQL:**
```sql
-- Edit line in seed_notifications.sql
SELECT activity.generate_test_notifications(2000); -- Generate 2000 instead
```

**Python:**
```python
# Edit line in seed_notifications.py
generate_notifications(conn, 2000)  # Generate 2000 instead
```

### Adjust distribution

Edit the `NOTIFICATION_TYPES` array weights in either script.

### Change date range

**SQL:** Edit the interval in the function:
```sql
v_created_at := NOW() - (random() * random() * INTERVAL '180 days'); -- 180 days instead of 90
```

**Python:**
```python
days_ago = random.random() ** 2 * 180  # 180 days instead of 90
```

## ⚡ Performance

- **SQL Script**: ~2-3 seconds for 1000 records
- **Python Script**: ~5-10 seconds for 1000 records

Both use batch inserts for optimal performance.

## 🐛 Troubleshooting

### "Need at least 2 test users"
The script needs users to assign notifications to. Run Step 1 first or check that users were created successfully.

### "Permission denied"
Make sure your database user has INSERT permissions on `activity.users` and `activity.notifications`.

### "Type does not exist"
The database schema must be set up first. Run `sqlschema.sql` before running the seed script.

### Python "psycopg2 not found"
Install it: `pip install psycopg2-binary`

### Connection refused
Check your `.env` file has the correct database credentials and the database is running.

## 📝 Notes

- Test data uses `@test.local` domain to easily identify and clean up
- All passwords are `test123` for convenience
- UUIDs for `target_id` are random (won't match real posts/activities)
- Timestamps are randomized but chronologically ordered via UUIDv7
- The scripts are idempotent for users (safe to re-run)

## 🎯 Use Cases

Perfect for testing:
- ✅ Notification API endpoints
- ✅ Pagination and filtering
- ✅ Status updates (mark as read)
- ✅ Date range queries
- ✅ Performance with realistic data volumes
- ✅ UI/UX with various notification types
- ✅ Real-time notification systems
- ✅ Database indexing strategies

---

**Happy Testing! 🎉**
