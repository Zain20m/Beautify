# Naming rules

## Forbidden leftovers

Do not leave these in final output:

- `v0`…`v99`, `u0`…, `p0`…, `a0`… as final names
- `tbl`, `tbl1`, `Arg1`, `arg_1`, `var_1`
- `_l123`, `LPH_*` locals that are not real API
- `PROTO_`, `STACK`, `R6`, `REGISTER`
- `f1`, `fn2` without meaning

## Preferred Roblox names

| Kind | Examples |
|------|----------|
| Services | `Players`, `RunService`, `ReplicatedStorage`, `Workspace`, `HttpService`, `TweenService`, `UserInputService`, `Debris`, `Lighting`, `CollectionService` |
| Player | `player`, `localPlayer`, `character`, `humanoid`, `rootPart`, `playerGui` |
| UI | `screenGui`, `frame`, `button`, `label`, `scrollFrame` |
| Combat / world | `tool`, `handle`, `hitbox`, `region`, `part`, `model` |
| Networking | `remoteEvent`, `remoteFunction`, `onServerEvent` |
| Connections | `heartbeatConn`, `renderConn`, `addedConn`, `conn` |
| Config | `config`, `settings`, `defaults`, `options` |

## Style

- Locals / functions: `camelCase`
- Module exports / “class” tables: `PascalCase` if the script already leans that way
- Constants: `UPPER_SNAKE` only for true constants
- One binding → one name for the whole file
