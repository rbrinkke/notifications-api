#!/bin/bash
# Quick seed script - auto-detects environment and runs appropriate method

set -e

echo "🚀 Quick Notifications Seed Script"
echo "===================================="
echo ""

# Check if we're in Docker environment
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    echo "📦 Docker environment detected"
    DOCKER_MODE=true
else
    echo "💻 Local environment detected"
    DOCKER_MODE=false
fi

# Check what's available
if command -v psql &> /dev/null; then
    echo "✅ psql found - using SQL script (fastest)"
    METHOD="sql"
elif command -v python3 &> /dev/null; then
    echo "✅ Python found - using Python script"
    METHOD="python"
else
    echo "❌ Neither psql nor python3 found"
    echo "   Please install PostgreSQL client or Python 3"
    exit 1
fi

echo ""
echo "Starting seed process..."
echo ""

# Load .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Use defaults if not set
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-activity_platform}"
DB_USER="${DB_USER:-api_user}"
DB_PASSWORD="${DB_PASSWORD:-changeme}"

if [ "$METHOD" = "sql" ]; then
    # Try to run SQL script
    if [ "$DOCKER_MODE" = true ]; then
        # In Docker, connect directly
        PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f seed_notifications.sql
    else
        # Local, might need Docker exec
        if docker ps | grep -q postgres; then
            echo "Using Docker PostgreSQL container..."
            docker exec -i $(docker ps | grep postgres | awk '{print $1}') \
                psql -U "$DB_USER" -d "$DB_NAME" < seed_notifications.sql
        else
            PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f seed_notifications.sql
        fi
    fi
else
    # Python method
    if ! pip list 2>/dev/null | grep -q psycopg2; then
        echo "📦 Installing psycopg2-binary..."
        pip install psycopg2-binary python-dotenv -q
    fi

    python3 seed_notifications.py
fi

echo ""
echo "✨ All done!"
