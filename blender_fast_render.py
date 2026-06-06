"""
blender_fast_render.py — BlenderMCP 안전 렌더 표준 (render_image 도구 회피용)

[배경]
  - 설치된 BlenderMCP 애드온(addon.py v1.2)에는 render_scene 핸들러가 없어
    MCP의 render_image 도구가 "Unknown command type: render_scene" 로 실패한다.
  - 또한 render_image 는 동기(blocking)+base64 전송 구조라, 오브젝트가 많은
    큰 씬에서는 MCP 응답 타임아웃("Timeout waiting for response")이 난다.

[해결책 = 이 파일]
  - 항상 지원되는 execute_code 경로로 이 코드를 보내고 fast_render() 를 호출한다.
  - bpy.app.timers 기반 비동기 렌더라 소켓 호출이 "즉시" 반환 -> 타임아웃 구조적 불가.
  - 엔진은 현재 빌드에서 사용 가능한 식별자를 자동 선택한다
    (Blender 5.0 은 'BLENDER_EEVEE' 하나만 존재. 'BLENDER_EEVEE_NEXT' 는 없음).

[사용법] (MCP execute_blender_code 안에서)
  exec(open(r"C:\scratch\mcpworld\blender_fast_render.py", encoding="utf-8").read())
  fast_render(output_path=r"C:\tmp\office.png", resolution=(1200, 900), samples=16)
  # 잠시 후 완료 확인
  print(render_status(r"C:\tmp\office.png"))
"""

import bpy
import os


def _pick_eevee_engine():
    """현재 Blender 빌드에서 실제 사용 가능한 EEVEE 식별자를 고른다."""
    items = [e.identifier for e in
             bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    for cand in ('BLENDER_EEVEE', 'BLENDER_EEVEE_NEXT'):
        if cand in items:
            return cand
    return items[0] if items else 'BLENDER_EEVEE'


def fast_render(output_path=None, resolution=(1200, 900), samples=16,
                engine=None, percentage=100, async_render=True):
    """
    EEVEE 비동기 렌더. 호출 즉시 반환하고 렌더는 백그라운드(메인 루프)에서 진행한다.
    - output_path: 저장 경로(PNG). 미지정 시 .blend 폴더 또는 C:\\tmp 로.
    - resolution : (x, y) 픽셀.
    - samples    : EEVEE taa_render_samples (낮을수록 빠름).
    - async_render: True 면 타임아웃 회피용 비동기, False 면 동기(작은 씬용).
    """
    scene = bpy.context.scene

    scene.render.engine = engine or _pick_eevee_engine()
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.render.resolution_percentage = int(percentage)
    scene.render.image_settings.file_format = 'PNG'

    try:
        scene.eevee.taa_render_samples = int(samples)
    except Exception as e:
        print("eevee sample skip:", e)

    if not output_path:
        base = os.path.dirname(bpy.data.filepath) if bpy.data.filepath else r"C:\tmp"
        output_path = os.path.join(base, "mcp_fast_render.png")
    scene.render.filepath = output_path

    # 이전 산출물 제거(완료 폴링을 명확히 하기 위함)
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except Exception:
            pass

    def _do():
        try:
            bpy.ops.render.render(write_still=True)
            print("RENDER DONE ->", output_path)
        except Exception as e:
            print("RENDER ERROR:", e)
        return None  # 1회 실행 후 타이머 해제

    if async_render:
        bpy.app.timers.register(_do, first_interval=0.25)
        print("RENDER SCHEDULED ->", output_path,
              "| engine =", scene.render.engine,
              "| res =", scene.render.resolution_x, "x", scene.render.resolution_y,
              "| samples =", samples)
        return output_path

    _do()
    return output_path


def render_status(output_path):
    """렌더 완료 폴링. 파일 존재 + 크기로 판정(>1KB 면 정상 완료로 간주)."""
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        return {"path": output_path, "exists": True,
                "size_bytes": size, "ready": size > 1000}
    return {"path": output_path, "exists": False, "ready": False}
