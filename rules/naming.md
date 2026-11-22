# Naming rules

## Targets

Rename only scoped local bindings, parameters, and loop variables that have weak generated names.

Common generated patterns:

- `v1`, `v12`, `u3`, `p4`, `a2`, `r8`, `t_1`
- `tbl`, `tbl4`, `Arg2`, `arg`, `var_3`
- `_l173`, `L_1`, `PROTO_5`, `STACK`, `REGISTER`
- `fn2`, `f4`, `thread2`, `connection3`

## Preferred Roblox names

| Kind | Examples |
|------|----------|
| Services | `Players`, `RunService`, `ReplicatedStorage`, `Workspace`, `HttpService`, `TweenService`, `UserInputService`, `Debris` |
| Player / character | `player`, `localPlayer`, `character`, `humanoid`, `rootPart`, `playerGui` |
| UI | `screenGui`, `frame`, `button`, `label`, `scrollFrame`, `uiTabs` |
| World | `tool`, `handle`, `hitbox`, `region`, `part`, `model`, `prompt` |
| Networking | `remoteEvent`, `remoteFunction`, `hitRemote`, `syncRemote` |
| Connections | `heartbeatConn`, `renderSteppedConn`, `characterAddedConn`, `inputBeganConn` |
| Tasks | `missionTask`, `raidTask`, `backgroundTask` |
| Config / data | `config`, `settings`, `defaults`, `options`, `state`, `cache` |

## Style

- Locals / functions: camelCase.
- Module exports or class-like tables: PascalCase only when the source already uses that convention.
- Constants: UPPER_SNAKE only for genuine constants.
- One binding keeps one name throughout its lexical scope.
- Shadowed bindings are separate variables and must be renamed independently.

## Safety and consistency

- Do not rename identifiers inside strings or comments.
- Do not rename member names after `.` or `:`.
- Do not rename literal table keys.
- Do not rename already meaningful identifiers.
- Avoid collisions with existing locals and reserved Lua / Luau names.
- If meaning is uncertain, prefer a neutral descriptive name over a guessed behavior.
