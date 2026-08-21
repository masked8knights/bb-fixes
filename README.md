# BB + Prime Agent fixes bundle

One-stop fixes for a fresh BB + Prime Agent setup:
ACP session restore (`bb-plugin-prime-agent`), usage dashboard fixes
(`bb-plugin-usage`), and local prime-agent ACP improvements with no upstream PR.

## Contents

- `plugins/bb-plugin-prime-agent/` — ACP shim now passes `--continue` so BB
  thread restarts resume the previous prime-agent session instead of showing
  "could not restore the previous session; continuing in a fresh session".
- `plugins/bb-plugin-usage/` — logged-cost pricing, local-timezone day
  bucketing, cache savings, opencode skipped-when-no-CLI, zero-token guard.
- `prime-agent/acp-fixes.patch` — local (uncommitted, no upstream PR) ACP mode
  changes: `session/load` support + `/plan /modify /todo /status /help /compact
  /effort` slash commands.
- `prime-agent/pa-acp.sh` — the fixed live shim as installed here.

## Install on a new machine

### 1. Plugins

```bash
bb plugin install ./plugins/bb-plugin-prime-agent
bb prime-agent setup

bb plugin install ./plugins/bb-plugin-usage
bb prime-agent setup   # then configure usage as usual
```

(Readme/usage docs live inside each plugin folder.)

### 2. Prime-agent source patches (local only)

```bash
git clone https://github.com/PrimeIntellect-ai/prime-agent.git
cd prime-agent
git apply /path/to/this/repo/prime-agent/acp-fixes.patch
```

### 3. Shim (if not using the plugin's setup)

Copy `prime-agent/pa-acp.sh` to `~/.bb/bin/pa-acp.sh` (chmod 755) and keep the
`customAcpAgents` entry pointing at it.

## Notes

- prime-agent runs from source via tsx here; the patch takes effect on the
  next BB thread restart.
- Slash commands take effect after a prime-agent restart; `/status` and
  `/help` are handled locally (no token spend).
