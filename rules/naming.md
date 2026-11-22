# Naming rules

## Rename targets

Rename scoped locals, local functions, parameters, and loop variables only when their names are generated or weak.

Common obfuscator names:
- `v1`, `v12`, `u3`, `p4`, `a2`, `r8`, `t_1`
- `tbl4`, `Arg2`, `arg`, `var_3`, `_l173`, `L_1`
- `PROTO_5`, `STACK`, `REGISTER`, `fn2`, `f4`

Weak names from an earlier cleanup pass:
- `handleEvent`, `handleEvent2`, `sendRemoteEvent`
- `value`, `value12`, `numericValue2`, `argument`
- `eventConnection`, `isFeatureEnabled`

## Naming process

1. Build lexical bindings and resolve every reference to its declaration.
2. Infer functions from complete bodies and nearby API usage; use action + target names.
3. Infer callback parameters from event names and properties used in the callback.
4. Infer locals from constructors, initializer expressions, assignments, property access, and surrounding function context.
5. Reuse Roblox service names and instance names when the source directly supports them.
6. Keep generated replacement names unique and outside the generated-name pattern.

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
| Config / data | `config`, `settings`, `defaults`, `options`, `state`, `cache`, `raidDefinition` |

## Style and safety

- Locals / functions: camelCase. Module exports: preserve the source's existing convention.
- Do not rename strings, comments, literal table keys, API members after `.` / `:`, or unrelated bindings.
- Do not rename unbound identifiers; they may be legitimate globals or missing devirtualized upvalues.
- When meaning is uncertain, choose `localValue`, `state`, `item`, or `argument`, or preserve the original name.
- Never assign a function a behavior name that its body does not support.
