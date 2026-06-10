#!/usr/bin/env python3
"""
repatch_blendermcp.py — BlenderMCP addon.py 에 render_scene + 비동기 Job 핸들러를 멱등 재패치.

[왜 필요한가]
  BlenderMCP 를 업데이트/재설치하면 addon.py 가 덮어써지면서 우리가 추가한 패치가
  사라진다. 이 스크립트는 설치된 모든 Blender 버전의 BlenderMCP addon.py 를 검사해,
  빠진 패치가 있으면 백업 후 자동으로 다시 패치한다. 이미 패치돼 있으면 건드리지
  않는다(멱등). 두 종류의 패치를 영구화한다:

  1) render_scene  — MCP render_image 도구 지원 복구
                     ("Unknown command type: render_scene" 방지).
  2) 비동기 Job    — execute_code_async / get_job_status / get_job_result / list_jobs.
                     긴 작업을 백그라운드 timer 로 돌리고 job_id 를 즉시 반환해
                     "Timeout waiting for response" 를 구조적으로 제거한다. 폴링 명령은
                     메인 스레드를 거치지 않고 클라이언트 스레드에서 즉답한다.

[안전장치]
  - 패치 전 타임스탬프 백업(addon.py.bak_YYYYmmdd_HHMMSS)
  - 패치 후 ast.parse 문법 검증 실패 시 -> 파일에 쓰지 않고 중단
  - 앵커(anchor)를 못 찾으면(미래 버전 구조 변경) 실패 보고 + 원본 보존
  - 각 패치는 독립 멱등 — render_scene 만 있고 async 가 없으면 async 만 보강

  수동 실행:  python repatch_blendermcp.py
  자동 실행:  repatch_blendermcp.ps1 (mcpworld GUI 시작 훅)

  종료 코드:  0 = 정상(패치 또는 이미 패치됨/대상 없음), 1 = 하나 이상 실패.
"""

import ast
import glob
import os
import shutil
import sys
from datetime import datetime

# 설치된 모든 Blender 버전의 addon.py
ADDON_GLOBS = [
    os.path.expandvars(r"%APPDATA%\Blender Foundation\Blender\*\scripts\addons\addon.py"),
]

# ---------------------------------------------------------------------------
# 패치 1: render_scene
# ---------------------------------------------------------------------------
# handlers 딕셔너리에 추가할 등록 라인 (앵커 = 마지막 base handler 라인)
HANDLER_HOOK = '            "get_hunyuan3d_status": self.get_hunyuan3d_status,'
HANDLER_ADD = '\n            "render_scene": self.render_scene,'

# render_scene 메서드 본문 (앵커 = execute_code 끝의 raise 라인; 안정적이고 유일)
RAISE_HOOK = '            raise Exception(f"Code execution error: {str(e)}")'
METHOD_ADD = '''

    def render_scene(self, output_path=None, filepath=None,
                     resolution_x=None, resolution_y=None,
                     engine=None, samples=None, **kwargs):
        """Render current scene to a file; restores MCP render_image support."""
        import os
        try:
            scene = bpy.context.scene
            path = output_path or filepath
            if not path:
                base = (os.path.dirname(bpy.data.filepath)
                        if bpy.data.filepath else bpy.app.tempdir)
                path = os.path.join(base, "mcp_render.png")
            if engine:
                valid = [e.identifier for e in
                         bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
                if engine in valid:
                    scene.render.engine = engine
            if resolution_x:
                scene.render.resolution_x = int(resolution_x)
            if resolution_y:
                scene.render.resolution_y = int(resolution_y)
            if samples is not None:
                try:
                    scene.eevee.taa_render_samples = int(samples)
                except Exception:
                    pass
            scene.render.image_settings.file_format = 'PNG'
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            return {"success": True, "rendered": True, "filepath": path,
                    "output_path": path, "width": scene.render.resolution_x,
                    "height": scene.render.resolution_y, "engine": scene.render.engine}
        except Exception as e:
            return {"error": str(e)}'''

# ---------------------------------------------------------------------------
# 패치 2: 비동기 Job 엔진
# ---------------------------------------------------------------------------
# 2a) __init__ 의 job 레지스트리 (앵커 = self.server_thread = None)
INIT_HOOK = '        self.server_thread = None'
INIT_ADD = '\n        self.jobs = {}  # async job registry: job_id -> state dict'

# 2b) handlers 등록 4개 (앵커 = 항상 존재하는 base handler "execute_code")
ASYNC_HANDLER_HOOK = '            "execute_code": self.execute_code,'
ASYNC_HANDLER_ADD = (
    '\n            "execute_code_async": self.execute_code_async,'
    '\n            "get_job_status": self.get_job_status,'
    '\n            "get_job_result": self.get_job_result,'
    '\n            "list_jobs": self.list_jobs,'
)

# 2c) 메서드 본문 (앵커 = get_polyhaven_categories 정의; render_scene 포맷과 무관하게 유일)
#     -> 앵커 "앞에" 삽입한다. raw 문자열로 둬서 f"...\n..." 의 \n 이 보존되게 한다.
ASYNC_METHOD_HOOK = '    def get_polyhaven_categories(self, asset_type):'
ASYNC_METHOD_ADD = r'''    def execute_code_async(self, code, job_id=None):
        """Run code in the background (main-loop timer) and return immediately.

        The socket call returns right away with a job_id, so the MCP
        request/response can never time out no matter how long the code runs.
        Poll get_job_status / get_job_result with the returned job_id. The
        executed code receives a JOB dict in its namespace and may update
        JOB["objects_created"] / JOB["stage"] for cooperative progress.
        """
        if not job_id:
            job_id = "job_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + os.urandom(3).hex()
        job = {
            "job_id": job_id,
            "status": "queued",
            "created": time.time(),
            "started": None,
            "finished": None,
            "stdout": "",
            "error": None,
            "object_count_start": len(bpy.context.scene.objects),
            "objects_created": 0,
            "stage": None,
            "result": None,
        }
        self.jobs[job_id] = job

        def _runner():
            job["status"] = "running"
            job["started"] = time.time()
            capture_buffer = io.StringIO()
            namespace = {"bpy": bpy, "JOB": job, "__name__": "__mcp_job__"}
            try:
                with redirect_stdout(capture_buffer):
                    exec(code, namespace)
                job["status"] = "done"
            except Exception as e:
                job["status"] = "failed"
                job["error"] = f"{e}\n{traceback.format_exc()}"
            finally:
                job["stdout"] = capture_buffer.getvalue()
                job["finished"] = time.time()
                try:
                    scene = bpy.context.scene
                    job["objects_created"] = len(scene.objects) - job["object_count_start"]
                    job["result"] = {
                        "object_count": len(scene.objects),
                        "objects_created": job["objects_created"],
                        "materials_count": len(bpy.data.materials),
                        "camera_exists": scene.camera is not None,
                        "saved_path": bpy.data.filepath or None,
                        "engine": scene.render.engine,
                    }
                except Exception as ve:
                    job["result"] = {"validation_error": str(ve)}
            return None  # one-shot timer

        bpy.app.timers.register(_runner, first_interval=0.05)
        return {"job_id": job_id, "status": "queued"}

    def _job_view(self, job):
        """Compact, poll-friendly view of a job (elapsed computed live)."""
        now = time.time()
        started = job.get("started")
        if started:
            elapsed = round((job.get("finished") or now) - started, 2)
        else:
            elapsed = 0.0
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "elapsed_sec": elapsed,
            "stage": job.get("stage"),
            "objects_created": job.get("objects_created", 0),
        }

    def get_job_status(self, job_id):
        """Return current status of an async job (safe to poll mid-run)."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": f"unknown job_id: {job_id}"}
        view = self._job_view(job)
        view["error"] = job.get("error")
        view["stdout_tail"] = (job.get("stdout") or "")[-1000:]
        return view

    def get_job_result(self, job_id):
        """Return the final result of an async job once it has finished."""
        job = self.jobs.get(job_id)
        if not job:
            return {"error": f"unknown job_id: {job_id}"}
        if job["status"] in ("queued", "running"):
            view = self._job_view(job)
            view["ready"] = False
            return view
        return {
            "job_id": job_id,
            "status": job["status"],
            "ready": True,
            "error": job.get("error"),
            "stdout": job.get("stdout", ""),
            "result": job.get("result"),
        }

    def list_jobs(self):
        """List all async jobs with a short status view."""
        return {"jobs": [self._job_view(j) for j in self.jobs.values()]}

'''

# 2d) _handle_client 폴링 우회 (앵커 = execute_wrapper 타이머 등록 라인을 분기로 교체)
POLL_HOOK = '                        bpy.app.timers.register(execute_wrapper, first_interval=0.0)'
POLL_BYPASS_ADD = (
    '                        # Poll-type commands only read the job registry (no\n'
    '                        # bpy access), so answer them on this client thread to\n'
    '                        # stay responsive while a long job blocks the main thread.\n'
    '                        if command.get("type") in ("get_job_status", "get_job_result", "list_jobs"):\n'
    '                            try:\n'
    '                                poll_response = self.execute_command(command)\n'
    "                                client.sendall(json.dumps(poll_response).encode('utf-8'))\n"
    '                            except Exception as poll_err:\n'
    '                                print(f"Poll command failed: {poll_err}")\n'
    '                        else:\n'
    '                            bpy.app.timers.register(execute_wrapper, first_interval=0.0)'
)


def log(msg):
    print(f"[repatch] {msg}")


def _fail(path, what):
    log(f"FAIL anchor({what}) not found -> manual patch needed: {path}")
    return False


def patch_file(path):
    """단일 addon.py 를 멱등 패치. 성공(또는 대상아님/이미패치)=True, 실패=False."""
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()

    # BlenderMCP 애드온이 아닌 동명 파일은 건너뜀
    if "BlenderMCPServer" not in src:
        log(f"SKIP (not BlenderMCP): {path}")
        return True

    new = src
    changed = []

    # --- 패치 1: render_scene (handler + method) ---
    if '"render_scene": self.render_scene' not in new:
        if HANDLER_HOOK in new:
            new = new.replace(HANDLER_HOOK, HANDLER_HOOK + HANDLER_ADD, 1)
            changed.append("render-handler")
        else:
            return _fail(path, "handlers/render_scene")
    if "def render_scene(self" not in new:
        if RAISE_HOOK in new:
            new = new.replace(RAISE_HOOK, RAISE_HOOK + METHOD_ADD, 1)
            changed.append("render-method")
        else:
            return _fail(path, "method/render_scene")

    # --- 패치 2: 비동기 Job (init + handlers + methods + poll bypass) ---
    if "self.jobs = {}" not in new:
        if INIT_HOOK in new:
            new = new.replace(INIT_HOOK, INIT_HOOK + INIT_ADD, 1)
            changed.append("jobs-init")
        else:
            return _fail(path, "init/jobs")
    if '"execute_code_async": self.execute_code_async' not in new:
        if ASYNC_HANDLER_HOOK in new:
            new = new.replace(ASYNC_HANDLER_HOOK, ASYNC_HANDLER_HOOK + ASYNC_HANDLER_ADD, 1)
            changed.append("async-handlers")
        else:
            return _fail(path, "handlers/async")
    if "def execute_code_async(self" not in new:
        if ASYNC_METHOD_HOOK in new:
            new = new.replace(ASYNC_METHOD_HOOK, ASYNC_METHOD_ADD + ASYNC_METHOD_HOOK, 1)
            changed.append("async-methods")
        else:
            return _fail(path, "method/async")
    if "poll_response = self.execute_command" not in new:
        if POLL_HOOK in new:
            new = new.replace(POLL_HOOK, POLL_BYPASS_ADD, 1)
            changed.append("poll-bypass")
        else:
            return _fail(path, "handle_client/poll-bypass")

    # 변경 없음 = 이미 모두 패치됨 (멱등)
    if not changed:
        log(f"OK already patched: {path}")
        return True

    # 패치 결과 문법 검증 (실패 시 파일 손대지 않음)
    try:
        ast.parse(new)
    except SyntaxError as e:
        log(f"FAIL syntax after patch ({e}) -> aborted, file untouched: {path}")
        return False

    # 백업 후 기록
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{path}.bak_{ts}"
    shutil.copy2(path, bak)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    log(f"PATCHED [{'+'.join(changed)}] (backup: {os.path.basename(bak)}): {path}")
    return True


def main():
    targets = []
    for g in ADDON_GLOBS:
        targets.extend(glob.glob(g))
    targets = sorted(set(targets))

    if not targets:
        log("no addon.py found under %APPDATA%\\Blender Foundation")
        return 0

    ok = True
    for p in targets:
        try:
            ok = patch_file(p) and ok
        except Exception as e:
            log(f"ERROR {p}: {e}")
            ok = False
    log("done." if ok else "done WITH FAILURES.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
