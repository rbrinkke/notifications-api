-- ============================================================================
-- NOTIFICATIONS TEST DATA GENERATOR
-- Generates 1000 realistic notification records with proper distribution
-- ============================================================================
--
-- Usage:
--   psql -U api_user -d activity_platform -f seed_notifications.sql
--
-- Or from running container:
--   docker exec -i notifications-api-postgres psql -U api_user -d activity_platform < seed_notifications.sql
--
-- ============================================================================

\echo '🚀 Starting notifications test data generation...'
\echo ''

-- ============================================================================
-- STEP 1: Ensure we have test users
-- ============================================================================

\echo '👥 Step 1: Ensuring test users exist...'

-- Create test users if they don't exist
INSERT INTO activity.users (
    user_id,
    email,
    username,
    password_hash,
    first_name,
    last_name,
    subscription_level,
    status
)
SELECT
    uuidv7(),
    'testuser' || i || '@test.local',
    'testuser' || i,
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU7dNmDwSIva', -- password: test123
    CASE (i % 10)
        WHEN 0 THEN 'John'
        WHEN 1 THEN 'Emma'
        WHEN 2 THEN 'Michael'
        WHEN 3 THEN 'Sophie'
        WHEN 4 THEN 'David'
        WHEN 5 THEN 'Lisa'
        WHEN 6 THEN 'James'
        WHEN 7 THEN 'Sarah'
        WHEN 8 THEN 'Robert'
        ELSE 'Anna'
    END,
    CASE (i % 10)
        WHEN 0 THEN 'Smith'
        WHEN 1 THEN 'Johnson'
        WHEN 2 THEN 'Williams'
        WHEN 3 THEN 'Brown'
        WHEN 4 THEN 'Jones'
        WHEN 5 THEN 'Garcia'
        WHEN 6 THEN 'Miller'
        WHEN 7 THEN 'Davis'
        WHEN 8 THEN 'Rodriguez'
        ELSE 'Martinez'
    END,
    CASE
        WHEN i % 3 = 0 THEN 'premium'::activity.subscription_level
        WHEN i % 3 = 1 THEN 'club'::activity.subscription_level
        ELSE 'free'::activity.subscription_level
    END,
    'active'::activity.user_status
FROM generate_series(1, 30) AS i
ON CONFLICT (email) DO NOTHING;

\echo '   ✅ Test users created/verified'
\echo ''

-- ============================================================================
-- STEP 2: Create a helper function for notification generation
-- ============================================================================

\echo '🔧 Step 2: Creating helper function...'

CREATE OR REPLACE FUNCTION activity.generate_test_notifications(num_notifications INT)
RETURNS TABLE (
    inserted_count INT
) AS $$
DECLARE
    v_user_ids UUID[];
    v_user_count INT;
    v_notification_type TEXT;
    v_status TEXT;
    v_title TEXT;
    v_message TEXT;
    v_target_type TEXT;
    v_created_at TIMESTAMP WITH TIME ZONE;
    v_read_at TIMESTAMP WITH TIME ZONE;
    v_actor_user_id UUID;
    v_recipient_user_id UUID;
    v_payload JSONB;
    v_type_random DECIMAL;
    v_status_random DECIMAL;
    v_counter INT := 0;
BEGIN
    -- Get all test user IDs
    SELECT array_agg(user_id) INTO v_user_ids
    FROM activity.users
    WHERE email LIKE '%@test.local';

    v_user_count := array_length(v_user_ids, 1);

    IF v_user_count < 2 THEN
        RAISE EXCEPTION 'Need at least 2 test users. Please run Step 1 first.';
    END IF;

    -- Generate notifications
    FOR i IN 1..num_notifications LOOP
        -- Random recipient
        v_recipient_user_id := v_user_ids[1 + floor(random() * v_user_count)::int];

        -- Random actor (80% chance of having an actor, 20% NULL for system)
        IF random() < 0.8 THEN
            v_actor_user_id := v_user_ids[1 + floor(random() * v_user_count)::int];
            -- Ensure actor != recipient
            WHILE v_actor_user_id = v_recipient_user_id LOOP
                v_actor_user_id := v_user_ids[1 + floor(random() * v_user_count)::int];
            END LOOP;
        ELSE
            v_actor_user_id := NULL;
        END IF;

        -- Random timestamp in last 90 days (weighted towards recent)
        -- Using exponential distribution to favor recent dates
        v_created_at := NOW() - (random() * random() * INTERVAL '90 days');

        -- Determine notification type (weighted distribution)
        v_type_random := random();
        CASE
            WHEN v_type_random < 0.25 THEN -- 25%
                v_notification_type := 'comment';
                v_target_type := 'post';
                v_title := 'New comment on your post';
                v_message := 'Someone commented on your post about hiking adventures';
                v_payload := jsonb_build_object(
                    'comment_text', 'Great photo! Where was this taken?',
                    'post_title', 'Amazing sunset hike'
                );

            WHEN v_type_random < 0.45 THEN -- 20%
                v_notification_type := 'reaction';
                v_target_type := 'post';
                v_title := 'Someone reacted to your post';
                v_message := 'Your post received a new reaction';
                v_payload := jsonb_build_object(
                    'reaction_type', (ARRAY['like', 'love', 'celebrate'])[1 + floor(random() * 3)::int],
                    'post_title', 'Weekend cycling adventure'
                );

            WHEN v_type_random < 0.60 THEN -- 15%
                v_notification_type := 'activity_invite';
                v_target_type := 'activity';
                v_title := 'You''re invited to an activity';
                v_message := 'Join us for a morning coffee meetup';
                v_payload := jsonb_build_object(
                    'activity_title', 'Coffee & Networking',
                    'activity_date', (NOW() + INTERVAL '7 days')::text,
                    'location', 'Central Coffee House'
                );

            WHEN v_type_random < 0.72 THEN -- 12%
                v_notification_type := 'new_post';
                v_target_type := 'community';
                v_title := 'New post in your community';
                v_message := 'Check out the latest post in Runners Club';
                v_payload := jsonb_build_object(
                    'community_name', 'Runners Club',
                    'post_title', 'Training tips for beginners'
                );

            WHEN v_type_random < 0.82 THEN -- 10%
                v_notification_type := 'activity_reminder';
                v_target_type := 'activity';
                v_title := 'Upcoming activity reminder';
                v_message := 'Your activity starts in 24 hours';
                v_payload := jsonb_build_object(
                    'activity_title', 'Sunday Brunch Meetup',
                    'starts_at', (NOW() + INTERVAL '24 hours')::text
                );

            WHEN v_type_random < 0.90 THEN -- 8%
                v_notification_type := 'activity_update';
                v_target_type := 'activity';
                v_title := 'Activity updated';
                v_message := 'The organizer updated the activity details';
                v_payload := jsonb_build_object(
                    'activity_title', 'Beach Volleyball',
                    'update_type', 'location_changed'
                );

            WHEN v_type_random < 0.95 THEN -- 5%
                v_notification_type := 'mention';
                v_target_type := 'post';
                v_title := 'You were mentioned';
                v_message := 'Someone mentioned you in a post';
                v_payload := jsonb_build_object(
                    'post_title', 'Great meetup yesterday!',
                    'mention_context', 'Thanks @user for organizing!'
                );

            WHEN v_type_random < 0.97 THEN -- 2%
                v_notification_type := 'profile_view';
                v_target_type := 'user';
                v_title := 'Someone viewed your profile';
                v_message := 'A user checked out your profile';
                v_payload := jsonb_build_object(
                    'is_premium_feature', true,
                    'viewer_interests', ARRAY['hiking', 'photography']
                );

            WHEN v_type_random < 0.98 THEN -- 1%
                v_notification_type := 'new_favorite';
                v_target_type := 'user';
                v_title := 'You have a new favorite';
                v_message := 'Someone added you to their favorites';
                v_payload := jsonb_build_object(
                    'is_premium_feature', true
                );

            WHEN v_type_random < 0.99 THEN -- 1%
                v_notification_type := 'community_invite';
                v_target_type := 'community';
                v_title := 'Community invitation';
                v_message := 'You''ve been invited to join a community';
                v_payload := jsonb_build_object(
                    'community_name', 'Food Lovers',
                    'inviter_username', 'chef_john'
                );

            WHEN v_type_random < 0.995 THEN -- 0.5%
                v_notification_type := 'new_member';
                v_target_type := 'community';
                v_title := 'New member joined';
                v_message := 'A new member joined your community';
                v_payload := jsonb_build_object(
                    'community_name', 'Yoga Enthusiasts'
                );

            ELSE -- 0.5%
                v_notification_type := 'system';
                v_target_type := NULL;
                v_title := 'System notification';
                v_message := 'Your account has been verified successfully';
                v_payload := jsonb_build_object(
                    'notification_code', 'ACCOUNT_VERIFIED'
                );
        END CASE;

        -- Determine status (weighted distribution)
        v_status_random := random();
        IF v_status_random < 0.75 THEN -- 75% unread
            v_status := 'unread';
            v_read_at := NULL;
        ELSIF v_status_random < 0.95 THEN -- 20% read
            v_status := 'read';
            v_read_at := v_created_at + (random() * INTERVAL '7 days');
        ELSE -- 5% archived
            v_status := 'archived';
            v_read_at := v_created_at + (random() * INTERVAL '14 days');
        END IF;

        -- Insert notification
        INSERT INTO activity.notifications (
            notification_id,
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
            uuidv7(),
            v_recipient_user_id,
            v_actor_user_id,
            v_notification_type::activity.notification_type,
            v_target_type,
            uuidv7(), -- Random target_id (in real scenario would reference actual records)
            v_title,
            v_message,
            v_status::activity.notification_status,
            v_created_at,
            v_read_at,
            v_payload
        );

        v_counter := v_counter + 1;

        -- Progress indicator every 100 records
        IF v_counter % 100 = 0 THEN
            RAISE NOTICE '   📊 Generated % notifications...', v_counter;
        END IF;
    END LOOP;

    RETURN QUERY SELECT v_counter;
END;
$$ LANGUAGE plpgsql;

\echo '   ✅ Helper function created'
\echo ''

-- ============================================================================
-- STEP 3: Generate the notifications
-- ============================================================================

\echo '📝 Step 3: Generating 1000 notifications...'
\echo ''

SELECT activity.generate_test_notifications(1000);

\echo ''
\echo '   ✅ Notifications generated successfully'
\echo ''

-- ============================================================================
-- STEP 4: Display statistics
-- ============================================================================

\echo '📊 Step 4: Generation Statistics'
\echo '================================'
\echo ''

-- Total count
\echo 'Total Notifications:'
SELECT COUNT(*) as total_notifications
FROM activity.notifications;

\echo ''
\echo 'By Type:'
SELECT
    notification_type,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM activity.notifications
GROUP BY notification_type
ORDER BY count DESC;

\echo ''
\echo 'By Status:'
SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM activity.notifications
GROUP BY status
ORDER BY count DESC;

\echo ''
\echo 'Date Range:'
SELECT
    MIN(created_at)::date as oldest_notification,
    MAX(created_at)::date as newest_notification,
    COUNT(DISTINCT created_at::date) as days_covered
FROM activity.notifications;

\echo ''
\echo 'With/Without Actor:'
SELECT
    CASE WHEN actor_user_id IS NULL THEN 'System (no actor)' ELSE 'User triggered' END as actor_type,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM activity.notifications
GROUP BY actor_user_id IS NULL
ORDER BY count DESC;

\echo ''
\echo '✨ Sample Notifications:'
SELECT
    notification_type,
    title,
    status,
    created_at::date as date
FROM activity.notifications
ORDER BY created_at DESC
LIMIT 5;

\echo ''
\echo '🎉 Done! 1000 test notifications have been generated successfully!'
\echo ''
\echo '💡 Tip: You can run this script multiple times. It will add more notifications each time.'
\echo '💡 To clean up: DELETE FROM activity.notifications WHERE user_id IN (SELECT user_id FROM activity.users WHERE email LIKE ''%@test.local'');'
\echo ''

-- Cleanup function (optional, for future use)
DROP FUNCTION IF EXISTS activity.generate_test_notifications(INT);
