"""MCPWorld Agent — 소비자용 데스크톱 GUI (tkinter).

mcpworld.pyw(관리자 컨트롤러) 스타일의 가벼운 소비자 창. 추가 의존성 없음(tkinter는
표준 라이브러리). 이미 검증된 mcpworld_agent.py 의 함수(등록/폴링/토큰/딥링크/업데이트)를
그대로 감싼다.

연결 경로:
  1) 대시보드 '이 PC 연결' 클릭 -> OS가 'mcpworld-agent-gui.exe "mcpworld://connect?..."'
     실행 -> 이 GUI가 argv 파싱 -> 자격 저장 -> 자동 연결.
  2) GUI의 '토큰 붙여넣기 + 연결'(딥링크가 안 되는 환경의 폴백).

실행: pythonw agent/mcpworld_agent_gui.py  (또는 빌드된 windowed exe)
"""
import socket
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import ttk, scrolledtext

import mcpworld_agent as agent

POLL_INTERVAL_SECONDS = 5
UPDATE_CHECK_SECONDS = 3600


# --------------------------------------------------------------------------- #
# 순수 헬퍼 (단위 테스트 대상 — GUI/네트워크 없이 검증 가능)
# --------------------------------------------------------------------------- #
def mcp_reachable(port, host="127.0.0.1", timeout=0.3):
    """로컬 MCP 포트가 열려 있는지(연결되는지). 디스플레이/외부 의존 없음."""
    if not port:
        return False
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def status_text(connected, agent_id=None):
    if connected:
        return f"연결됨 · 폴링 중 ({agent_id})" if agent_id else "연결됨 · 폴링 중"
    return "연결 안 됨"


def dashboard_url(server):
    return f"{(server or agent.DEFAULT_SERVER).rstrip('/')}/dashboard.html"


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #
class AgentGUI:
    def __init__(self, root, connect_link=None):
        self.root = root
        self.creds = agent.load_agent_creds()
        if connect_link:
            link = agent.parse_connect_url(connect_link)
            if link.get("token"):
                self.creds = agent.save_agent_creds(link)
        self.server = self.creds.get("server") or agent.DEFAULT_SERVER
        self.token = self.creds.get("token") or ""
        self.agent_id = self.creds.get("agentId") or ""
        self.config = agent.load_local_mcp_config()
        self.mcp_lights = {}
        self._poll_thread = None
        self._stop = threading.Event()
        self._connected = False
        self._build()
        self._refresh_lights()
        if self.token:
            self.start_polling()
        root.protocol("WM_DELETE_WINDOW", self._quit)

    # ---- UI 구성 ----
    def _build(self):
        r = self.root
        r.title(f"MCPWorld Agent  v{agent.AGENT_VERSION}")
        r.minsize(560, 520)

        head = ttk.Frame(r)
        head.pack(fill="x", padx=12, pady=(10, 4))
        self.status_dot = tk.Label(head, text="●", fg="gray", font=("", 14, "bold"))
        self.status_dot.pack(side="left")
        self.status_label = tk.Label(head, text=status_text(False), font=("", 11, "bold"))
        self.status_label.pack(side="left", padx=6)

        conn = ttk.LabelFrame(r, text="연결")
        conn.pack(fill="x", padx=12, pady=6)
        ttk.Button(conn, text="이 PC 연결 (대시보드 열기)", command=self._open_dashboard).grid(
            row=0, column=0, padx=8, pady=8, sticky="w")
        ttk.Label(conn, text="토큰:").grid(row=1, column=0, padx=8, sticky="w")
        self.token_entry = ttk.Entry(conn, width=52, show="•")
        self.token_entry.grid(row=1, column=1, padx=6, pady=(0, 8), sticky="we")
        ttk.Button(conn, text="연결", command=self._connect_from_entry).grid(row=1, column=2, padx=8)
        ttk.Button(conn, text="연결 해제", command=self._disconnect).grid(row=0, column=2, padx=8)
        conn.columnconfigure(1, weight=1)

        mcp = ttk.LabelFrame(r, text="로컬 MCP 서버")
        mcp.pack(fill="x", padx=12, pady=6)
        mcps = self.config.get("mcps") or {}
        if not mcps:
            tk.Label(mcp, text="~/.mcpworld/config.json 에 로컬 MCP가 없습니다.",
                     fg="#888").pack(anchor="w", padx=8, pady=6)
        for mid, item in mcps.items():
            row = ttk.Frame(mcp)
            row.pack(fill="x", padx=8, pady=2)
            dot = tk.Label(row, text="●", fg="gray", font=("", 10, "bold"))
            dot.pack(side="left")
            name = item.get("name") or mid
            port = item.get("local_port")
            tk.Label(row, text=f"{name}  (:{port})").pack(side="left", padx=6)
            self.mcp_lights[mid] = (dot, port)
        ttk.Button(mcp, text="🔄 새로고침", command=self._refresh_lights).pack(anchor="w", padx=8, pady=4)

        tk.Label(r, text="로그").pack(anchor="w", padx=12)
        bottom = ttk.Frame(r)
        bottom.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
        ttk.Button(bottom, text="업데이트 확인", command=self._check_update).pack(side="left")
        ttk.Button(bottom, text="최소화", command=r.iconify).pack(side="left", padx=6)
        ttk.Button(bottom, text="종료", command=self._quit).pack(side="right")

        self.logbox = scrolledtext.ScrolledText(r, height=12, font=("Consolas", 9))
        self.logbox.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self.logbox.tag_config("error", foreground="#c0392b", font=("Consolas", 9, "bold"))
        self.logbox.tag_config("warn", foreground="#d98a00")

    # ---- 스레드 안전 로그/상태 ----
    def _log(self, msg, tag=None):
        def append():
            stamp = time.strftime("%H:%M:%S")
            self.logbox.insert("end", f"[{stamp}] {msg}\n", tag or ())
            self.logbox.see("end")
        self.root.after(0, append)

    def _set_connected(self, connected):
        self._connected = connected

        def paint():
            self.status_dot.config(fg="#2ecc71" if connected else "gray")
            self.status_label.config(text=status_text(connected, self.agent_id))
        self.root.after(0, paint)

    # ---- 동작 ----
    def _open_dashboard(self):
        webbrowser.open(dashboard_url(self.server))
        self._log("대시보드를 열었습니다. 로그인 후 '이 PC 연결'을 누르거나 토큰을 복사해 붙여넣으세요.")

    def _connect_from_entry(self):
        token = self.token_entry.get().strip()
        if not token:
            self._log("토큰을 입력하세요.", "warn")
            return
        self.token = token
        self.agent_id = self.creds.get("agentId") or ""
        agent.save_agent_creds({"server": self.server, "token": token, "agentId": self.agent_id})
        self.token_entry.delete(0, "end")
        self.start_polling()

    def _disconnect(self):
        self._stop.set()
        self._set_connected(False)
        self._log("연결 해제됨(폴링 중지). 자격은 보존됩니다.")

    def start_polling(self):
        if self._poll_thread and self._poll_thread.is_alive():
            self._log("이미 폴링 중입니다.")
            return
        if not self.token:
            self._log("토큰이 없어 연결할 수 없습니다.", "warn")
            return
        self._stop.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        self.root.after(UPDATE_CHECK_SECONDS * 1000, self._periodic_update)

    def _poll_loop(self):
        auth = {"token": self.token}
        try:
            resp = agent.post_json(
                f"{self.server.rstrip('/')}/api/agent/register",
                {**auth, "deviceName": socket.gethostname(), "agentId": self.agent_id},
            )
            self.agent_id = resp.get("agentId") or self.agent_id
            agent.save_agent_creds({"server": self.server, "token": self.token, "agentId": self.agent_id})
            self._set_connected(True)
            self._log(f"등록 완료: {self.agent_id}")
        except Exception as exc:
            self._log(f"등록 실패: {exc}", "error")
            self._set_connected(False)
            return
        while not self._stop.is_set():
            try:
                call_resp = agent.post_json(
                    f"{self.server.rstrip('/')}/api/agent/poll",
                    {**auth, "agentId": self.agent_id},
                )
                call = call_resp.get("call")
                if call:
                    self._log(f"도구 호출: {call.get('toolName')}")
                    try:
                        result = agent.run_adapter(call["toolName"], call.get("arguments") or {}, self.config)
                        status, error = "done", None
                    except Exception as exc:
                        result, status, error = None, "error", str(exc)
                        self._log(f"  실행 오류: {exc}", "error")
                    agent.post_json(
                        f"{self.server.rstrip('/')}/api/agent/result",
                        {"callId": call["id"], "status": status, "result": result, "error": error},
                    )
                    self._log(f"  완료: {status}")
            except Exception as exc:
                self._log(f"폴링 오류: {exc}", "warn")
            self._stop.wait(POLL_INTERVAL_SECONDS)
        self._set_connected(False)

    def _refresh_lights(self):
        def worker():
            for mid, (dot, port) in self.mcp_lights.items():
                ok = mcp_reachable(port)
                self.root.after(0, lambda d=dot, o=ok: d.config(fg="#2ecc71" if o else "#c0392b"))
        threading.Thread(target=worker, daemon=True).start()

    def _check_update(self):
        def worker():
            try:
                decision = agent.check_for_update(self.server)
            except Exception as exc:
                self._log(f"업데이트 확인 실패: {exc}", "warn")
                return
            if decision.get("update_available"):
                self._log(f"새 버전 있음: {decision['current']} -> {decision['target']} "
                          f"(forced={decision['forced']})")
                self._log("적용하려면 인스톨러를 받거나 자동 업데이트를 켜세요.")
            else:
                self._log(f"최신입니다 ({decision['current']}).")
        threading.Thread(target=worker, daemon=True).start()

    def _periodic_update(self):
        if not self._stop.is_set():
            self._check_update()
            self.root.after(UPDATE_CHECK_SECONDS * 1000, self._periodic_update)

    def _quit(self):
        self._stop.set()
        self.root.destroy()


def main():
    connect_link = None
    if len(sys.argv) > 1 and sys.argv[1].startswith("mcpworld://"):
        connect_link = sys.argv[1]
    root = tk.Tk()
    AgentGUI(root, connect_link=connect_link)
    root.mainloop()


if __name__ == "__main__":
    main()
