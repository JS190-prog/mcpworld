"""MCP World — Blender / CAD / Photoshop MCP 서버 + SSH 역터널 통합 컨트롤러 (tkinter GUI).

각 MCP에 대해 (1) 로컬 서버/proxy 프로세스 (2) VPS 역터널을 한 창에서 시작/중지하고
상태등으로 모니터링한다. 설정은 config.json. 트레이는 pystray가 있으면 자동 활성화.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config.json"
LOG_DIR = BASE / "logs"
LOG_DIR.mkdir(exist_ok=True)

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

try:
    import pystray
    from PIL import Image as PILImage, ImageDraw
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False

try:
    import psutil
except Exception:
    psutil = None


# ── 단일 인스턴스 잠금 ───────────────────────────────────────────────────────
# 같은 GUI 가 중복 실행되지 않도록 고정 로컬 포트 bind 를 잠금으로 쓴다.
# 첫 인스턴스만 bind 에 성공하고, 두 번째는 실패 -> 알림 후 종료한다.
# 프로세스가 죽으면 OS 가 소켓을 회수하므로 stale lock 이 남지 않는다.
_SINGLE_INSTANCE_PORT = 49677
_single_instance_sock = None


def acquire_single_instance():
    """첫 인스턴스면 True, 이미 실행 중이면 False."""
    global _single_instance_sock
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", _SINGLE_INSTANCE_PORT))
        s.listen(1)
    except OSError:
        s.close()
        return False
    # 프로세스 수명 동안 참조 유지 — GC 로 닫히면 잠금이 풀린다.
    _single_instance_sock = s
    return True


def already_running_alert():
    """중복 실행 시 사용자에게 알림창을 띄운다(콘솔 없는 .pyw 대응)."""
    msg = ("MCP World가 이미 실행 중입니다.\n\n"
           "트레이 아이콘 또는 작업 표시줄에서 기존 창을 여세요.")
    try:
        import ctypes
        # MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND
        ctypes.windll.user32.MessageBoxW(0, msg, "MCP World", 0x40 | 0x10000)
    except Exception:
        try:
            tmp = tk.Tk()
            tmp.withdraw()
            messagebox.showinfo("MCP World", msg)
            tmp.destroy()
        except Exception:
            pass


def port_open(port, host="127.0.0.1", timeout=0.4):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def pid_on_port(port):
    try:
        out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True,
                             creationflags=CREATE_NO_WINDOW).stdout
    except Exception:
        return None
    for line in out.splitlines():
        if (":%d " % port) in line and "LISTENING" in line.upper():
            return line.split()[-1].strip()
    return None


def kill_pid(pid, tree=True):
    args = ["taskkill", "/F"] + (["/T"] if tree else []) + ["/PID", str(pid)]
    subprocess.run(args, capture_output=True, creationflags=CREATE_NO_WINDOW)


def ssh_tunnel_pids(vps_port):
    """vps_port 로 SSH 역터널(-R <vps_port>:...)을 하는 모든 ssh 프로세스 PID.
    GUI가 띄운 것이든 외부(CLI)에서 띄운 것이든 전부 찾는다."""
    pids = []
    if psutil is None:
        return pids
    needle = "-R %d:" % vps_port
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (p.info.get("name") or "").lower()
            if "ssh" not in name:
                continue
            cmdline = " ".join(p.info.get("cmdline") or [])
            if needle in cmdline:
                pids.append(p.pid)
        except Exception:
            continue
    return pids


class Mcp:
    def __init__(self, cfg, gctx, log):
        self.cfg = cfg
        self.g = gctx
        self.log = log
        self.server_proc = None
        self.tunnel_proc = None
        self.extras = cfg.get("extra_endpoints", [])
        self._eprocs = {e["id"]: {"server": None, "tunnel": None} for e in self.extras}

    @property
    def name(self):
        return self.cfg["name"]

    @property
    def local_port(self):
        return self.cfg["local_port"]

    @property
    def vps_port(self):
        return self.cfg["vps_port"]

    @property
    def public_url(self):
        return self.g["public_base"] + self.cfg["path"] + "mcp"

    def public_urls(self):
        out = [self.public_url]
        for e in self.extras:
            out.append(self.g["public_base"] + e["path"] + "mcp")
        return out

    def _logf(self, suffix):
        return open(LOG_DIR / ("%s-%s.log" % (self.cfg["id"], suffix)), "a",
                    encoding="utf-8", errors="replace")

    def needs_install(self):
        """install.check 경로가 없으면 설치 필요(True). install 정의가 없으면 False."""
        inst = self.cfg.get("install")
        if not inst or not inst.get("check"):
            return False
        return not os.path.exists(inst["check"])

    def _install(self):
        """install.steps를 순차 실행. 모든 단계 성공 + check 충족 시 True."""
        inst = self.cfg.get("install", {})
        steps = inst.get("steps", [])
        self.log("[%s] 자동 설치 시작 (%d단계)..." % (self.name, len(steps)))
        for i, step in enumerate(steps, 1):
            self.log("[%s] 설치 (%d/%d): %s" % (self.name, i, len(steps), " ".join(step)))
            try:
                r = subprocess.run(step, cwd=inst.get("cwd"), capture_output=True,
                                   text=True, encoding="utf-8", errors="replace",
                                   creationflags=CREATE_NO_WINDOW)
            except Exception as ex:
                self.log("[%s] 설치 오류: %s" % (self.name, ex), level="error")
                return False
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip()[-300:]
                self.log("[%s] 설치 단계 실패(rc=%d): %s" % (self.name, r.returncode, tail), level="error")
                return False
        ok = not self.needs_install()
        self.log("[%s] 설치 %s" % (self.name, "완료" if ok else "했으나 확인 실패"),
                 level=None if ok else "error")
        return ok

    def start(self):
        # 서버가 미설치 상태면(install 레시피의 check 기준) 먼저 자동 설치한다.
        if not port_open(self.local_port) and self.needs_install():
            if not self._install():
                self.log("[%s] 설치 실패 — 시작 중단" % self.name, level="error")
                return
        if port_open(self.local_port):
            self.log("[%s] 서버 이미 가동 (:%d)" % (self.name, self.local_port))
        else:
            self.log("[%s] 서버 시작..." % self.name)
            try:
                env = os.environ.copy()
                env.update(self.cfg.get("env", {}))  # config의 서버별 env 주입(예: HWP 자동 실행)
                self.server_proc = subprocess.Popen(
                    self.cfg["server"], cwd=self.cfg.get("cwd"), env=env,
                    stdout=self._logf("server"), stderr=subprocess.STDOUT,
                    creationflags=CREATE_NO_WINDOW)
            except Exception as e:
                self.log("[%s] 서버 시작 실패: %s" % (self.name, e))
                return
            for _ in range(40):
                if port_open(self.local_port):
                    break
                time.sleep(0.5)
            if port_open(self.local_port):
                self.log("[%s] 서버 OK (:%d)" % (self.name, self.local_port))
            else:
                self.log("[%s] 서버 포트 미개방 — logs/%s-server.log 확인" % (self.name, self.cfg["id"]))
                return
        if self.tunnel_alive():
            self.log("[%s] 터널 이미 연결" % self.name)
        else:
            cmd = ["ssh"] + self.g["ssh_opts"] + \
                  ["-R", "%d:127.0.0.1:%d" % (self.vps_port, self.local_port), self.g["vps_ssh"]]
            self.log("[%s] 터널 %d->%d" % (self.name, self.vps_port, self.local_port))
            try:
                self.tunnel_proc = subprocess.Popen(
                    cmd, stdout=self._logf("tunnel"), stderr=subprocess.STDOUT,
                    creationflags=CREATE_NO_WINDOW)
            except Exception as e:
                self.log("[%s] 터널 실패: %s" % (self.name, e))
        for e in self.extras:
            self._start_extra(e)

    def _start_extra(self, e):
        eid, lp, vp = e["id"], e["local_port"], e["vps_port"]
        tag = "%s/%s" % (self.name, e.get("label", eid))
        rec = self._eprocs.setdefault(eid, {"server": None, "tunnel": None})
        if port_open(lp):
            self.log("[%s] 서버 이미 가동 (:%d)" % (tag, lp))
        else:
            self.log("[%s] 서버 시작..." % tag)
            try:
                rec["server"] = subprocess.Popen(
                    e["server"], cwd=e.get("cwd"),
                    stdout=self._logf("%s-server" % eid), stderr=subprocess.STDOUT,
                    creationflags=CREATE_NO_WINDOW)
            except Exception as ex:
                self.log("[%s] 서버 실패: %s" % (tag, ex))
                return
            for _ in range(40):
                if port_open(lp):
                    break
                time.sleep(0.5)
            if not port_open(lp):
                self.log("[%s] 서버 포트 미개방" % tag)
                return
            self.log("[%s] 서버 OK (:%d)" % (tag, lp))
        if ssh_tunnel_pids(vp):
            self.log("[%s] 터널 이미 연결" % tag)
        else:
            cmd = ["ssh"] + self.g["ssh_opts"] + ["-R", "%d:127.0.0.1:%d" % (vp, lp), self.g["vps_ssh"]]
            self.log("[%s] 터널 %d->%d" % (tag, vp, lp))
            try:
                rec["tunnel"] = subprocess.Popen(
                    cmd, stdout=self._logf("%s-tunnel" % eid), stderr=subprocess.STDOUT,
                    creationflags=CREATE_NO_WINDOW)
            except Exception as ex:
                self.log("[%s] 터널 실패: %s" % (tag, ex))

    def _stop_extra(self, e):
        eid, lp, vp = e["id"], e["local_port"], e["vps_port"]
        tag = "%s/%s" % (self.name, e.get("label", eid))
        for pid in ssh_tunnel_pids(vp):
            kill_pid(pid, tree=False)
        rec = self._eprocs.get(eid, {})
        if rec.get("tunnel") and rec["tunnel"].poll() is None:
            kill_pid(rec["tunnel"].pid, tree=False)
        if rec.get("server") and rec["server"].poll() is None:
            kill_pid(rec["server"].pid)
        pid = pid_on_port(lp)
        if pid:
            kill_pid(pid)
        self._eprocs[eid] = {"server": None, "tunnel": None}
        self.log("[%s] 중지" % tag)

    def stop(self):
        for e in self.extras:
            self._stop_extra(e)
        # 1) 터널: GUI가 띄운 것 + 외부(vps_port 로 -R 하는 모든 ssh)
        ext = ssh_tunnel_pids(self.vps_port)
        for pid in ext:
            kill_pid(pid, tree=False)
        if self.tunnel_proc and self.tunnel_proc.poll() is None:
            kill_pid(self.tunnel_proc.pid, tree=False)
        self.tunnel_proc = None
        # 2) 서버: GUI Popen + 외부(로컬 포트 점유 프로세스)
        if self.server_proc and self.server_proc.poll() is None:
            kill_pid(self.server_proc.pid)
        self.server_proc = None
        pid = pid_on_port(self.local_port)
        if pid:
            kill_pid(pid)
        extra = (" (외부 터널 %d개 포함)" % len(ext)) if ext else ""
        self.log("[%s] 중지 — 서버+터널%s" % (self.name, extra))

    def tunnel_alive(self):
        # 외부에서 띄운 터널도 초록으로 감지 (psutil 있을 때)
        if ssh_tunnel_pids(self.vps_port):
            return True
        return self.tunnel_proc is not None and self.tunnel_proc.poll() is None

    def server_up(self):
        return port_open(self.local_port)

    def _server_states(self):
        return [port_open(self.local_port)] + [port_open(e["local_port"]) for e in self.extras]

    def _tunnel_states(self):
        main = bool(ssh_tunnel_pids(self.vps_port)) or (
            self.tunnel_proc is not None and self.tunnel_proc.poll() is None)
        return [main] + [bool(ssh_tunnel_pids(e["vps_port"])) for e in self.extras]


class App:
    def __init__(self, root):
        self.root = root
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        self.g = cfg
        self.mcps = [Mcp(m, cfg, self.log) for m in cfg["mcps"]]
        self.rows = {}
        self._tray = None
        self._stop_poll = False
        self._build()
        self._ensure_blender_patch()
        threading.Thread(target=self._poll, daemon=True).start()
        if HAS_TRAY:
            self._setup_tray()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build(self):
        r = self.root
        r.title("MCP World — Blender / CAD / Photoshop / HWP / Office")
        r.geometry("660x600")
        r.minsize(560, 480)

        top = ttk.Frame(r)
        top.pack(fill="x", padx=10, pady=8)
        ttk.Button(top, text="▶ 전체 시작", command=lambda: self._all("start")).pack(side="left")
        ttk.Button(top, text="■ 전체 중지", command=lambda: self._all("stop")).pack(side="left", padx=6)
        ttk.Button(top, text="🔄 새로고침", command=self._update_lights).pack(side="left")
        ttk.Button(top, text="⚙ 설정", command=self._open_settings).pack(side="left", padx=6)

        for m in self.mcps:
            fr = ttk.LabelFrame(r, text=m.name)
            fr.pack(fill="x", padx=10, pady=4)
            srv = tk.Label(fr, text="● 서버", fg="gray", font=("", 10, "bold"))
            srv.grid(row=0, column=0, padx=8, pady=6)
            tun = tk.Label(fr, text="● 터널", fg="gray", font=("", 10, "bold"))
            tun.grid(row=0, column=1, padx=8)
            tk.Label(fr, text=":%d → %d   %s" % (m.local_port, m.vps_port, m.cfg["path"])).grid(
                row=0, column=2, padx=8)
            ttk.Button(fr, text="시작", width=6, command=lambda x=m: self._one(x, "start")).grid(
                row=0, column=3, padx=3)
            ttk.Button(fr, text="중지", width=6, command=lambda x=m: self._one(x, "stop")).grid(
                row=0, column=4, padx=3)
            ttk.Button(fr, text="📋 URL", width=8, command=lambda x=m: self._copy(x)).grid(
                row=0, column=5, padx=3)
            tk.Label(fr, text="앱: " + m.cfg.get("app_hint", ""), fg="#888", font=("", 8),
                     wraplength=560, justify="left").grid(
                row=1, column=0, columnspan=6, sticky="w", padx=8, pady=(0, 4))
            self.rows[m.cfg["id"]] = (srv, tun)

        base = self.g.get("public_base", "https://YOUR_DOMAIN")
        paths = ",".join(m.cfg["path"].strip("/") for m in self.mcps)
        info = tk.Label(
            r, fg="#555", justify="left", wraplength=640,
            text="공개 URL: %s/{%s}/mcp  (ChatGPT 개발자모드 · 인증=없음)\n"
                 "도구 변경 시 ChatGPT 커넥터를 삭제 후 재추가해야 새 도구가 보입니다." % (base, paths))
        info.pack(anchor="w", padx=10, pady=(4, 2))

        tk.Label(r, text="로그").pack(anchor="w", padx=10)
        self.logbox = scrolledtext.ScrolledText(r, height=12, font=("Consolas", 9))
        self.logbox.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.logbox.tag_config("error", foreground="#c0392b", font=("Consolas", 9, "bold"))
        self.logbox.tag_config("warn", foreground="#d98a00")

        bottom = ttk.Frame(r)
        bottom.pack(fill="x", padx=10, pady=(0, 8))
        if HAS_TRAY:
            ttk.Button(bottom, text="트레이로 최소화", command=self._hide).pack(side="left")
        ttk.Button(bottom, text="종료(서버는 유지)", command=self._quit).pack(side="right")

    def log(self, msg, level=None):
        ts = time.strftime("%H:%M:%S")

        def _():
            if level:
                self.logbox.insert("end", "%s %s\n" % (ts, msg), level)
            else:
                self.logbox.insert("end", "%s %s\n" % (ts, msg))
            self.logbox.see("end")
        try:
            self.root.after(0, _)
        except Exception:
            pass

    def _one(self, m, action):
        if action == "start" and m.needs_install():
            if not messagebox.askyesno(
                    "자동 설치",
                    "[%s] 서버가 설치되어 있지 않습니다.\n지금 설치 후 시작할까요?\n"
                    "(GitHub clone·패키지 설치 등 네트워크/디스크 작업이 진행됩니다)" % m.name):
                self.log("[%s] 설치 취소됨" % m.name)
                return
        threading.Thread(target=(m.start if action == "start" else m.stop), daemon=True).start()

    def _all(self, action):
        if action == "start":
            need = [m for m in self.mcps if m.needs_install()]
            if need:
                names = "\n".join("· " + m.name for m in need)
                if not messagebox.askyesno(
                        "자동 설치",
                        "다음 서버가 설치되어 있지 않습니다:\n%s\n\n지금 설치 후 전체 시작할까요?" % names):
                    return
        def run():
            # 각 MCP를 병렬로 시작/중지한다. 과거엔 순차 실행이라 서버마다
            # 포트 대기(최대 수십 초)가 누적돼 전체 시작이 hang 처럼 보였다.
            fn = Mcp.start if action == "start" else Mcp.stop
            threads = [threading.Thread(target=fn, args=(m,), daemon=True)
                       for m in self.mcps]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        threading.Thread(target=run, daemon=True).start()

    def _copy(self, m):
        urls = m.public_urls()
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(urls))
        if len(urls) > 1:
            self.log("[%s] URL %d개 복사 (줄바꿈 분리):" % (m.name, len(urls)))
            for u in urls:
                self.log("    " + u)
        else:
            self.log("[%s] URL 복사: %s" % (m.name, urls[0]))

    def _compute_lights(self):
        """상태등 색상 계산. port_open(블로킹 소켓) + psutil 스캔을 포함하므로
        반드시 백그라운드 스레드에서만 호출한다(메인 UI 스레드 금지 — hang 원인)."""
        GREEN, ORANGE, GRAY = "#19a319", "#d98a00", "gray"
        colors = {}
        for m in self.mcps:
            try:
                ss = m._server_states()
                ts = m._tunnel_states()
                colors[m.cfg["id"]] = (
                    GREEN if all(ss) else (ORANGE if any(ss) else GRAY),
                    GREEN if all(ts) else (ORANGE if any(ts) else GRAY),
                )
            except Exception:
                pass
        return colors

    def _apply_lights(self, colors):
        """계산된 색상을 위젯에 적용. 메인 스레드에서만 호출(빠름, 비블로킹)."""
        for mid, (srv_c, tun_c) in colors.items():
            row = self.rows.get(mid)
            if row:
                row[0].config(fg=srv_c)
                row[1].config(fg=tun_c)

    def _open_settings(self):
        """현재 config.json의 모든 설정을 편집하는 창(저장 시 MCP World 재시작 후 적용)."""
        try:
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception as e:
            messagebox.showerror("설정", "config.json 읽기 실패: %s" % e)
            return

        win = tk.Toplevel(self.root)
        win.title("MCP World 설정 — config.json")
        win.geometry("780x640")
        win.transient(self.root)

        canvas = tk.Canvas(win, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        bodyf = ttk.Frame(canvas)
        bodyf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=bodyf, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)

        vars_global = {}
        gfr = ttk.LabelFrame(bodyf, text="전역 설정")
        gfr.pack(fill="x", padx=10, pady=6)
        for i, (key, label) in enumerate([("vps_ssh", "VPS SSH"), ("public_base", "Public Base URL")]):
            ttk.Label(gfr, text=label, width=18).grid(row=i, column=0, sticky="w", padx=6, pady=3)
            v = tk.StringVar(value=str(cfg.get(key, "")))
            ttk.Entry(gfr, textvariable=v, width=82).grid(row=i, column=1, sticky="w", padx=6, pady=3)
            vars_global[key] = v

        vars_mcp = []
        for m in cfg.get("mcps", []):
            mf = ttk.LabelFrame(bodyf, text="MCP: %s  (id=%s)" % (m.get("name", ""), m.get("id", "")))
            mf.pack(fill="x", padx=10, pady=6)
            w = {}
            rows = [("name", "이름"), ("local_port", "로컬 포트"), ("vps_port", "VPS 포트"),
                    ("path", "경로(path)"), ("cwd", "작업폴더(cwd)"), ("app_hint", "앱 힌트")]
            for i, (key, label) in enumerate(rows):
                ttk.Label(mf, text=label, width=18).grid(row=i, column=0, sticky="w", padx=6, pady=2)
                v = tk.StringVar(value=str(m.get(key, "")))
                ttk.Entry(mf, textvariable=v, width=82).grid(row=i, column=1, sticky="w", padx=6, pady=2)
                w[key] = v
            r0 = len(rows)
            ttk.Label(mf, text="환경변수(KEY=VALUE)", width=18).grid(row=r0, column=0, sticky="nw", padx=6, pady=2)
            envt = tk.Text(mf, width=82, height=2)
            envt.insert("1.0", "\n".join("%s=%s" % (k, val) for k, val in m.get("env", {}).items()))
            envt.grid(row=r0, column=1, sticky="w", padx=6, pady=2)
            w["_env"] = envt
            ttk.Label(mf, text="서버 명령(한 줄=인자)", width=18).grid(row=r0 + 1, column=0, sticky="nw", padx=6, pady=2)
            srvt = tk.Text(mf, width=82, height=4)
            srvt.insert("1.0", "\n".join(m.get("server", [])))
            srvt.grid(row=r0 + 1, column=1, sticky="w", padx=6, pady=2)
            w["_server"] = srvt
            vars_mcp.append((m, w))

        def do_save():
            try:
                for key, var in vars_global.items():
                    cfg[key] = var.get().strip()
                for mcfg, w in vars_mcp:
                    for key in ("name", "path", "cwd", "app_hint"):
                        mcfg[key] = w[key].get().strip()
                    for key in ("local_port", "vps_port"):
                        mcfg[key] = int(w[key].get().strip())
                    env = {}
                    for ln in w["_env"].get("1.0", "end").splitlines():
                        ln = ln.strip()
                        if ln and "=" in ln:
                            k, val = ln.split("=", 1)
                            env[k.strip()] = val.strip()
                    if env:
                        mcfg["env"] = env
                    elif "env" in mcfg:
                        del mcfg["env"]
                    mcfg["server"] = [s.strip() for s in w["_server"].get("1.0", "end").splitlines() if s.strip()]
                text = json.dumps(cfg, ensure_ascii=False, indent=2)
                json.loads(text)  # 검증
                CONFIG.write_text(text, encoding="utf-8")
            except ValueError:
                messagebox.showerror("설정 저장 실패", "로컬/VPS 포트는 숫자여야 합니다.")
                return
            except Exception as e:
                messagebox.showerror("설정 저장 실패", str(e))
                return
            messagebox.showinfo("설정", "저장되었습니다.\nMCP World를 재시작하면 적용됩니다.")
            win.destroy()

        btnfr = ttk.Frame(win)
        btnfr.pack(side="bottom", fill="x", pady=6)
        ttk.Button(btnfr, text="저장", command=do_save).pack(side="right", padx=10)
        ttk.Button(btnfr, text="취소", command=win.destroy).pack(side="right")
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def _update_lights(self):
        """새로고침 버튼용. 계산을 백그라운드로 돌려 UI 블로킹을 막는다."""
        def work():
            colors = self._compute_lights()
            try:
                self.root.after(0, self._apply_lights, colors)
            except Exception:
                pass
        threading.Thread(target=work, daemon=True).start()

    def _poll(self):
        while not self._stop_poll:
            # 블로킹 계산은 이 백그라운드 스레드에서 직접 수행하고,
            # 메인 스레드에는 색상 적용(_apply_lights)만 예약한다.
            colors = self._compute_lights()
            try:
                self.root.after(0, self._apply_lights, colors)
            except Exception:
                break
            time.sleep(2)

    def _ensure_blender_patch(self):
        """MCP World 가동 시 BlenderMCP addon.py 의 render_scene 패치를 보장(멱등).

        BlenderMCP 업데이트로 addon.py 가 덮어써지면 'Unknown command type:
        render_scene' 가 재발한다. MCP World 는 워크플로상 Blender 보다 먼저 켜지므로,
        여기서 패치를 보장해 두면 이후 실행되는 Blender 가 패치본을 로드한다.
        멱등이라 이미 패치돼 있으면 아무것도 바꾸지 않는다."""
        def run():
            try:
                script = BASE / "repatch_blendermcp.py"
                if not script.exists():
                    self.log("[경고] BlenderMCP 재패처 파일 없음: %s" % script, level="warn")
                    return
                proc = subprocess.run([sys.executable, str(script)],
                                      capture_output=True, text=True,
                                      creationflags=CREATE_NO_WINDOW)
                out = (proc.stdout or "") + (proc.stderr or "")
                lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
                failed = proc.returncode != 0 or any(
                    ("FAIL" in ln or "ERROR" in ln) for ln in lines)
                if failed:
                    self.log("[실패] BlenderMCP render_scene 패치 복구 실패 "
                             "— render_image 도구가 동작하지 않을 수 있음", level="error")
                    for ln in lines:
                        self.log("    " + ln, level="error")
                    self.log("    ↳ 해결: logs는 repatch_blendermcp.log 확인 · "
                             "repatch_blendermcp.ps1 수동 실행 · "
                             "큰 씬은 blender_fast_render.py 로 렌더", level="error")
                else:
                    for ln in lines:
                        self.log(ln)
            except Exception as e:
                self.log("[실패] repatch 실행 오류: %s" % e, level="error")
        threading.Thread(target=run, daemon=True).start()

    def _setup_tray(self):
        img = PILImage.new("RGB", (64, 64), "#222")
        d = ImageDraw.Draw(img)
        d.ellipse((12, 12, 52, 52), fill="#19a319")
        menu = pystray.Menu(
            pystray.MenuItem("열기", self._show, default=True),
            pystray.MenuItem("전체 시작", lambda *a: self._all("start")),
            pystray.MenuItem("전체 중지", lambda *a: self._all("stop")),
            pystray.MenuItem("종료", self._quit),
        )
        self._tray = pystray.Icon("mcpworld", img, "MCP World", menu)
        threading.Thread(target=self._tray.run, daemon=True).start()

    def _hide(self):
        self.root.withdraw()

    def _show(self, *a):
        self.root.after(0, self.root.deiconify)

    def _on_close(self):
        if HAS_TRAY:
            self._hide()
            self.log("트레이로 최소화 (트레이 아이콘 → 종료)")
        else:
            self._quit()

    def _quit(self, *a):
        self._stop_poll = True
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass


def main():
    # 중복 실행 차단: 이미 떠 있으면 알림만 띄우고 창을 열지 않는다.
    if not acquire_single_instance():
        already_running_alert()
        return
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
