"""Detect, apply, and verify the known BB + Prime Agent fixes.

Exposed to the kernel as `bb_fixes_bootstrap`. Safe and idempotent: it only
repairs the exact files it understands and never makes broad changes.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

EXPECTED_EXEC_LINE = "exec prime-agent --continue $out"

# Markers that make the usage plugin "fixed" vs "stock".
USAGE_FIXED_MARKERS = {
    "logged-cost pricing": 'costMode: "positive-logged-only"',
    "cache savings": "cacheSavingsUsd: pricing.price ?",
    "opencode skip": "OpenCode CLI is required to collect OpenCode usage.",
    "local days": "date('now', 'localtime',",
}
ACP_FIX_MARKERS = {
    "slash commands": "function acpSlashCommand(",
    "session/load": '.onRequest("session/load"',
    "advertised loadSession": "loadSession: true,",
}


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except Exception as exc:  # pragma: no cover - defensive
        return 1, str(exc)


def _which(name: str) -> Path | None:
    found = shutil.which(name)
    if found:
        return Path(found)
    # bb may only be reachable through the npx bb-app cache.
    npx = Path.home() / ".npm" / "_npx"
    if npx.is_dir():
        for entry in npx.iterdir():
            cand = entry / "node_modules" / ".bin" / name
            if cand.exists():
                return cand
    return None


def _fix_shim(shim: Path) -> str:
    if not shim.exists():
        return f"blocked: {shim} does not exist (run `bb prime-agent setup` first)"
    text = shim.read_text()
    if EXPECTED_EXEC_LINE in text:
        return "already present"
    if "exec prime-agent" in text:
        rewritten = text.replace("exec prime-agent $out", EXPECTED_EXEC_LINE)
        shim.write_text(rewritten)
        return f"rewrote exec line to: {EXPECTED_EXEC_LINE}"
    return "blocked: shim exec line not recognized; report contents for a custom fix"


def _usage_status(bb: str | None) -> dict[str, str]:
    if not bb:
        return {"source": "blocked: bb CLI not found"}
    code, out = _run([bb, "plugin", "list"])
    source = ""
    lines = out.splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("usage@"):
            continue
        # bb prints the source on the line(s) right after the plugin header.
        m = re.search(r"path:(\S+)", line)
        if not m:
            for nxt in lines[i + 1 : i + 3]:
                m = re.search(r"path:(\S+)", nxt)
                if m:
                    break
        if m:
            source = m.group(1)
        break
    if not source:
        return {"source": "blocked: bb-plugin-usage not installed or path source unparsed"}
    src_path = Path(source)
    status: dict[str, str] = {"source": str(src_path)}
    targets = {
        "logged-cost pricing": src_path / "collectors.ts",
        "cache savings": src_path / "collectors.ts",
        "opencode skip": src_path / "server.ts",
        "local days": src_path / "server.ts",
    }
    for label, marker in USAGE_FIXED_MARKERS.items():
        target = targets[label]
        status[label] = "present" if target.exists() and marker in target.read_text(errors="replace") else "missing"
    return status


def _prime_agent_path() -> Path | None:
    exe = _which("prime-agent")
    if exe:
        resolved = exe.resolve()
        if "prime-agent-src" in str(resolved):
            return resolved.parent.parent
    for root in (Path.home(), Path("/home")):
        cand = root / "ai-stack" / "prime-agent-src"
        if cand.exists():
            return cand
    return None


def _acp_status(repo: Path | None) -> dict[str, str]:
    if not repo:
        return {"source": "blocked: prime-agent source not found"}
    acp = repo / "packages" / "coding-agent" / "src" / "modes" / "acp" / "acp-mode.ts"
    if not acp.exists():
        return {"source": f"blocked: acp-mode.ts not found in {repo}"}
    text = acp.read_text(errors="replace")
    status: dict[str, str] = {"source": str(acp)}
    for label, marker in ACP_FIX_MARKERS.items():
        status[label] = "present" if marker in text else "missing"
    return status


def _apply_patch(home: Path, repo: Path) -> str:
    patch = home / "bb-fixes" / "prime-agent" / "acp-fixes.patch"
    if not patch.exists():
        return f"blocked: no patch file at {patch}"
    code, out = _run(["git", "apply", str(patch)], cwd=str(repo))
    return f"applied ({code})" if code == 0 else f"failed: {out.strip()[:300]}"


async def run(home: str | None = None, apply_prime_patch: bool = False) -> str:
    """Check and apply the BB + Prime Agent fixes.

    Args:
        home: Home directory to look in (defaults to $HOME).
        apply_prime_patch: When true and <home>/bb-fixes/prime-agent/acp-fixes.patch
            exists, also apply the prime-agent ACP patch with `git apply`.
    """
    home = home or os.environ.get("HOME", "/home/admin1")
    h = Path(home).expanduser()

    bb = _which("bb") or _which("bb-app")
    shim = h / ".bb" / "bin" / "pa-acp.sh"
    repo = _prime_agent_path()

    sections: list[str] = []
    sections.append(f"## bb-plugin-prime-agent shim\n{_fix_shim(shim)}")

    usage = _usage_status(str(bb) if bb else None)
    sections.append("## bb-plugin-usage\n" + "\n".join(f"- {k}: {v}" for k, v in usage.items()))

    acp = _acp_status(repo)
    lines = [f"- {k}: {v}" for k, v in acp.items()]
    if apply_prime_patch and repo and any(v == "missing" for k, v in acp.items() if k != "source"):
        lines.append("- patch: " + _apply_patch(h, repo))
    sections.append("## prime-agent ACP\n" + "\n".join(lines))

    return "\n\n".join(sections)
