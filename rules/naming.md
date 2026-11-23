# Naming rules

## Rename targets

Rename scoped locals, local functions, parameters, and loop variables only when their names are generated or weak.

Common obfuscator names: `v1`, `v12`, `t_1`, `s68`, `tbl4`, `Arg2`, `_l173`, `PROTO_5`, `UPVALUE_3`, `fn2`.

Weak earlier-pass names: `handleEvent`, `sendRemoteEvent`, `value12`, `numericValue2`, `eventConnection`.

## AST and binding rules

1. Prefer the Tree-sitter Luau AST for local/function/parameter/loop declarations and references.
2. Resolve each use to the nearest active declaration. Treat shadowed bindings independently.
3. Do not treat strings, comments, properties, method names, table keys, type names, or unbound globals as local references.
4. Keep the token scanner as an explicit fallback; report which backend was used.

## Semantic inference

- Functions: score names from the complete function body and its AST calls, member accesses, strings, and control flow. Exclude nested function bodies from the parent score.
- Parameters: use event/callback role plus that parameter's own reference sites.
- Locals: use constructors, initializers, assignments, properties, and nearby reference sites.
- Prefer action + target names for functions and role + type names for values.
- Store evidence/confidence for selected semantic names.
- Choose a neutral fallback or retain the original name when evidence is weak.
- Never use a confident name that claims behavior the source does not demonstrate.

## Preferred Roblox names

| Kind | Examples |
|------|----------|
| Services | `Players`, `RunService`, `ReplicatedStorage`, `Workspace`, `HttpService`, `TweenService`, `UserInputService`, `Debris` |
| Player / character | `player`, `localPlayer`, `character`, `humanoid`, `rootPart`, `playerGui` |
| UI | `screenGui`, `frame`, `button`, `label`, `scrollFrame`, `uiTabs` |
| World | `tool`, `handle`, `hitbox`, `region`, `part`, `model`, `prompt` |
| Networking | `remoteEvent`, `remoteFunction`, `hitRemote`, `syncRemote` |
| Tasks | `missionTask`, `raidTask`, `backgroundTask` |
| Config / data | `config`, `settings`, `defaults`, `options`, `state`, `cache`, `raidDefinition` |

## Missing code

- Do not rename unbound identifiers; they may be real globals or missing upvalues.
- Report common upvalue placeholders and unresolved generated references inside functions.
- Mark syntax-damaged functions as partial.
- Do not invent the missing upvalue definition or a replacement function.
