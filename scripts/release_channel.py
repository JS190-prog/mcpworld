#!/usr/bin/env python3
"""MCPWorld 에이전트 릴리스 채널 + 승격 게이트.

두 채널(같은 코드, 다른 대상):
  edge   = 관리자 테스트 채널 (GitHub prerelease). 빌드마다 release/edge.json 갱신.
  stable = 소비자 채널 (GitHub latest). promote 만이 release/stable.json 을 갱신.

흐름:
  관리자 코드 수정 -> CI 가 edge 빌드 -> 관리자가 도구를 실제로 돌려보고
  결과를 기록(record) -> 게이트가 "최근 N회 연속 green + 마지막 헬스 ok" 를 요구(status)
  -> 관리자가 명시 승인으로 승격(promote): GitHub 릴리스를 latest 로 전환하고
     edge.json -> stable.json 으로 스왑(직전 stable 은 stable.json.prev 로 보존),
     사이트 다운로드를 새 태그로 재지정, 재배포. 문제가 있으면 rollback 으로
     직전 stable 복구.

자동 게이트 + 수동 승인:
  - 자동 게이트: 최근 N회(기본 3) 연속 green + 마지막 헬스 ok 가 아니면 승격 차단.
  - 수동 승인: 게이트를 통과해도 --confirm 없이는 stable 로 반영하지 않음.

순수 함수(load_ledger/record_result/green_streak/promotion_eligibility/
compute_promoted_manifest)는 단위 테스트 대상이고, promote/rollback 핸들러가
gh + deploy.sh 를 오케스트레이션한다.

사용 예:
  python scripts/release_channel.py record  --version 0.2.0-beta.3 --result pass --health ok
  python scripts/release_channel.py status   --version 0.2.0-beta.3
  python scripts/release_channel.py promote  --version 0.2.0-beta.3 --confirm
  python scripts/release_channel.py rollback --confirm
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "release"
EDGE = RELEASE_DIR / "edge.json"
STABLE = RELEASE_DIR / "stable.json"
STABLE_PREV = RELEASE_DIR / "stable.json.prev"
LATEST = RELEASE_DIR / "latest.json"  # 사이트 폴백 호환용 (stable 미러)
LEDGER = RELEASE_DIR / "test-ledger.json"
SITE_CONFIG = ROOT / "site-config.js"
DEFAULT_REPO = "JS190-prog/mcpworld"
DEFAULT_REQUIRED_GREEN = 3

# --------------------------------------------------------------------------- #
# 순수 로직 (단위 테스트 대상 — 파일/네트워크 부수효과 없음)
# --------------------------------------------------------------------------- #
def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def load_ledger(path=LEDGER):
    data = read_json(path, {})
    return data if isinstance(data, dict) else {}


def record_result(ledger, version, result, health="ok", note="", ts=None):
    """`version` 에 실행 결과 한 건을 덧붙인 새 ledger(dict)를 반환."""
    if result not in ("pass", "fail"):
        raise ValueError("result must be 'pass' or 'fail'")
    if health not in ("ok", "fail"):
        raise ValueError("health must be 'ok' or 'fail'")
    entry = {
        "ts": int(ts if ts is not None else time.time()),
        "result": result,
        "health": health,
        "note": note,
    }
    runs = list(ledger.get(version, []))
    runs.append(entry)
    new = dict(ledger)
    new[version] = runs
    return new


def green_streak(ledger, version):
    """가장 최근부터 연속으로 pass + health ok 인 실행 횟수."""
    streak = 0
    for run in reversed(ledger.get(version, [])):
        if run.get("result") == "pass" and run.get("health") == "ok":
            streak += 1
        else:
            break
    return streak


def promotion_eligibility(ledger, version, required_green=DEFAULT_REQUIRED_GREEN):
    """승격 적격 여부 + 사유. 자동 게이트의 판정 로직."""
    runs = ledger.get(version, [])
    streak = green_streak(ledger, version)
    last = runs[-1] if runs else None
    health_ok = bool(last and last.get("health") == "ok")
    if not runs:
        eligible, reason = False, f"{version} 에 기록된 테스트 실행이 없습니다"
    elif streak < required_green:
        eligible, reason = False, f"연속 green {required_green}회 필요 — 현재 {streak}회"
    elif not health_ok:
        eligible, reason = False, "마지막 실행의 헬스가 ok 가 아닙니다"
    else:
        eligible, reason = True, f"연속 green {streak}회 + 헬스 ok"
    return {
        "version": version,
        "eligible": eligible,
        "green_streak": streak,
        "required_green": required_green,
        "health_ok": health_ok,
        "total_runs": len(runs),
        "reason": reason,
    }


def compute_promoted_manifest(edge):
    """edge 매니페스트 -> stable 매니페스트 (track 만 stable 로 전환)."""
    promoted = dict(edge)
    promoted["track"] = "stable"
    promoted["notes"] = (
        "Stable (consumer) channel. Updated only by scripts/release_channel.py "
        "promote after the test gate passes."
    )
    return promoted


def repoint_site_text(text, version, repo=DEFAULT_REPO):
    """site-config.js 의 githubReleases 태그를 v{version} 으로 교체한 문자열 반환."""
    return re.sub(
        r"(githubReleases:\s*')[^']*(')",
        rf"\1https://github.com/{repo}/releases/tag/v{version}\2",
        text,
    )


# --------------------------------------------------------------------------- #
# 부수효과 헬퍼 (오케스트레이션)
# --------------------------------------------------------------------------- #
def _write_json(path, data):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _run(cmd, dry=False):
    print("+", " ".join(cmd))
    if dry:
        return
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _git_dirty():
    out = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(ROOT), capture_output=True, text=True
    ).stdout.strip()
    return out


# --------------------------------------------------------------------------- #
# CLI 핸들러
# --------------------------------------------------------------------------- #
def cmd_record(args):
    ledger = load_ledger()
    ledger = record_result(
        ledger, args.version, args.result, health=args.health, note=args.note or ""
    )
    _write_json(LEDGER, ledger)
    elig = promotion_eligibility(ledger, args.version, args.required)
    print(json.dumps(elig, ensure_ascii=False, indent=2))


def cmd_status(args):
    ledger = load_ledger()
    elig = promotion_eligibility(ledger, args.version, args.required)
    print(json.dumps(elig, ensure_ascii=False, indent=2))
    sys.exit(0 if elig["eligible"] else 1)


def cmd_promote(args):
    ledger = load_ledger()
    elig = promotion_eligibility(ledger, args.version, args.required)
    print(json.dumps(elig, ensure_ascii=False, indent=2))

    # 자동 게이트
    if not elig["eligible"]:
        sys.exit(f"승격 차단(자동 게이트): {elig['reason']}")
    # 수동 승인
    if not args.confirm:
        sys.exit("승격 차단(수동 승인): 게이트는 통과했으나 --confirm 이 필요합니다.")
    # edge 가 그 버전인지 확인
    edge = read_json(EDGE)
    if not edge or edge.get("version") != args.version:
        got = edge.get("version") if edge else None
        sys.exit(f"edge.json 버전 불일치: 기대 {args.version}, 실제 {got}")
    # 작업 트리 청결 가드 (동시 WIP 가 배포에 딸려가지 않도록)
    if not args.allow_dirty:
        dirty = _git_dirty()
        if dirty:
            sys.exit(
                "작업 트리에 미커밋 변경이 있어 승격을 중단합니다(배포 드리프트 방지).\n"
                "커밋 후 재시도하거나, 의도한 것이면 --allow-dirty 를 주세요.\n" + dirty
            )

    # 1) GitHub 릴리스를 latest 로 전환 (prerelease 해제)
    if not args.no_gh:
        _run(
            ["gh", "release", "edit", f"v{args.version}", "--repo", args.repo,
             "--prerelease=false", "--latest"],
            dry=args.dry_run,
        )
    # 2) stable 스왑 (직전 stable 은 .prev 로 보존)
    if STABLE.exists():
        STABLE_PREV.write_text(STABLE.read_text(encoding="utf-8"), encoding="utf-8")
    promoted = compute_promoted_manifest(edge)
    if not args.dry_run:
        _write_json(STABLE, promoted)
        _write_json(LATEST, promoted)  # 사이트 폴백 호환
        # 3) 사이트 다운로드를 새 태그로 재지정
        SITE_CONFIG.write_text(
            repoint_site_text(SITE_CONFIG.read_text(encoding="utf-8"), args.version, args.repo),
            encoding="utf-8",
        )
    print(f"  stable.json/latest.json -> v{args.version}, site-config 재지정")
    # 4) 재배포 (deploy.sh 가 테스트->스왑->헬스->자동롤백)
    if not args.no_deploy:
        _run(["bash", "deploy/deploy.sh"], dry=args.dry_run)
    print(f"승격 완료: v{args.version} -> stable (롤백본: release/stable.json.prev)")


def cmd_rollback(args):
    if not STABLE_PREV.exists():
        sys.exit("롤백 불가: release/stable.json.prev 가 없습니다(직전 stable 미보존).")
    prev = read_json(STABLE_PREV)
    prev_version = prev.get("version") if prev else None
    print(f"직전 stable 로 롤백: -> v{prev_version}")
    if not args.confirm:
        sys.exit("롤백 차단(수동 승인): --confirm 이 필요합니다.")
    if not args.dry_run:
        _write_json(STABLE, prev)
        _write_json(LATEST, prev)
        if prev_version:
            SITE_CONFIG.write_text(
                repoint_site_text(SITE_CONFIG.read_text(encoding="utf-8"), prev_version, args.repo),
                encoding="utf-8",
            )
    # 되돌린 버전을 다시 prerelease 로 (선택)
    if not args.no_gh and prev_version and not args.dry_run:
        _run(["gh", "release", "edit", f"v{prev_version}", "--repo", args.repo, "--latest"],
             dry=args.dry_run)
    if not args.no_deploy:
        _run(["bash", "deploy/deploy.sh"], dry=args.dry_run)
    print(f"롤백 완료: stable -> v{prev_version}")


def build_parser():
    p = argparse.ArgumentParser(description="MCPWorld 릴리스 채널/승격 게이트")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("record", help="버전에 테스트 실행 결과 1건 기록")
    pr.add_argument("--version", required=True)
    pr.add_argument("--result", required=True, choices=["pass", "fail"])
    pr.add_argument("--health", default="ok", choices=["ok", "fail"])
    pr.add_argument("--note", default="")
    pr.add_argument("--required", type=int, default=DEFAULT_REQUIRED_GREEN)
    pr.set_defaults(func=cmd_record)

    ps = sub.add_parser("status", help="버전의 승격 적격 여부 출력")
    ps.add_argument("--version", required=True)
    ps.add_argument("--required", type=int, default=DEFAULT_REQUIRED_GREEN)
    ps.set_defaults(func=cmd_status)

    pp = sub.add_parser("promote", help="게이트+수동승인 통과 시 edge->stable 승격")
    pp.add_argument("--version", required=True)
    pp.add_argument("--required", type=int, default=DEFAULT_REQUIRED_GREEN)
    pp.add_argument("--confirm", action="store_true", help="수동 승인(필수)")
    pp.add_argument("--repo", default=DEFAULT_REPO)
    pp.add_argument("--allow-dirty", action="store_true", help="미커밋 변경이 있어도 진행")
    pp.add_argument("--no-gh", action="store_true", help="gh release edit 생략")
    pp.add_argument("--no-deploy", action="store_true", help="deploy.sh 생략")
    pp.add_argument("--dry-run", action="store_true", help="파일/명령 변경 없이 미리보기")
    pp.set_defaults(func=cmd_promote)

    pb = sub.add_parser("rollback", help="직전 stable(.prev)로 롤백")
    pb.add_argument("--confirm", action="store_true")
    pb.add_argument("--repo", default=DEFAULT_REPO)
    pb.add_argument("--no-gh", action="store_true")
    pb.add_argument("--no-deploy", action="store_true")
    pb.add_argument("--dry-run", action="store_true")
    pb.set_defaults(func=cmd_rollback)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
