#!/usr/bin/env bash
#
# MCP World 검증형 배포 (로컬 -> VPS). rsync 불필요 (tar + ssh만 사용).
#
# 흐름: 로컬 테스트 -> tar로 업로드(.new) -> 원자적 스왑(.old=롤백) -> nginx 검사
#       -> mcpworld-api 재시작 -> 헬스체크 -> 실패 시 .old로 자동 롤백.
#
# "깨진 코드가 라이브로 안 남는다"가 목표: 테스트 실패면 배포를 시작도 안 하고,
# 재시작 후 서비스가 안 뜨면(import/문법 오류 등) 직전 버전(.old)으로 자동 복구.
#
# 사용법:
#   bash deploy/deploy.sh             # 검증형 배포
#   DRY_RUN=1 bash deploy/deploy.sh   # 배포될 파일 목록만 미리보기(원격 변경 없음)
#   SKIP_TESTS=1 bash deploy/deploy.sh  # (비권장) 로컬 테스트 생략
#
# 필요: 로컬에 ssh, tar (Git for Windows / WSL 기본 포함). VPS SSH 별칭은 myserver-root.
# DB(/var/lib/mcpworld)와 시크릿(/etc/mcpworld/session.env)은 동기화 대상이 아니라 보존됩니다.

set -euo pipefail

SSH_TARGET="${MCPWORLD_SSH:-myserver-root}"
REMOTE_DIR="${MCPWORLD_REMOTE_DIR:-/var/www/mcpworld}"
SERVICE="${MCPWORLD_SERVICE:-mcpworld-api}"
OWNER="${MCPWORLD_OWNER:-www-data:www-data}"
HEALTH_PORT="${MCPWORLD_HEALTH_PORT:-33210}"
PYTHON_BIN="${PYTHON_BIN:-python}"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log()  { printf '\n==> %s\n' "$*"; }
fail() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

# Never deploy these (vcs/venv/build/test/db/secret artifacts).
EXCLUDES=(
  --exclude='./.git' --exclude='./.gitignore' --exclude='./.github'
  --exclude='./.venv' --exclude='./venv'
  --exclude='./dist' --exclude='./local_artifacts' --exclude='./.test-tmp' --exclude='./.pytest_cache'
  --exclude='./installer' --exclude='./tests'
  --exclude='*.tmp' --exclude='*.tar.gz' --exclude='*.bak' --exclude='*.bak-*'
  --exclude='./write_test.txt'
  --exclude='*__pycache__*' --exclude='*.pyc'
  --exclude='*/node_modules' --exclude='*/.wrangler'
  --exclude='*.sqlite3' --exclude='*.sqlite3-*'
  --exclude='./.env' --exclude='*/session.env'
)

# Restore the previous version (.old) and bring the service back up.
rollback() {
  printf '\n!! 배포 중단/헬스 실패: %s — 직전 버전(.old)으로 롤백합니다.\n' "${1:-unknown}" >&2
  ssh "$SSH_TARGET" "
    if [ -d '$REMOTE_DIR.old' ]; then
      rm -rf '$REMOTE_DIR.failed'
      mv '$REMOTE_DIR' '$REMOTE_DIR.failed' 2>/dev/null || true
      mv '$REMOTE_DIR.old' '$REMOTE_DIR'
      chown -R '$OWNER' '$REMOTE_DIR'
      systemctl restart '$SERVICE'
      systemctl reload nginx
    fi
  " || true
  fail "롤백 완료 (직전 버전 복구). 새 배포는 적용되지 않았습니다. 원인은 위 로그를 확인하세요."
}

# 1) Local validation gate — a failing test aborts BEFORE touching the VPS.
if [ "${SKIP_TESTS:-0}" = "1" ]; then
  log "1/5 로컬 테스트 생략 (SKIP_TESTS=1)"
else
  log "1/5 로컬 테스트 (실패 시 배포 중단)"
  "$PYTHON_BIN" -m pytest "$LOCAL_DIR/tests" -q || fail "테스트 실패 — 배포를 중단합니다."
fi

# DRY_RUN: show exactly what would ship, without touching the VPS.
if [ "${DRY_RUN:-0}" = "1" ]; then
  log "DRY_RUN: 배포될 파일 목록 (원격 변경 없음)"
  tar czf - -C "$LOCAL_DIR" "${EXCLUDES[@]}" . | tar tzf - | sed 's#^\./##' | grep -v '/$' | sort
  log "DRY_RUN 종료 — 실제 배포는 DRY_RUN 없이 실행하세요."
  exit 0
fi

# 2) Upload a fresh copy into $REMOTE_DIR.new (current live dir untouched yet).
log "2/5 업로드 (tar over ssh) -> $REMOTE_DIR.new"
tar czf - -C "$LOCAL_DIR" "${EXCLUDES[@]}" . \
  | ssh "$SSH_TARGET" "rm -rf '$REMOTE_DIR.new' && mkdir -p '$REMOTE_DIR.new' && tar xzf - -C '$REMOTE_DIR.new'" \
  || fail "업로드 실패 — 원격은 변경되지 않았습니다."

# 3) Atomic swap: keep the current live dir as .old (rollback point).
log "3/5 원자적 스왑 (.old = 롤백 지점)"
ssh "$SSH_TARGET" "
  rm -rf '$REMOTE_DIR.old'
  [ -d '$REMOTE_DIR' ] && mv '$REMOTE_DIR' '$REMOTE_DIR.old'
  mv '$REMOTE_DIR.new' '$REMOTE_DIR'
  chown -R '$OWNER' '$REMOTE_DIR'
" || rollback "스왑 실패"

# 4) nginx config test, then restart the API and reload nginx.
log "4/5 nginx 검사 + $SERVICE 재시작 + nginx reload"
ssh "$SSH_TARGET" "nginx -t" || rollback "nginx 설정 검사 실패"
ssh "$SSH_TARGET" "systemctl restart '$SERVICE' && systemctl reload nginx" || rollback "서비스 재시작 실패"

# 5) Health check — roll back automatically if the service did not come up clean.
log "5/5 헬스체크"
sleep 2
ACTIVE="$(ssh "$SSH_TARGET" "systemctl is-active '$SERVICE' || true")"
[ "$ACTIVE" = "active" ] || rollback "systemctl is-active=$ACTIVE"
ssh "$SSH_TARGET" "curl -sS -o /dev/null --max-time 5 http://127.0.0.1:$HEALTH_PORT/tools/catalog" \
  || rollback "포트 $HEALTH_PORT 무응답"

log "배포 성공 — $SERVICE active, 포트 $HEALTH_PORT 응답 OK. (롤백본: $REMOTE_DIR.old)"
