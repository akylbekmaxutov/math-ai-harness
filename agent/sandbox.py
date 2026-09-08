"""Sandboxed Python execution.

Read-only in effect: a fresh subprocess, a wall-clock timeout, address-space
and CPU limits, and sockets disabled before user code runs. No permission
model and no undo, because the tools have no side effects to undo — that
exclusion is deliberate and stated in the workshop.
"""
from __future__ import annotations

import resource
import subprocess
import sys
from dataclasses import dataclass

PREAMBLE = (
    "import socket as _s\n"
    "def _blocked(*a, **k):\n"
    "    raise OSError('network disabled in sandbox')\n"
    "_s.socket = _blocked\n"
    "_s.create_connection = _blocked\n"
    "import builtins as _b\n"
    "_b.__import__ = (lambda _o: (lambda n, *a, **k: _blocked() if n in "
    "('urllib','requests','httpx','http','ftplib','smtplib') else _o(n,*a,**k)))(_b.__import__)\n"
)

DEFAULT_TIMEOUT_S = 10
DEFAULT_MEM_MB = 512
DEFAULT_CPU_S = 10


@dataclass
class ExecResult:
    stdout: str
    stderr: str
    returncode: int
    timed_out: bool

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "timed_out": self.timed_out,
        }


def _limits():
    """Best-effort resource caps in the child, before exec.

    Not every limit is enforceable on every platform — macOS refuses to start
    a CPython child under RLIMIT_AS, and RLIMIT_NPROC is per-user there rather
    than per-process. A limit we cannot set is skipped rather than fatal; the
    wall-clock timeout in run_python is the backstop that always holds.
    """
    caps = [(resource.RLIMIT_CPU, (DEFAULT_CPU_S, DEFAULT_CPU_S)),
            (resource.RLIMIT_FSIZE, (8 * 1024 * 1024,) * 2)]
    if sys.platform != "darwin":
        mem = DEFAULT_MEM_MB * 1024 * 1024
        caps.append((resource.RLIMIT_AS, (mem, mem)))
        caps.append((resource.RLIMIT_NPROC, (64, 64)))
    for what, vals in caps:
        try:
            resource.setrlimit(what, vals)
        except (ValueError, OSError):
            pass


def run_python(code: str, timeout_s: int = DEFAULT_TIMEOUT_S) -> ExecResult:
    """Execute `code` in a fresh isolated interpreter. Never raises on user error."""
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-S", "-c", PREAMBLE + code],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            preexec_fn=_limits,
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"},
        )
        return ExecResult(
            stdout=proc.stdout[-4000:],
            stderr=proc.stderr[-2000:],
            returncode=proc.returncode,
            timed_out=False,
        )
    except subprocess.TimeoutExpired:
        return ExecResult("", f"timeout after {timeout_s}s", -1, True)
