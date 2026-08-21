---
name: bb-fixes-bootstrap
description: Detects and applies the known BB + Prime Agent fixes (ACP session restore, usage plugin pricing/day-bucketing/cache-savings, prime-agent ACP slash commands), then verifies them. Use when setting up a fresh BB/Prime Agent machine, after reinstalling BB or prime-agent, when BB shows "could not restore the previous session", when usage cache savings are zero, or when /plan-style commands do not work in a BB Prime Agent thread.
---

# BB + Prime Agent Fixes Bootstrap

Call directly from the kernel:

    await bb_fixes_bootstrap(home="/home/you")

Or from a shell cell:

    !bb_fixes_bootstrap --home /home/you

It checks, applies, and verifies all known fixes. Idempotent and safe: it only
touches the exact files it knows how to repair, and it reports what changed.

Seen in the machine currently being set up? Run this skill once after BB and
prime-agent are installed; rerun any time to re-verify.

## What it checks and repairs

1. **ACP shim resume** (`<home>/.bb/bin/pa-acp.sh`): ensures the final exec line
   is `exec prime-agent --continue $out` so BB thread restarts keep session
   history instead of showing the "could not restore the previous session"
   banner. If it only has `$out`, the line is rewritten.
2. **prime-agent ACP slash commands + session/load** (source at the configured
   repo): if `<repo>/packages/coding-agent/src/modes/acp/acp-mode.ts` is missing
   the slash-command helpers / `session/load` handler, prints the exact patch to
   apply (it cannot edit prime-agent source automatically by design; you apply
   the patch, then rerun with `apply_prime_patch=True` to let the skill apply it
   if a patch file is present).
   - Optional `apply_prime_patch` argument: when true and a patch file already
     staged at `<home>/bb-fixes/prime-agent/acp-fixes.patch`, the skill applies
     it with `git apply`.
3. **Usage plugin**: reads the installed plugin source path from
   `bb plugin list`; verifies cache savings are computed
   (`cacheSavingsUsd: pricing.price ?`), Prime/Pi use logged-only costs, and the
   opencode collector skips when the CLI is missing. Reports which source
   markers are present or absent.

## Output

Returns a short markdown report: ✔ applied / ✔ already present / ✖ blocked
(with the reason and the exact next step) for each item. No destructive or
broad filesystem changes are made.
