-- ============================================================================
-- NOTIFICATIONS API - STORED PROCEDURES
-- ============================================================================
-- This file contains all stored procedures needed by the notifications-api
-- Apply to database: docker exec -i activity-postgres-db psql -U postgres -d activitydb < migrations/01_notification_procedures.sql
-- ============================================================================

-- First, ensure notification_preferences table exists
CREATE TABLE IF NOT EXISTS activity.notification_preferences (
    user_id UUID PRIMARY KEY REFERENCES activity.users(user_id) ON DELETE CASCADE,
    email_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    push_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    in_app_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    enabled_types JSONB NOT NULL DEFAULT '["activity_invite", "activity_reminder", "activity_update", "community_invite", "new_member", "new_post", "comment", "reaction", "mention", "system"]'::jsonb,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_preferences_user ON activity.notification_preferences(user_id);

-- ============================================================================
-- 1. sp_get_user_notifications - Get paginated notifications for user
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_get_user_notifications(
    p_user_id UUID,
    p_status VARCHAR DEFAULT NULL,
    p_notification_type VARCHAR DEFAULT NULL,
    p_limit INT DEFAULT 20,
    p_offset INT DEFAULT 0,
    p_include_premium_only BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    notification_id UUID,
    user_id UUID,
    actor_user_id UUID,
    actor_username VARCHAR,
    actor_first_name VARCHAR,
    actor_last_name VARCHAR,
    actor_main_photo_url VARCHAR,
    notification_type VARCHAR,
    target_type VARCHAR,
    target_id UUID,
    title VARCHAR,
    message TEXT,
    status VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    payload JSONB,
    total_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    WITH filtered_notifications AS (
        SELECT
            n.notification_id,
            n.user_id,
            n.actor_user_id,
            n.notification_type::VARCHAR,
            n.target_type,
            n.target_id,
            n.title,
            n.message,
            n.status::VARCHAR,
            n.created_at,
            n.read_at,
            n.payload,
            u.username,
            u.first_name,
            u.last_name,
            u.main_photo_url
        FROM activity.notifications n
        LEFT JOIN activity.users u ON n.actor_user_id = u.user_id
        WHERE n.user_id = p_user_id
            AND (p_status IS NULL OR n.status::VARCHAR = p_status)
            AND (p_notification_type IS NULL OR n.notification_type::VARCHAR = p_notification_type)
            AND (
                p_include_premium_only = TRUE
                OR n.notification_type::VARCHAR NOT IN ('profile_view', 'new_favorite')
            )
        ORDER BY n.created_at DESC
        LIMIT p_limit
        OFFSET p_offset
    ),
    total AS (
        SELECT COUNT(*) as cnt
        FROM activity.notifications n
        WHERE n.user_id = p_user_id
            AND (p_status IS NULL OR n.status::VARCHAR = p_status)
            AND (p_notification_type IS NULL OR n.notification_type::VARCHAR = p_notification_type)
            AND (
                p_include_premium_only = TRUE
                OR n.notification_type::VARCHAR NOT IN ('profile_view', 'new_favorite')
            )
    )
    SELECT
        fn.notification_id,
        fn.user_id,
        fn.actor_user_id,
        fn.username,
        fn.first_name,
        fn.last_name,
        fn.main_photo_url,
        fn.notification_type,
        fn.target_type,
        fn.target_id,
        fn.title,
        fn.message,
        fn.status,
        fn.created_at,
        fn.read_at,
        fn.payload,
        t.cnt as total_count
    FROM filtered_notifications fn
    CROSS JOIN total t;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 2. sp_get_notification_by_id - Get single notification
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_get_notification_by_id(
    p_user_id UUID,
    p_notification_id UUID
)
RETURNS TABLE (
    notification_id UUID,
    user_id UUID,
    actor_user_id UUID,
    actor_username VARCHAR,
    actor_first_name VARCHAR,
    actor_last_name VARCHAR,
    actor_main_photo_url VARCHAR,
    notification_type VARCHAR,
    target_type VARCHAR,
    target_id UUID,
    title VARCHAR,
    message TEXT,
    status VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    payload JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        n.notification_id,
        n.user_id,
        n.actor_user_id,
        u.username,
        u.first_name,
        u.last_name,
        u.main_photo_url,
        n.notification_type::VARCHAR,
        n.target_type,
        n.target_id,
        n.title,
        n.message,
        n.status::VARCHAR,
        n.created_at,
        n.read_at,
        n.payload
    FROM activity.notifications n
    LEFT JOIN activity.users u ON n.actor_user_id = u.user_id
    WHERE n.notification_id = p_notification_id
        AND n.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 3. sp_mark_notification_as_read - Mark single notification as read
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_mark_notification_as_read(
    p_user_id UUID,
    p_notification_id UUID
)
RETURNS TABLE (
    notification_id UUID,
    status VARCHAR,
    read_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    UPDATE activity.notifications
    SET
        status = 'read'::activity.notification_status,
        read_at = NOW()
    WHERE notification_id = p_notification_id
        AND user_id = p_user_id
        AND status = 'unread'::activity.notification_status;

    RETURN QUERY
    SELECT
        n.notification_id,
        n.status::VARCHAR,
        n.read_at
    FROM activity.notifications n
    WHERE n.notification_id = p_notification_id
        AND n.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 4. sp_mark_notifications_as_read_bulk - Bulk mark as read
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_mark_notifications_as_read_bulk(
    p_user_id UUID,
    p_notification_ids UUID[] DEFAULT NULL,
    p_notification_type VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    updated_count BIGINT
) AS $$
DECLARE
    v_updated_count BIGINT;
BEGIN
    -- If notification_ids provided, mark those
    IF p_notification_ids IS NOT NULL THEN
        UPDATE activity.notifications
        SET
            status = 'read'::activity.notification_status,
            read_at = NOW()
        WHERE user_id = p_user_id
            AND notification_id = ANY(p_notification_ids)
            AND status = 'unread'::activity.notification_status;

        GET DIAGNOSTICS v_updated_count = ROW_COUNT;

    -- If notification_type provided, mark all of that type
    ELSIF p_notification_type IS NOT NULL THEN
        UPDATE activity.notifications
        SET
            status = 'read'::activity.notification_status,
            read_at = NOW()
        WHERE user_id = p_user_id
            AND notification_type::VARCHAR = p_notification_type
            AND status = 'unread'::activity.notification_status;

        GET DIAGNOSTICS v_updated_count = ROW_COUNT;

    -- Otherwise mark all unread
    ELSE
        UPDATE activity.notifications
        SET
            status = 'read'::activity.notification_status,
            read_at = NOW()
        WHERE user_id = p_user_id
            AND status = 'unread'::activity.notification_status;

        GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    END IF;

    RETURN QUERY SELECT v_updated_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 5. sp_delete_notification - Delete or archive notification
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_delete_notification(
    p_user_id UUID,
    p_notification_id UUID,
    p_permanent BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    success BOOLEAN,
    message TEXT
) AS $$
DECLARE
    v_exists BOOLEAN;
BEGIN
    -- Check if notification exists and belongs to user
    SELECT EXISTS(
        SELECT 1 FROM activity.notifications
        WHERE notification_id = p_notification_id
            AND user_id = p_user_id
    ) INTO v_exists;

    IF NOT v_exists THEN
        RETURN QUERY SELECT FALSE, 'Notification not found'::TEXT;
        RETURN;
    END IF;

    -- Permanent delete
    IF p_permanent THEN
        DELETE FROM activity.notifications
        WHERE notification_id = p_notification_id
            AND user_id = p_user_id;

        RETURN QUERY SELECT TRUE, 'Notification permanently deleted'::TEXT;

    -- Archive (soft delete)
    ELSE
        UPDATE activity.notifications
        SET status = 'archived'::activity.notification_status
        WHERE notification_id = p_notification_id
            AND user_id = p_user_id;

        RETURN QUERY SELECT TRUE, 'Notification archived'::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 6. sp_get_unread_count - Get unread notification counts by type
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_get_unread_count(
    p_user_id UUID,
    p_include_premium_only BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    total_unread BIGINT,
    activity_invite_count BIGINT,
    activity_reminder_count BIGINT,
    activity_update_count BIGINT,
    community_invite_count BIGINT,
    new_member_count BIGINT,
    new_post_count BIGINT,
    comment_count BIGINT,
    reaction_count BIGINT,
    mention_count BIGINT,
    profile_view_count BIGINT,
    new_favorite_count BIGINT,
    system_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_unread,
        COUNT(*) FILTER (WHERE notification_type = 'activity_invite')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'activity_reminder')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'activity_update')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'community_invite')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'new_member')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'new_post')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'comment')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'reaction')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'mention')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'profile_view')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'new_favorite')::BIGINT,
        COUNT(*) FILTER (WHERE notification_type = 'system')::BIGINT
    FROM activity.notifications
    WHERE user_id = p_user_id
        AND status = 'unread'::activity.notification_status
        AND (
            p_include_premium_only = TRUE
            OR notification_type::VARCHAR NOT IN ('profile_view', 'new_favorite')
        );
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. sp_create_notification - Create new notification (internal service)
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_create_notification(
    p_user_id UUID,
    p_actor_user_id UUID,
    p_notification_type VARCHAR,
    p_target_type VARCHAR,
    p_target_id UUID,
    p_title VARCHAR,
    p_message TEXT DEFAULT NULL,
    p_payload JSONB DEFAULT NULL
)
RETURNS TABLE (
    notification_id UUID,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
DECLARE
    v_notification_id UUID;
    v_created_at TIMESTAMP WITH TIME ZONE;
    v_prefs_exist BOOLEAN;
    v_enabled_types JSONB;
    v_in_app_enabled BOOLEAN;
BEGIN
    -- Check user notification preferences
    SELECT
        in_app_enabled,
        enabled_types
    INTO
        v_in_app_enabled,
        v_enabled_types
    FROM activity.notification_preferences
    WHERE user_id = p_user_id;

    -- If no preferences exist, create defaults
    IF NOT FOUND THEN
        INSERT INTO activity.notification_preferences (user_id)
        VALUES (p_user_id)
        RETURNING in_app_enabled, enabled_types
        INTO v_in_app_enabled, v_enabled_types;
    END IF;

    -- Check if notification type is enabled
    IF v_in_app_enabled = FALSE OR NOT (v_enabled_types ? p_notification_type) THEN
        -- Return empty result (notification skipped)
        RETURN;
    END IF;

    -- Create notification
    INSERT INTO activity.notifications (
        user_id,
        actor_user_id,
        notification_type,
        target_type,
        target_id,
        title,
        message,
        payload
    ) VALUES (
        p_user_id,
        p_actor_user_id,
        p_notification_type::activity.notification_type,
        p_target_type,
        p_target_id,
        p_title,
        p_message,
        p_payload
    )
    RETURNING notifications.notification_id, notifications.created_at
    INTO v_notification_id, v_created_at;

    RETURN QUERY SELECT v_notification_id, v_created_at;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. sp_get_notification_settings - Get user notification preferences
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_get_notification_settings(
    p_user_id UUID
)
RETURNS TABLE (
    email_enabled BOOLEAN,
    push_enabled BOOLEAN,
    in_app_enabled BOOLEAN,
    enabled_types JSONB,
    quiet_hours_start TIME,
    quiet_hours_end TIME
) AS $$
BEGIN
    -- Ensure preferences exist, create if not
    INSERT INTO activity.notification_preferences (user_id)
    VALUES (p_user_id)
    ON CONFLICT (user_id) DO NOTHING;

    RETURN QUERY
    SELECT
        np.email_enabled,
        np.push_enabled,
        np.in_app_enabled,
        np.enabled_types,
        np.quiet_hours_start,
        np.quiet_hours_end
    FROM activity.notification_preferences np
    WHERE np.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 9. sp_update_notification_settings - Update user notification preferences
-- ============================================================================
CREATE OR REPLACE FUNCTION activity.sp_update_notification_settings(
    p_user_id UUID,
    p_email_enabled BOOLEAN DEFAULT NULL,
    p_push_enabled BOOLEAN DEFAULT NULL,
    p_in_app_enabled BOOLEAN DEFAULT NULL,
    p_enabled_types JSONB DEFAULT NULL,
    p_quiet_hours_start TIME DEFAULT NULL,
    p_quiet_hours_end TIME DEFAULT NULL
)
RETURNS TABLE (
    email_enabled BOOLEAN,
    push_enabled BOOLEAN,
    in_app_enabled BOOLEAN,
    enabled_types JSONB,
    quiet_hours_start TIME,
    quiet_hours_end TIME
) AS $$
BEGIN
    -- Ensure preferences exist
    INSERT INTO activity.notification_preferences (user_id)
    VALUES (p_user_id)
    ON CONFLICT (user_id) DO NOTHING;

    -- Update only provided fields
    UPDATE activity.notification_preferences
    SET
        email_enabled = COALESCE(p_email_enabled, email_enabled),
        push_enabled = COALESCE(p_push_enabled, push_enabled),
        in_app_enabled = COALESCE(p_in_app_enabled, in_app_enabled),
        enabled_types = COALESCE(p_enabled_types, enabled_types),
        quiet_hours_start = COALESCE(p_quiet_hours_start, quiet_hours_start),
        quiet_hours_end = COALESCE(p_quiet_hours_end, quiet_hours_end),
        updated_at = NOW()
    WHERE user_id = p_user_id;

    -- Return updated settings
    RETURN QUERY
    SELECT
        np.email_enabled,
        np.push_enabled,
        np.in_app_enabled,
        np.enabled_types,
        np.quiet_hours_start,
        np.quiet_hours_end
    FROM activity.notification_preferences np
    WHERE np.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================
GRANT EXECUTE ON FUNCTION activity.sp_get_user_notifications TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_get_notification_by_id TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_mark_notification_as_read TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_mark_notifications_as_read_bulk TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_delete_notification TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_get_unread_count TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_create_notification TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_get_notification_settings TO postgres;
GRANT EXECUTE ON FUNCTION activity.sp_update_notification_settings TO postgres;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- List all notification stored procedures
SELECT
    n.nspname as schema,
    p.proname as procedure_name,
    pg_get_function_arguments(p.oid) as arguments
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'activity'
    AND p.proname LIKE 'sp_%notification%'
ORDER BY p.proname;
