#!/bin/bash

# AlphaVelocity - Unified Service Management Script
# Manages PostgreSQL, FastAPI Backend, and Frontend Server

set -e

# Configuration
FRONTEND_PORT=3000
FRONTEND_PID_FILE="/tmp/frontend_server.pid"
FRONTEND_LOG_FILE="/tmp/frontend_server.log"
BACKEND_SCRIPT="/alpha_velocity/server.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

print_header() {
    echo ""
    print_msg "$BLUE" "=========================================="
    print_msg "$BLUE" "$@"
    print_msg "$BLUE" "=========================================="
    echo ""
}

# Check if PostgreSQL is running
is_postgres_running() {
    pg_isready > /dev/null 2>&1
    return $?
}

# Check if frontend is running
is_frontend_running() {
    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid=$(cat "$FRONTEND_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$FRONTEND_PID_FILE"
            return 1
        fi
    fi

    # Fallback: check if port is in use
    lsof -i :$FRONTEND_PORT > /dev/null 2>&1
    return $?
}

# Start PostgreSQL
start_postgres() {
    print_msg "$YELLOW" "Starting PostgreSQL..."

    if is_postgres_running; then
        print_msg "$GREEN" "✓ PostgreSQL is already running"
        return 0
    fi

    sudo service postgresql start

    # Wait for PostgreSQL to be ready
    local count=0
    while [ $count -lt 10 ]; do
        if is_postgres_running; then
            print_msg "$GREEN" "✓ PostgreSQL started successfully"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done

    print_msg "$RED" "✗ PostgreSQL failed to start"
    return 1
}

# Stop PostgreSQL
stop_postgres() {
    print_msg "$YELLOW" "Stopping PostgreSQL..."

    if is_postgres_running; then
        sudo service postgresql stop
        print_msg "$GREEN" "✓ PostgreSQL stopped"
    else
        print_msg "$YELLOW" "PostgreSQL is not running"
    fi
}

# Start Backend
start_backend() {
    print_msg "$YELLOW" "Starting FastAPI Backend..."

    if [ ! -f "$BACKEND_SCRIPT" ]; then
        print_msg "$RED" "✗ Backend script not found: $BACKEND_SCRIPT"
        return 1
    fi

    $BACKEND_SCRIPT start
}

# Stop Backend
stop_backend() {
    print_msg "$YELLOW" "Stopping FastAPI Backend..."

    if [ -f "$BACKEND_SCRIPT" ]; then
        $BACKEND_SCRIPT stop
    else
        print_msg "$YELLOW" "Backend script not found, skipping"
    fi
}

# Start Frontend
start_frontend() {
    print_msg "$YELLOW" "Starting Frontend Server..."

    if is_frontend_running; then
        print_msg "$GREEN" "✓ Frontend is already running"
        return 0
    fi

    # Clean up any orphaned processes on the port
    local port_pid=$(lsof -ti :$FRONTEND_PORT 2>/dev/null || true)
    if [ -n "$port_pid" ]; then
        print_msg "$YELLOW" "Cleaning up process on port $FRONTEND_PORT (PID: $port_pid)"
        kill -TERM "$port_pid" 2>/dev/null || true
        sleep 1
    fi

    # Start the frontend server
    nohup python /alpha_velocity/frontend_server.py $FRONTEND_PORT > "$FRONTEND_LOG_FILE" 2>&1 &
    local pid=$!
    echo $pid > "$FRONTEND_PID_FILE"

    print_msg "$YELLOW" "Waiting for frontend to start (PID: $pid)..."

    # Wait for frontend to start
    local count=0
    while [ $count -lt 5 ]; do
        if lsof -i :$FRONTEND_PORT > /dev/null 2>&1; then
            print_msg "$GREEN" "✓ Frontend started successfully"
            return 0
        fi

        # Check if process died
        if ! ps -p $pid > /dev/null 2>&1; then
            print_msg "$RED" "✗ Frontend process died during startup"
            print_msg "$RED" "Check logs: tail -f $FRONTEND_LOG_FILE"
            rm -f "$FRONTEND_PID_FILE"
            return 1
        fi

        sleep 1
        count=$((count + 1))
    done

    print_msg "$RED" "✗ Frontend failed to start within 5s"
    return 1
}

# Stop Frontend
stop_frontend() {
    print_msg "$YELLOW" "Stopping Frontend Server..."

    if [ -f "$FRONTEND_PID_FILE" ]; then
        local pid=$(cat "$FRONTEND_PID_FILE")

        if ps -p "$pid" > /dev/null 2>&1; then
            kill -TERM "$pid" 2>/dev/null || true

            # Wait for graceful shutdown
            local count=0
            while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 5 ]; do
                sleep 1
                count=$((count + 1))
            done

            # Force kill if still running
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi

        rm -f "$FRONTEND_PID_FILE"
    fi

    # Clean up any orphaned processes
    local orphans=$(pgrep -f "python.*frontend_server.py" 2>/dev/null || true)
    if [ -n "$orphans" ]; then
        print_msg "$YELLOW" "Cleaning up orphaned frontend processes: $orphans"
        echo "$orphans" | xargs kill -TERM 2>/dev/null || true
        sleep 1
    fi

    # Clean up any process holding the port
    local port_pid=$(lsof -ti :$FRONTEND_PORT 2>/dev/null || true)
    if [ -n "$port_pid" ]; then
        print_msg "$YELLOW" "Cleaning up process on port $FRONTEND_PORT"
        kill -TERM "$port_pid" 2>/dev/null || true
    fi

    print_msg "$GREEN" "✓ Frontend stopped"
}

# Start all services
start_all() {
    print_header "🚀 Starting AlphaVelocity Services"

    # Start services in order
    start_postgres || { print_msg "$RED" "Failed to start PostgreSQL"; return 1; }
    echo ""

    start_backend || { print_msg "$RED" "Failed to start backend"; return 1; }
    echo ""

    start_frontend || { print_msg "$RED" "Failed to start frontend"; return 1; }

    print_header "✅ All Services Started"

    print_msg "$GREEN" "🌐 Access URLs:"
    print_msg "$GREEN" "  Frontend:  http://localhost:$FRONTEND_PORT/"
    print_msg "$GREEN" "  Backend:   http://localhost:8000/"
    print_msg "$GREEN" "  API Docs:  http://localhost:8000/docs"
    echo ""
    print_msg "$YELLOW" "📝 Log Files:"
    print_msg "$YELLOW" "  Backend:   tail -f /tmp/alphavelocity.log"
    print_msg "$YELLOW" "  Frontend:  tail -f $FRONTEND_LOG_FILE"
    echo ""
}

# Stop all services
stop_all() {
    print_header "🛑 Stopping AlphaVelocity Services"

    stop_frontend
    echo ""

    stop_backend
    echo ""

    stop_postgres

    print_header "✅ All Services Stopped"
}

# Restart all services
restart_all() {
    print_header "🔄 Restarting AlphaVelocity Services"

    stop_all
    sleep 2
    start_all
}

# Show status of all services
status_all() {
    print_header "📊 AlphaVelocity Service Status"

    # PostgreSQL status
    print_msg "$BLUE" "PostgreSQL Database:"
    if is_postgres_running; then
        print_msg "$GREEN" "  ✓ Running"
        pg_isready 2>&1 | sed 's/^/    /'
    else
        print_msg "$RED" "  ✗ Not running"
    fi
    echo ""

    # Backend status
    print_msg "$BLUE" "FastAPI Backend:"
    if [ -f "$BACKEND_SCRIPT" ]; then
        $BACKEND_SCRIPT status 2>&1 | sed 's/^/  /'
    else
        print_msg "$RED" "  ✗ Backend script not found"
    fi
    echo ""

    # Frontend status
    print_msg "$BLUE" "Frontend Server:"
    if is_frontend_running; then
        if [ -f "$FRONTEND_PID_FILE" ]; then
            local pid=$(cat "$FRONTEND_PID_FILE")
            print_msg "$GREEN" "  ✓ Running (PID: $pid, Port: $FRONTEND_PORT)"
            ps -p "$pid" -o pid,ppid,%cpu,%mem,etime,cmd 2>/dev/null | sed 's/^/    /' || true
        else
            print_msg "$GREEN" "  ✓ Running (Port: $FRONTEND_PORT)"
        fi
    else
        print_msg "$YELLOW" "  ✗ Not running"
    fi
    echo ""

    # Access URLs
    print_msg "$BLUE" "Access URLs:"
    if is_frontend_running && is_postgres_running; then
        print_msg "$GREEN" "  Frontend:  http://localhost:$FRONTEND_PORT/"
        print_msg "$GREEN" "  Backend:   http://localhost:8000/"
        print_msg "$GREEN" "  API Docs:  http://localhost:8000/docs"
    else
        print_msg "$YELLOW" "  Some services are not running"
    fi
    echo ""
}

# Show logs
logs() {
    local service=${1:-all}

    case "$service" in
        backend)
            print_msg "$BLUE" "📝 Backend logs (Ctrl+C to stop):"
            $BACKEND_SCRIPT logs
            ;;
        frontend)
            print_msg "$BLUE" "📝 Frontend logs (Ctrl+C to stop):"
            tail -f "$FRONTEND_LOG_FILE"
            ;;
        all)
            print_msg "$BLUE" "📝 All logs (Ctrl+C to stop):"
            tail -f /tmp/alphavelocity.log "$FRONTEND_LOG_FILE"
            ;;
        *)
            print_msg "$RED" "Unknown service: $service"
            print_msg "$YELLOW" "Valid options: backend, frontend, all"
            exit 1
            ;;
    esac
}

# Show usage
usage() {
    cat << EOF
AlphaVelocity - Unified Service Management

Usage: $0 {start|stop|restart|status|logs}

Commands:
  start      Start all services (PostgreSQL, Backend, Frontend)
  stop       Stop all services
  restart    Restart all services
  status     Show status of all services
  logs       Show logs from all services
             - logs backend   : Show backend logs only
             - logs frontend  : Show frontend logs only
             - logs all       : Show all logs (default)

Services:
  - PostgreSQL Database (port 5432)
  - FastAPI Backend (port 8000)
  - Frontend Server (port $FRONTEND_PORT)

Access:
  - Frontend:  http://localhost:$FRONTEND_PORT/
  - Backend:   http://localhost:8000/
  - API Docs:  http://localhost:8000/docs

Examples:
  $0 start           # Start everything
  $0 status          # Check what's running
  $0 logs backend    # Watch backend logs
  $0 restart         # Restart all services
  $0 stop            # Stop everything
EOF
}

# Main command handler
case "${1:-}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    restart)
        restart_all
        ;;
    status)
        status_all
        ;;
    logs)
        logs "${2:-all}"
        ;;
    *)
        usage
        exit 1
        ;;
esac
