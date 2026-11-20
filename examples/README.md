# Examples

Synthetic **before → after** pair for teaching the AI (not a real game dump).

| File | What it shows |
|------|----------------|
| `before.lua` | Typical deobfuscator soup: banners, `v1`/`tbl4`/`Arg3`/`_l173`/`fn1`, pure junk (`bit32.bxor`, `type(123)`, `do end`) |
| `after.lua` | Same behaviour as clean Roblox Luau: `GetService`, real names, no tool noise |

## Name map (for learning)

| Before | After |
|--------|--------|
| `v1` | `Players` |
| `v2` | `RunService` |
| `v3` | `ReplicatedStorage` |
| `v4` | `UserInputService` |
| `tbl1` | `localPlayer` |
| `tbl2` | `playerGui` |
| `tbl3` | `remotes` |
| `tbl4` | `config` |
| `Arg1` | `combatEvent` |
| `Arg2` | `dataFunction` |
| `Arg3` | `fireCombat` |
| `_l173` | `setupCharacter` |
| `fn1` | `onInputBegan` |
| `v5` | `DEFAULT_RANGE` |
| `v6` | `walkSpeed` |
| `v14` / `v15` / `v16` | `characterAddedConn` / `inputBeganConn` / `heartbeatConn` |

Use with [`../AI_PROMPT.md`](../AI_PROMPT.md): paste the prompt, then `before.lua`, and check the model against `after.lua`.
