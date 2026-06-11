#!/usr/bin/env bash
# Start/stop both the backend (FastAPI/uvicorn) and frontend (Vite) together.
#
#   ./dev.sh start     launch both (backend :8000, frontend :5173)
#   ./dev.sh stop      stop both
#   ./dev.sh restart   stop then start
#   ./dev.sh status    show whether each is running
#   ./dev.sh logs      tail both logs
#
# PIDs and logs live in .dev/ (git-ignored).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_DIR="$ROOT/.dev"
VENV="$ROOT/.venv"
BACKEND_PID="$DEV_DIR/backend.pid"
FRONTEND_PID="$DEV_DIR/frontend.pid"
BACKEND_LOG="$DEV_DIR/backend.log"
FRONTEND_LOG="$DEV_DIR/frontend.log"

mkdir -p "$DEV_DIR"

_running() {  # $1 = pidfile
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

start_backend() {
  if _running "$BACKEND_PID"; then
    echo "backend already running (pid $(cat "$BACKEND_PID"))"
    return
  fi
  if [ ! -x "$VENV/bin/uvicorn" ]; then
    echo "error: $VENV/bin/uvicorn not found — create the venv and pip install -r backend/requirements.txt" >&2
    exit 1
  fi
  echo "starting backend → http://localhost:8000  (log: $BACKEND_LOG)"
  (
    cd "$ROOT/backend"
    # Load backend/.env (e.g. ANTHROPIC_API_KEY) if present.
    if [ -f .env ]; then set -a; . ./.env; set +a; fi
    exec "$VENV/bin/uvicorn" app.main:app --reload --port 8000
  ) >"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID"
}

start_frontend() {
  if _running "$FRONTEND_PID"; then
    echo "frontend already running (pid $(cat "$FRONTEND_PID"))"
    return
  fi
  echo "starting frontend → http://localhost:5173  (log: $FRONTEND_LOG)"
  ( cd "$ROOT/frontend" && exec npm run dev ) >"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID"
}

stop_one() {  # $1 = name, $2 = pidfile
  if _running "$2"; then
    local pid; pid="$(cat "$2")"
    echo "stopping $1 (pid $pid)"
    # Kill children first (uvicorn reload worker, vite) then the parent.
    pkill -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
    rm -f "$2"
  else
    echo "$1 not running"
    rm -f "$2"
  fi
}

status_one() {  # $1 = name, $2 = pidfile
  if _running "$2"; then
    echo "  $1: running (pid $(cat "$2"))"
  else
    echo "  $1: stopped"
  fi
}

case "${1:-}" in
  start)
    start_backend
    start_frontend
    echo "done. './dev.sh logs' to tail, './dev.sh stop' to stop."
    ;;
  stop)
    stop_one frontend "$FRONTEND_PID"
    stop_one backend "$BACKEND_PID"
    ;;
  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;
  status)
    echo "status:"
    status_one backend "$BACKEND_PID"
    status_one frontend "$FRONTEND_PID"
    ;;
  logs)
    tail -n 40 -f "$BACKEND_LOG" "$FRONTEND_LOG"
    ;;
  *)
    echo "usage: $0 {start|stop|restart|status|logs}" >&2
    exit 1
    ;;
esac
