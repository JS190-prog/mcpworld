#!/usr/bin/env python3
"""
repatch_blendermcp.py — BlenderMCP addon.py 에 render_scene 핸들러를 멱등 재패치.

[왜 필요한가]
  BlenderMCP 를 업데이트/재설치하면 addon.py 가 덮어써지면서 render_scene 패치가
  사라져 "Unknown command type: render_scene" 가 재발한다. 이 스크립트는 설치된
  모든 Blender 버전의 BlenderMCP addon.py 를 검사해, 패치가 없으면 백업 후 자동으로
  다시 패치한다. 이미 패치돼 있으면 건드리지 않는다(멱등).

[안전장치]
  - 패치 전 타임스탬프 백업(addon.py.bak_YYYYmmdd_HHMMSS)
  - 패치 후 ast.parse 문법 검증 실패 시 -> 파일에 쓰지 않고 중단
  - 앵커(anchor)를 못 찾으면(미래 버전 구조 변경) 실패 보고 + 원본 보존

  수동 실행:  python repatch_blendermcp.py
  자동 실행:  repatch_blendermcp.ps1 (작업 스케줄러 로그온 트리거)

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


def log(msg):
    print(f"[repatch] {msg}")


def patch_file(path):
    """단일 addon.py 를 멱등 패치. 성공(또는 대상아님/이미패치)=True, 실패=False."""
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()

    # BlenderMCP 애드온이 아닌 동명 파일은 건너뜀
    if "BlenderMCPServer" not in src:
        log(f"SKIP (not BlenderMCP): {path}")
        return True

    # 멱등: 이미 패치돼 있으면 종료
    if "def render_scene(self" in src and '"render_scene": self.render_scene' in src:
        log(f"OK already patched: {path}")
        return True

    new = src
    changed = []

    # 1) handlers 딕셔너리 등록
    if '"render_scene": self.render_scene' not in new:
        if HANDLER_HOOK in new:
            new = new.replace(HANDLER_HOOK, HANDLER_HOOK + HANDLER_ADD, 1)
            changed.append("handler")
        else:
            log(f"FAIL anchor(handlers) not found -> manual patch needed: {path}")
            return False

    # 2) render_scene 메서드 정의
    if "def render_scene(self" not in new:
        if RAISE_HOOK in new:
            new = new.replace(RAISE_HOOK, RAISE_HOOK + METHOD_ADD, 1)
            changed.append("method")
        else:
            log(f"FAIL anchor(method) not found -> manual patch needed: {path}")
            return False

    # 3) 패치 결과 문법 검증 (실패 시 파일 손대지 않음)
    try:
        ast.parse(new)
    except SyntaxError as e:
        log(f"FAIL syntax after patch ({e}) -> aborted, file untouched: {path}")
        return False

    # 4) 백업 후 기록
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
