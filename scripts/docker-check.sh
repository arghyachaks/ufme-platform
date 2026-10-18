#!/usr/bin/env bash
# Local Docker gate: build + start the full stack, run all checks inside containers, smoke-test.
# Used by the git pre-push hook; can also be run directly. Log: tmp/docker-check.log
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p tmp
LOG="$ROOT/tmp/docker-check.log"
DC="docker compose -f infra/docker/docker-compose.yml"
exec > >(tee "$LOG") 2>&1

step() { printf '\n==== %s\n' "$*"; }
fail() { printf '\nRESULT: FAIL (%s)\n' "$*"; exit 1; }
wait_http() { # url, seconds
  for _ in $(seq 1 "$2"); do curl -fsS -o /dev/null "$1" 2>/dev/null && return 0; sleep 1; done; return 1
}

step "Docker"
docker info --format 'Docker {{.ServerVersion}}' || fail "Docker is not running - start Docker Desktop"

step "Build images"
$DC --profile test build || fail "image build"

step "Start stack (postgres, redis, api, worker, web)"
$DC up -d --wait postgres redis api worker web || { $DC ps; $DC logs --tail 60 api worker web; fail "stack did not become healthy"; }
$DC exec -T postgres psql -U ufme -d ufme -tc "SELECT 1 FROM pg_database WHERE datname='ufme_test'" | grep -q 1 \
  || $DC exec -T postgres psql -U ufme -d ufme -c "CREATE DATABASE ufme_test OWNER ufme" || fail "create test db"

step "Backend: ruff, mypy, pytest (Postgres)"
$DC --profile test run --rm api-test || fail "backend checks"

step "Frontend: type-check + production build"
$DC --profile test run --rm web-test || fail "frontend build"

step "Smoke tests"
wait_http http://localhost:8000/api/v1/health/ready 30 || fail "API not ready on :8000"
curl -fsS http://localhost:8000/api/v1/health/ready; echo
wait_http http://localhost:5173/ 60 || fail "web not serving on :5173"
curl -fsS http://localhost:5173/api/v1/health | grep -q '"ok"' || fail "web -> api proxy"
echo "web :5173 ok, proxy -> api ok"
$DC exec -T worker celery -A app.workers.celery_app call ufme.ping >/dev/null || fail "worker task"
echo "worker ok"

$DC ps
printf '\nRESULT: PASS\n'
