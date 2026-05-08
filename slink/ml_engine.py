"""Multi-login engine for sli ml."""
import os
import re
import subprocess
import sys
import threading
from typing import Optional

# Platform-specific modules imported lazily in methods to avoid ImportError on Windows.


class Session:
    """Single SSH session."""

    def __init__(self, name: str, host_info: dict):
        self.name = name
        self.info = host_info
        self.proc: Optional[subprocess.Popen] = None
        self.blocked = False
        self.online = False
        self.last_cmd: Optional[str] = None
        self.in_raw_mode = False

    def connect(self):
        ssh_cmd = ["ssh", "-t", "-t", "-o", "StrictHostKeyChecking=accept-new"]
        user = self.info.get("username")
        host = self.info.get("hostname")
        port = self.info.get("port", 22)
        if not host:
            raise ValueError(f"Host '{self.name}' has no hostname.")
        target = f"{user}@{host}" if user else host
        if port != 22:
            ssh_cmd.extend(["-p", str(port)])
        ssh_cmd.append(target)
        self.proc = subprocess.Popen(
            ssh_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, bufsize=0,
        )
        self.online = True

    def send(self, data: bytes):
        if self.proc and self.proc.stdin and self.online:
            try:
                self.proc.stdin.write(data)
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError):
                self.online = False

    def disconnect(self):
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=2)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
            self.online = False
            self.proc = None


class MLEngine:
    """Manages multiple SSH sessions with broadcast/focus modes."""

    RAW_TRIGGERS = [
        re.compile(r"--\s*INSERT\s*--", re.I),
        re.compile(r"^\s*:\s*$"),
        re.compile(r"^\s*\[sudo\]", re.I),
        re.compile(r"^\s*Password:\s*$", re.I),
    ]
    DANGEROUS = [
        re.compile(r"rm\s+(-[rf]*\s+)+(/\S*)"),
        re.compile(r"\bdd\b"),
        re.compile(r"\bmkfs\."),
        re.compile(r"\breboot\b"),
        re.compile(r"\bshutdown\b"),
        re.compile(r"init\s+0"),
    ]

    def __init__(self, sessions: list[Session]):
        self.sessions = {s.name: s for s in sessions}
        self.mode = "broadcast"
        self.focused: Optional[str] = None
        self.running = False
        self._cmd_buffer = ""

    def run(self):
        self.running = True
        if sys.platform == "win32":
            self._run_windows()
        else:
            self._run_unix()

    # --- Unix path ---------------------------------------------------------
    def _run_unix(self):
        import select, termios, tty
        old = termios.tcgetattr(sys.stdin) if sys.stdin.isatty() else None
        try:
            if old:
                tty.setcbreak(sys.stdin.fileno())
            while self.running:
                fds = [sys.stdin] + [
                    s.proc.stdout for s in self.sessions.values()
                    if s.online and s.proc and s.proc.stdout
                ]
                readable, _, _ = select.select(fds, [], [], 0.05)
                for fd in readable:
                    if fd is sys.stdin:
                        self._handle_input(os.read(sys.stdin.fileno(), 4096))
                    else:
                        self._handle_fd(fd)
        finally:
            if old:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
            self._cleanup()

    # --- Windows path ------------------------------------------------------
    def _run_windows(self):
        import msvcrt
        stop = threading.Event()
        threads = [threading.Thread(target=self._win_stdin, args=(stop,), daemon=True)]
        for s in self.sessions.values():
            if s.online:
                threads.append(threading.Thread(target=self._win_stdout, args=(s, stop), daemon=True))
        for t in threads:
            t.start()
        try:
            while self.running and not stop.is_set():
                stop.wait(0.1)
        finally:
            stop.set()
            for t in threads:
                t.join(timeout=1)
            self._cleanup()

    def _win_stdin(self, stop: threading.Event):
        import msvcrt
        while self.running and not stop.is_set():
            if msvcrt.kbhit():
                self._handle_input(msvcrt.getch())
            stop.wait(0.01)

    def _win_stdout(self, session: Session, stop: threading.Event):
        while session.online and not stop.is_set():
            try:
                data = session.proc.stdout.read(1)
                if not data:
                    break
                self._display(session, data)
            except Exception:
                break
        session.online = False

    # --- I/O handling ------------------------------------------------------
    def _handle_fd(self, fd):
        for s in self.sessions.values():
            if s.online and s.proc and s.proc.stdout is fd:
                try:
                    data = os.read(fd.fileno(), 4096)
                    if not data:
                        s.online = False
                        continue
                    self._display(s, data)
                    if self._is_raw(data.decode("utf-8", "replace")):
                        s.in_raw_mode = True
                except (OSError, ValueError):
                    s.online = False
                break

    def _handle_input(self, data: bytes):
        text = data.decode("utf-8", errors="replace")
        # Accumulate command line
        if "\r" in text or "\n" in text:
            line = self._cmd_buffer + text.replace("\r", "").replace("\n", "")
            self._cmd_buffer = ""
            if line.startswith(">"):
                self._exec_cmd(line[1:].strip())
                return
            if line:
                self._dispatch(line.encode("utf-8"))
        else:
            self._cmd_buffer += text
            self._dispatch(data)

    def _dispatch(self, data: bytes):
        if self.mode == "focus" and self.focused:
            s = self.sessions.get(self.focused)
            if s and s.online and not s.blocked:
                s.send(data)
            return
        for s in self.sessions.values():
            if s.online and not s.blocked:
                s.send(data)

    def _display(self, session: Session, data: bytes):
        sys.stdout.buffer.write(f"[\u2190 {session.name}] ".encode() + data)
        sys.stdout.flush()

    def _is_raw(self, text: str) -> bool:
        return any(p.search(text) for p in self.RAW_TRIGGERS)

    def _check_dangerous(self, cmd: str) -> tuple:
        for p in self.DANGEROUS:
            if p.search(cmd):
                affected = sum(1 for s in self.sessions.values() if s.online and not s.blocked)
                return True, affected
        return False, 0

    def _cleanup(self):
        for s in self.sessions.values():
            s.disconnect()

    # --- Internal commands -------------------------------------------------
    def _exec_cmd(self, line: str):
        parts = line.split()
        if not parts:
            return
        cmd, args = parts[0], parts[1:]
        handler = getattr(self, f"cmd_{cmd}", None)
        if handler:
            handler(args)
        else:
            print(f"[ml] Unknown command: {cmd}")

    def cmd_block(self, args):
        targets = self.sessions if not args or args[0] == "all" else args
        for name in targets:
            s = self.sessions.get(name)
            if s:
                s.blocked = True
                print(f"[\u26a1 {name} blocked]")

    def cmd_unblock(self, args):
        targets = self.sessions if not args or args[0] == "all" else args
        for name in targets:
            s = self.sessions.get(name)
            if s:
                s.blocked = False
                print(f"[\u26a1 {name} resumed]")

    def cmd_focus(self, args):
        if args:
            self.focused = args[0]
            self.mode = "focus"
            print(f"[\u26a1 Focused on {args[0]}]")

    def cmd_broadcast(self, args):
        self.focused = None
        self.mode = "broadcast"
        print("[\u26a1 Broadcast mode]")

    def cmd_list(self, args):
        for name, s in self.sessions.items():
            st = "ONLINE" if s.online else "OFFLINE"
            blk = " [BLOCKED]" if s.blocked else ""
            print(f"  {name}: {st}{blk}")

    def cmd_status(self, args):
        for name, s in self.sessions.items():
            print(f"  {name}: last={s.last_cmd or 'N/A'} raw={s.in_raw_mode}")

    def cmd_save(self, args):
        if not args:
            print("[ml] Usage: >save <name>")
            return
        from .workspace import save_workspace, build_workspace
        data = build_workspace(
            args[0],
            list(self.sessions.keys()),
            [n for n, s in self.sessions.items() if s.blocked],
            self.focused,
            self.mode,
        )
        save_workspace(data, args[0])
        print(f"[\u26a1 Workspace '{args[0]}' saved]")

    def cmd_exit(self, args):
        print("[ml] Disconnecting all sessions...")
        self.running = False
