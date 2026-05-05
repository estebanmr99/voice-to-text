# GSD Tooling Recovery

Timestamp: 2026-05-04 20:06

## Diagnosis
- `where.exe gsd-sdk` initially failed: no executable found on PATH.
- `where.exe node` returned `C:\nvm4w\nodejs\node.exe`.
- `where.exe npm` returned `C:\nvm4w\nodejs\npm` and `C:\nvm4w\nodejs\npm.cmd`.
- `npm config get prefix` returned `C:\nvm4w\nodejs`.

## Recovery attempts
1. `npx.cmd get-shit-done-cc@latest --opencode --global --sdk`
   - Succeeded and installed GSD OpenCode assets under `~\.config\opencode`.
   - Result still did not add a shell-visible `gsd-sdk` executable.
2. `npx.cmd get-shit-done-cc@latest --opencode --global`
   - Same result: OpenCode assets installed, but no `gsd-sdk` shim on PATH.

## Current blocker
- `where.exe gsd-sdk` still fails in this PowerShell session.
- The installer reports the SDK is ready as `sdk/dist/cli.js`, but it is not exposed as an OS-level executable here.

## Exact next command
- Open a fresh PowerShell/OpenCode shell session, then rerun `where.exe gsd-sdk`.
- If it still fails, run OpenCode-native `/gsd-new-project` commands from inside OpenCode rather than the shell.

## Scope impact
- No production app code was created.
- `.planning/` source-of-truth artifacts were not generated because the shell cannot invoke `gsd-sdk`.

