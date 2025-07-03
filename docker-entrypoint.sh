#!/bin/sh

set -e

echo "Starting MetaMCP services..."

# Function to wait for postgres
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
        echo "PostgreSQL is not ready - sleeping 2 seconds"
        sleep 2
    done
    echo "PostgreSQL is ready!"
}

# Function to run migrations
run_migrations() {
    echo "Running database migrations..."
    cd /app/apps/backend
    
    # Check if migrations need to be run
    if [ -d "drizzle" ] && [ "$(ls -A drizzle/*.sql 2>/dev/null)" ]; then
        echo "Found migration files, running migrations..."
        # Use local drizzle-kit since env vars are available at system level in Docker
        if pnpm exec drizzle-kit migrate; then
            echo "Migrations completed successfully!"
        else
            echo "❌ Migration failed! Exiting..."
            exit 1
        fi
    else
        echo "No migrations found or directory empty"
    fi
    
    cd /app
}

# Function to wait for frontend and open browser
wait_for_frontend_and_open_browser() {
    echo "Waiting for frontend to be ready..."
    MAX_ATTEMPTS=30
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        if curl -s http://localhost:12008 > /dev/null 2>&1; then
            echo "🚀 Frontend is ready!"
            echo "🌐 Opening browser..."
            
            # Try to open browser using host-spawn
            if command -v host-spawn > /dev/null; then
                host-spawn /opt/google/chrome-unstable/chrome http://localhost:12008 || \
                host-spawn /usr/bin/google-chrome http://localhost:12008 || \
                echo "Could not open browser - please open http://localhost:12008 manually" || \
            else
                echo "host-spawn not available - please open http://localhost:12020 manually"
            fi
            
            return 0
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
        echo "Frontend not ready yet - attempt $ATTEMPT/$MAX_ATTEMPTS"
        sleep 2
    done
    
    echo "❌ Frontend did not become ready within expected time"
    return 1
}

# Set default values for postgres connection if not provided
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-postgres}

# Wait for PostgreSQL
wait_for_postgres

# Run migrations
run_migrations

# Start backend in the background
echo "Starting backend server..."
cd /app/apps/backend
PORT=12009 node dist/index.js &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Check if backend is still running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend server died! Exiting..."
    exit 1
fi
echo "✅ Backend server started successfully (PID: $BACKEND_PID)"

# Start frontend
echo "Starting frontend server..."
cd /app/apps/frontend
PORT=12008 pnpm start &
FRONTEND_PID=$!

# Wait a moment for frontend to start
sleep 3

# Check if frontend is still running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "❌ Frontend server died! Exiting..."
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi
echo "✅ Frontend server started successfully (PID: $FRONTEND_PID)"

# Function to cleanup on exit
cleanup() {
    echo "Shutting down services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID 2>/dev/null || true
    wait $FRONTEND_PID 2>/dev/null || true
    echo "Services stopped"
}

# Trap signals for graceful shutdown
trap cleanup TERM INT

echo "Services started successfully!"
echo "Backend running on port 12009"
echo "Frontend running on port 12008"

# Wait for both processes
wait $BACKEND_PID
wait $FRONTEND_PID 