"""WebSocket PTY terminal — provides a browser-based terminal via xterm.js."""
import asyncio
import fcntl
import logging
import os
import pty
import signal
import struct
import termios

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger("vivify.terminal")
router = APIRouter()


class PTYProcess:
    """Manages a PTY fork for terminal sessions."""

    def __init__(self, shell_cmd: str | None = None):
        self.pid: int = -1
        self.master_fd: int = -1
        self._cmd = shell_cmd or (
            'TERM=xterm-256color tmux new -A -s web 2>/dev/null || bash'
        )

    def spawn(self):
        self.master_fd, slave_fd = pty.openpty()
        self.pid = os.fork()
        if self.pid == 0:
            os.close(self.master_fd)
            os.setsid()
            os.dup2(slave_fd, 0)
            os.dup2(slave_fd, 1)
            os.dup2(slave_fd, 2)
            if slave_fd > 2:
                os.close(slave_fd)
            os.execve("/bin/bash", ["/bin/bash", "-c", self._cmd], os.environ)
            os._exit(1)
        os.close(slave_fd)

    def read(self, nbytes: int = 4096) -> bytes:
        return os.read(self.master_fd, nbytes)

    def write(self, data: bytes):
        os.write(self.master_fd, data)

    def resize(self, rows: int, cols: int):
        buf = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, buf)

    def close(self):
        if self.pid > 0:
            try:
                os.kill(self.pid, signal.SIGTERM)
                os.waitpid(self.pid, 0)
            except ChildProcessError:
                pass
            self.pid = -1
        if self.master_fd > 0:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = -1


@router.websocket("/ws/terminal")
async def terminal_ws(websocket: WebSocket):
    await websocket.accept()
    p = PTYProcess()
    p.spawn()

    async def pty_to_ws():
        loop = asyncio.get_event_loop()
        try:
            while True:
                data = await loop.run_in_executor(None, p.read, 4096)
                if not data:
                    break
                await websocket.send_bytes(data)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    async def ws_to_pty():
        try:
            while True:
                raw = await websocket.receive()
                if raw.get("type") == "websocket.disconnect":
                    break
                if raw.get("type") == "websocket.receive":
                    msg = raw.get("text") or raw.get("bytes")
                    if msg is None:
                        continue
                    if isinstance(msg, str):
                        try:
                            import json
                            ctl = json.loads(msg)
                            if ctl.get("type") == "resize":
                                p.resize(ctl.get("rows", 24), ctl.get("cols", 80))
                                continue
                        except (json.JSONDecodeError, TypeError):
                            p.write(msg.encode())
                    else:
                        p.write(msg)
        except WebSocketDisconnect:
            pass
        except Exception:
            pass

    try:
        await asyncio.gather(pty_to_ws(), ws_to_pty())
    finally:
        p.close()
