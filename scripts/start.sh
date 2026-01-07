#!/bin/bash
# =============================================================================
# Research Agent - Unix/Linux/Mac Startup Script
# =============================================================================

set -e

echo ""
echo "========================================"
echo "  Autonomous Research Agent"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

show_usage() {
    echo "Usage: ./start.sh [docker|local]"
    echo ""
    echo "  docker  - Start using Docker (recommended for production)"
    echo "  local   - Start using local Python environment"
    echo ""
}

start_docker() {
    echo "Starting with Docker..."
    cd "$PROJECT_DIR"
    docker-compose up -d
    echo ""
    echo "Application started at: http://localhost:8501"
    echo ""
    echo "Commands:"
    echo "  - View logs:  docker-compose logs -f"
    echo "  - Stop:       docker-compose down"
    echo ""
}

start_local() {
    echo "Starting locally..."
    cd "$PROJECT_DIR"

    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Virtual environment not found. Creating..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    fi

    echo ""
    echo "Starting Streamlit server..."
    streamlit run streamlit_app.py
}

case "$1" in
    docker)
        start_docker
        ;;
    local)
        start_local
        ;;
    *)
        show_usage
        ;;
esac
