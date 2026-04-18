#!/bin/bash

# AlphaVelocity - Unified Service Management Script
# Manages PostgreSQL and FastAPI Backend (frontend is served by FastAPI)

set -e

# Configuration
BACKEND_SCRIPT="/alpha_velocity/server.sh"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

is_postgres_running() {
    pg_isready > /dev/null 2>&1
    return $?
}

start_postgres() {
    print_msg "$YELLOW" "Starting PostgreSQL..."

    if is_postgres_running; then
        print_msg "$GREEN" "✓ PostgreSQL is already running"
        return 0
    fi

    sudo service postgresql start

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

stop_postgres() {
    print_msg "$YELLOW" "Stopping PostgreSQL..."

    if is_postgres_running; then
        sudo service postgresql stop
        print_msg "$GREEN" "✓ PostgreSQL stopped"
    else
        print_msg "$YELLOW" "PostgreSQL is not running"
    fi
}

start_backend() {
    print_msg "$YELLOW" "Starting FastAPI Backend..."

    if [ ! -f "$BACKEND_SCRIPT" ]; then
        print_msg "$RED" "✗ Backend script not found: $BACKEND_SCRIPT"
        return 1
    fi

    $BACKEND_SCRIPT start
}

stop_backend() {
    print_msg "$YELLOW" "Stopping FastAPI Backend..."

    if [ -f "$BACKEND_SCRIPT" ]; then
        $BACKEND_SCRIPT stop
    else
        print_msg "$YELLOW" "Backend script not found, skipping"
    fi
}

start_all() {
    print_header "Starting AlphaVelocity"

    start_postgres || { print_msg "$RED" "Failed to start PostgreSQL"; return 1; }
    echo ""
    start_backend || { print_msg "$RED" "Failed to start backend"; return 1; }

    print_header "AlphaVelocity is running"
    print_msg "$GREEN" "  App:      http://localhost:8000/"
    print_msg "$GREEN" "  API Docs: http://localhost:8000/docs"
    echo ""
    print_msg "$YELLOW" "  Logs: tail -f /tmp/alphavelocity.log"
    echo ""
}

stop_all() {
    print_header "Stopping AlphaVelocity"

    stop_backend
    echo ""
    stop_postgres

    print_header "All Services Stopped"
}

restart_all() {
    stop_all
    sleep 2
    start_all
}

status_all() {
    print_header "AlphaVelocity Service Status"

    print_msg "$BLUE" "PostgreSQL:"
    if is_postgres_running; then
        print_msg "$GREEN" "  ✓ Running"
        pg_isready 2>&1 | sed 's/^/    /'
    else
        print_msg "$RED" "  ✗ Not running"
    fi
    echo ""

    print_msg "$BLUE" "FastAPI Backend:"
    if [ -f "$BACKEND_SCRIPT" ]; then
        $BACKEND_SCRIPT status 2>&1 | sed 's/^/  /'
    else
        print_msg "$RED" "  ✗ Backend script not found"
    fi
    echo ""

    print_msg "$BLUE" "Access URLs:"
    if is_postgres_running; then
        print_msg "$GREEN" "  App:      http://localhost:8000/"
        print_msg "$GREEN" "  API Docs: http://localhost:8000/docs"
    else
        print_msg "$YELLOW" "  Some services are not running"
    fi
    echo ""
}

usage() {
    cat << EOF
AlphaVelocity - Service Management

Usage: $0 {start|stop|restart|status|logs}

Commands:
  start      Start PostgreSQL + FastAPI backend
  stop       Stop all services
  restart    Restart all services
  status     Show service status
  logs       Follow backend logs

Access:
  App:      http://localhost:8000/
  API Docs: http://localhost:8000/docs
EOF
}

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
        $BACKEND_SCRIPT logs
        ;;
    *)
        usage
        exit 1
        ;;
esac
