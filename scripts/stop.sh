#!/bin/bash
# =============================================================================
# Research Agent - Unix/Linux/Mac Stop Script
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo ""
echo "Stopping Research Agent..."
echo ""

show_usage() {
    echo "Usage: ./stop.sh [docker|local]"
    echo ""
    echo "  docker  - Stop Docker containers"
    echo "  local   - Stop local Streamlit process"
    echo ""
}

stop_docker() {
    echo "Stopping Docker containers..."
    cd "$PROJECT_DIR"
    docker-compose down
    echo "Done."
}

stop_local() {
    echo "Stopping local Streamlit process..."
    pkill -f "streamlit run" 2>/dev/null && echo "Streamlit stopped." || echo "No Streamlit process found."
}

case "$1" in
    docker)
        stop_docker
        ;;
    local)
        stop_local
        ;;
    *)
        show_usage
        ;;
esac
