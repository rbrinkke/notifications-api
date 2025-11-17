#!/usr/bin/env python3
"""
Notifications Test Data Generator (Python Version)
Generates 1000 realistic notification records with proper distribution

Usage:
    python seed_notifications.py

Requirements:
    pip install psycopg2-binary python-dotenv
"""

import os
import random
import sys
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("❌ Error: psycopg2 not installed")
    print("   Run: pip install psycopg2-binary")
    sys.exit(1)


# Load environment variables
load_dotenv()


# Notification type distribution (type, weight, has_actor)
NOTIFICATION_TYPES = [
    ('comment', 0.25, True, 'post', 'New comment on your post', 'Someone commented on your post'),
    ('reaction', 0.20, True, 'post', 'Someone reacted to your post', 'Your post received a new reaction'),
    ('activity_invite', 0.15, True, 'activity', "You're invited to an activity", 'Join us for a meetup'),
    ('new_post', 0.12, True, 'community', 'New post in your community', 'Check out the latest post'),
    ('activity_reminder', 0.10, False, 'activity', 'Upcoming activity reminder', 'Your activity starts soon'),
    ('activity_update', 0.08, True, 'activity', 'Activity updated', 'The organizer updated the details'),
    ('mention', 0.05, True, 'post', 'You were mentioned', 'Someone mentioned you in a post'),
    ('profile_view', 0.02, True, 'user', 'Someone viewed your profile', 'A user checked out your profile'),
    ('new_favorite', 0.01, True, 'user', 'You have a new favorite', 'Someone added you to their favorites'),
    ('community_invite', 0.01, True, 'community', 'Community invitation', "You've been invited to join"),
    ('new_member', 0.005, True, 'community', 'New member joined', 'A new member joined your community'),
    ('system', 0.005, False, None, 'System notification', 'Important system message'),
]

# Status distribution
STATUS_DISTRIBUTION = [
    ('unread', 0.75),
    ('read', 0.20),
    ('archived', 0.05),
]


def get_db_connection():
    """Create database connection from environment variables"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'activity_platform'),
        user=os.getenv('DB_USER', 'api_user'),
        password=os.getenv('DB_PASSWORD', 'changeme')
    )


def create_test_users(conn):
    """Create test users if they don't exist"""
    print("👥 Creating test users...")

    first_names = ['John', 'Emma', 'Michael', 'Sophie', 'David', 'Lisa', 'James', 'Sarah', 'Robert', 'Anna']
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
    subscription_levels = ['free', 'club', 'premium']

    users_data = []
    for i in range(1, 31):
        users_data.append((
            f'testuser{i}@meet5.test',
            f'testuser{i}',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7dNmDwSIva',  # password: test123
            first_names[i % len(first_names)],
            last_names[i % len(last_names)],
            subscription_levels[i % 3],
        ))

    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO activity.users (
                email, username, password_hash, first_name, last_name, subscription_level
            ) VALUES (%s, %s, %s, %s, %s, %s::activity.subscription_level)
            ON CONFLICT (email) DO NOTHING
        """, users_data)

        conn.commit()
        print(f"   ✅ Test users created/verified")


def get_test_user_ids(conn):
    """Get all test user IDs"""
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM activity.users WHERE email LIKE '%@meet5.test'")
        return [row[0] for row in cur.fetchall()]


def random_date_last_90_days():
    """Generate random date in last 90 days, weighted towards recent"""
    # Using exponential distribution to favor recent dates
    days_ago = random.random() ** 2 * 90
    return datetime.now() - timedelta(days=days_ago)


def generate_payload(notification_type: str) -> dict:
    """Generate realistic payload for notification type"""
    payloads = {
        'comment': {
            'comment_text': random.choice([
                'Great photo! Where was this taken?',
                'Thanks for organizing!',
                'Count me in for next time!',
                'Amazing experience!',
            ]),
            'post_title': random.choice([
                'Amazing sunset hike',
                'Weekend cycling adventure',
                'Coffee meetup recap',
            ]),
        },
        'reaction': {
            'reaction_type': random.choice(['like', 'love', 'celebrate', 'support']),
            'post_title': 'Weekend cycling adventure',
        },
        'activity_invite': {
            'activity_title': random.choice([
                'Coffee & Networking',
                'Sunday Brunch',
                'Beach Volleyball',
                'Movie Night',
            ]),
            'activity_date': (datetime.now() + timedelta(days=random.randint(1, 30))).isoformat(),
            'location': random.choice(['Central Park', 'Coffee House', 'Beach Club']),
        },
        'new_post': {
            'community_name': random.choice(['Runners Club', 'Food Lovers', 'Yoga Enthusiasts']),
            'post_title': 'Check out this new post!',
        },
        'activity_reminder': {
            'activity_title': random.choice(['Sunday Brunch Meetup', 'Morning Run', 'Yoga Session']),
            'starts_at': (datetime.now() + timedelta(hours=24)).isoformat(),
        },
        'activity_update': {
            'activity_title': 'Beach Volleyball',
            'update_type': random.choice(['location_changed', 'time_changed', 'details_updated']),
        },
        'mention': {
            'post_title': 'Great meetup yesterday!',
            'mention_context': 'Thanks @user for organizing!',
        },
        'profile_view': {
            'is_premium_feature': True,
            'viewer_interests': random.sample(['hiking', 'photography', 'cooking', 'yoga', 'running'], 2),
        },
        'new_favorite': {
            'is_premium_feature': True,
        },
        'community_invite': {
            'community_name': random.choice(['Food Lovers', 'Tech Enthusiasts', 'Book Club']),
            'inviter_username': f'user_{random.randint(1, 100)}',
        },
        'new_member': {
            'community_name': random.choice(['Yoga Enthusiasts', 'Runners Club']),
        },
        'system': {
            'notification_code': random.choice([
                'ACCOUNT_VERIFIED',
                'SUBSCRIPTION_RENEWED',
                'SECURITY_ALERT',
                'FEATURE_ANNOUNCEMENT',
            ]),
        },
    }

    return payloads.get(notification_type, {})


def pick_weighted_choice(choices):
    """Pick a choice based on weights"""
    total_weight = sum(weight for _, weight in choices)
    random_value = random.random() * total_weight

    cumulative = 0
    for choice, weight in choices:
        cumulative += weight
        if random_value <= cumulative:
            return choice

    return choices[-1][0]  # fallback


def generate_notifications(conn, count: int = 1000):
    """Generate test notifications"""
    print(f"📝 Generating {count} notifications...")

    user_ids = get_test_user_ids(conn)
    if len(user_ids) < 2:
        raise Exception("Need at least 2 test users. Run create_test_users first.")

    notifications = []

    for i in range(count):
        # Pick random recipient
        recipient_id = random.choice(user_ids)

        # Pick notification type
        type_random = random.random()
        cumulative = 0
        selected_type = None

        for notif_type, weight, has_actor, target_type, title, message in NOTIFICATION_TYPES:
            cumulative += weight
            if type_random <= cumulative:
                selected_type = (notif_type, has_actor, target_type, title, message)
                break

        if selected_type is None:
            selected_type = NOTIFICATION_TYPES[-1][:5]

        notif_type, has_actor, target_type, title, message = selected_type

        # Pick actor (if applicable)
        actor_id = None
        if has_actor and random.random() < 0.8:  # 80% chance
            actor_id = random.choice([uid for uid in user_ids if uid != recipient_id])

        # Generate timestamp
        created_at = random_date_last_90_days()

        # Pick status
        status = pick_weighted_choice([(s, w) for s, w in STATUS_DISTRIBUTION])

        # Set read_at if read or archived
        read_at = None
        if status in ('read', 'archived'):
            read_at = created_at + timedelta(
                hours=random.randint(1, 168)  # 1 hour to 7 days
            )

        # Generate payload
        payload = generate_payload(notif_type)

        notifications.append((
            recipient_id,
            actor_id,
            notif_type,
            target_type,
            title,
            message,
            status,
            created_at,
            read_at,
            payload,
        ))

        if (i + 1) % 100 == 0:
            print(f"   📊 Generated {i + 1} notifications...")

    # Bulk insert
    with conn.cursor() as cur:
        execute_batch(cur, """
            INSERT INTO activity.notifications (
                user_id,
                actor_user_id,
                notification_type,
                target_type,
                target_id,
                title,
                message,
                status,
                created_at,
                read_at,
                payload
            ) VALUES (
                %s,
                %s,
                %s::activity.notification_type,
                %s,
                gen_random_uuid(),
                %s,
                %s,
                %s::activity.notification_status,
                %s,
                %s,
                %s::jsonb
            )
        """, [(
            n[0], n[1], n[2], n[3], n[4], n[5], n[6], n[7], n[8],
            str(n[9]).replace("'", '"')  # Convert dict to JSON string
        ) for n in notifications])

        conn.commit()

    print(f"   ✅ {count} notifications generated successfully")


def show_statistics(conn):
    """Display generation statistics"""
    print("\n📊 Generation Statistics")
    print("=" * 50)

    with conn.cursor() as cur:
        # Total count
        cur.execute("SELECT COUNT(*) FROM activity.notifications")
        total = cur.fetchone()[0]
        print(f"\nTotal Notifications: {total}")

        # By type
        print("\nBy Type:")
        cur.execute("""
            SELECT
                notification_type,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM activity.notifications
            GROUP BY notification_type
            ORDER BY count DESC
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:20s} {row[1]:5d} ({row[2]:5.2f}%)")

        # By status
        print("\nBy Status:")
        cur.execute("""
            SELECT
                status,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
            FROM activity.notifications
            GROUP BY status
            ORDER BY count DESC
        """)
        for row in cur.fetchall():
            print(f"  {row[0]:20s} {row[1]:5d} ({row[2]:5.2f}%)")

        # Date range
        print("\nDate Range:")
        cur.execute("""
            SELECT
                MIN(created_at)::date as oldest,
                MAX(created_at)::date as newest,
                COUNT(DISTINCT created_at::date) as days_covered
            FROM activity.notifications
        """)
        oldest, newest, days = cur.fetchone()
        print(f"  Oldest: {oldest}")
        print(f"  Newest: {newest}")
        print(f"  Days covered: {days}")

        # Sample
        print("\n✨ Sample Notifications:")
        cur.execute("""
            SELECT notification_type, title, status, created_at::date
            FROM activity.notifications
            ORDER BY created_at DESC
            LIMIT 5
        """)
        for row in cur.fetchall():
            print(f"  [{row[0]:15s}] {row[1][:40]:40s} | {row[2]:8s} | {row[3]}")


def main():
    """Main execution"""
    print("🚀 Starting notifications test data generation...\n")

    try:
        conn = get_db_connection()
        print("✅ Database connection established\n")

        # Step 1: Create test users
        create_test_users(conn)

        # Step 2: Generate notifications
        generate_notifications(conn, 1000)

        # Step 3: Show statistics
        show_statistics(conn)

        conn.close()

        print("\n🎉 Done! 1000 test notifications have been generated successfully!")
        print("\n💡 Tip: Run this script multiple times to add more notifications")
        print("💡 To clean up: DELETE FROM activity.notifications WHERE user_id IN")
        print("   (SELECT user_id FROM activity.users WHERE email LIKE '%@meet5.test');")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
