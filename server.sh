#!/bin/bash

# AlphaVelocity Server Management Script
# Safely manages the FastAPI backend server

set -e

# Configuration
APP_MODULE="backend.main:app"
HOST="0.0.0.0"
PORT=8000
PID_FILE="/tmp/alphavelocity.pid"
LOG_FILE="/tmp/alphavelocity.log"
MAX_STARTUP_TIME=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored message
print_msg() {
    local color=$1
    shift
    echo -e "${color}$@${NC}"
}

# Check if server is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Get server status
status() {
    if is_running; then
        local pid=$(cat "$PID_FILE")
        print_msg "$GREEN" "✓ Server is running (PID: $pid)"

        # Check if port is actually listening
        if lsof -i :$PORT > /dev/null 2>&1; then
            print_msg "$GREEN" "✓ Port $PORT is listening"
        else
            print_msg "$YELLOW" "⚠ Warning: Process running but port $PORT not listening"
        fi

        # Show resource usage
        echo ""
        ps -p "$pid" -o pid,ppid,%cpu,%mem,etime,cmd 2>/dev/null || true

        return 0
    else
        print_msg "$YELLOW" "Server is not running"

        # Check for orphaned processes
        local orphans=$(pgrep -f "uvicorn.*$APP_MODULE" 2>/dev/null || true)
        if [ -n "$orphans" ]; then
            print_msg "$YELLOW" "⚠ Found orphaned processes: $orphans"
        fi

        return 1
    fi
}

# Stop the server
stop() {
    print_msg "$YELLOW" "Stopping server..."

    if is_running; then
        local pid=$(cat "$PID_FILE")

        # Try graceful shutdown first (SIGTERM)
        print_msg "$YELLOW" "Sending SIGTERM to PID $pid..."
        kill -TERM "$pid" 2>/dev/null || true

        # Wait for graceful shutdown
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [ $count -lt 5 ]; do
            sleep 1
            count=$((count + 1))
        done

        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            print_msg "$YELLOW" "Process still running, sending SIGKILL..."
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi

        rm -f "$PID_FILE"
        print_msg "$GREEN" "✓ Server stopped"
    else
        print_msg "$YELLOW" "Server is not running"
    fi

    # Clean up any orphaned processes
    cleanup_orphans
}

# Clean up orphaned processes
cleanup_orphans() {
    local orphans=$(pgrep -f "uvicorn.*$APP_MODULE" 2>/dev/null || true)

    if [ -n "$orphans" ]; then
        print_msg "$YELLOW" "Cleaning up orphaned processes: $orphans"
        echo "$orphans" | xargs kill -TERM 2>/dev/null || true
        sleep 2

        # Force kill if still there
        orphans=$(pgrep -f "uvicorn.*$APP_MODULE" 2>/dev/null || true)
        if [ -n "$orphans" ]; then
            echo "$orphans" | xargs kill -9 2>/dev/null || true
        fi
    fi

    # Clean up any process holding the port
    local port_pid=$(lsof -ti :$PORT 2>/dev/null || true)
    if [ -n "$port_pid" ]; then
        print_msg "$YELLOW" "Cleaning up process on port $PORT (PID: $port_pid)"
        kill -TERM "$port_pid" 2>/dev/null || true
        sleep 1

        # Force kill if needed
        if lsof -ti :$PORT > /dev/null 2>&1; then
            kill -9 "$port_pid" 2>/dev/null || true
        fi
    fi
}

# Start the server
start() {
    if is_running; then
        print_msg "$YELLOW" "Server is already running"
        status
        return 1
    fi

    print_msg "$GREEN" "Starting AlphaVelocity server..."

    # Clean up any orphaned processes first
    cleanup_orphans

    # Ensure log directory exists
    touch "$LOG_FILE"

    # Start the server
    nohup uvicorn "$APP_MODULE" \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        > "$LOG_FILE" 2>&1 &

    local pid=$!
    echo $pid > "$PID_FILE"

    print_msg "$YELLOW" "Waiting for server to start (PID: $pid)..."

    # Wait for server to start
    local count=0
    local started=false

    while [ $count -lt $MAX_STARTUP_TIME ]; do
        if lsof -i :$PORT > /dev/null 2>&1; then
            started=true
            break
        fi

        # Check if process died
        if ! ps -p $pid > /dev/null 2>&1; then
            print_msg "$RED" "✗ Server process died during startup"
            print_msg "$RED" "Check logs: tail -f $LOG_FILE"
            rm -f "$PID_FILE"
            return 1
        fi

        sleep 1
        count=$((count + 1))
    done

    if [ "$started" = true ]; then
        print_msg "$GREEN" "✓ Server started successfully!"
        print_msg "$GREEN" "  Frontend: http://localhost:$PORT/"
        print_msg "$GREEN" "  API Docs: http://localhost:$PORT/docs"
        print_msg "$GREEN" "  Logs: tail -f $LOG_FILE"
    else
        print_msg "$RED" "✗ Server failed to start within ${MAX_STARTUP_TIME}s"
        print_msg "$RED" "Check logs: tail -f $LOG_FILE"
        stop
        return 1
    fi
}

# Restart the server
restart() {
    print_msg "$YELLOW" "Restarting server..."
    stop
    sleep 2
    start
}

# Show logs
logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        print_msg "$YELLOW" "Log file not found: $LOG_FILE"
    fi
}

# Show recent logs
recent_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -n 50 "$LOG_FILE"
    else
        print_msg "$YELLOW" "Log file not found: $LOG_FILE"
    fi
}

# Show usage
usage() {
    cat << EOF
AlphaVelocity Server Management Script

Usage: $0 {start|stop|restart|status|logs|recent-logs|cleanup}

Commands:
  start        Start the server
  stop         Stop the server
  restart      Restart the server
  status       Show server status
  logs         Follow server logs (tail -f)
  recent-logs  Show recent logs (last 50 lines)
  cleanup      Clean up orphaned processes

Files:
  PID:  $PID_FILE
  Logs: $LOG_FILE
EOF
}

# Main command handler
case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    recent-logs)
        recent_logs
        ;;
    cleanup)
        cleanup_orphans
        ;;
    *)
        usage
        exit 1
        ;;
esac
