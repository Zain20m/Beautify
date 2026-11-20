# Examples

Synthetic teaching pairs (not real game dumps).

| File | Difficulty | What it shows |
|------|------------|----------------|
| `before.lua` → `after.lua` | Medium | Banners, `v1`/`tbl4`/`Arg3`/`_l173`, a few junk lines |
| `before_extreme.lua` → `after_extreme.lua` | **Hard** | Almost the **whole file** is unreadable: minified lines, `Arg3`/`Arg4`/`_l10`/`fn2`/`v22`, pure junk, packed logic |

## Extreme name map

| Before | After |
|--------|--------|
| `v1`…`v6` | `Players` … `Debris` (services) |
| `tbl1` | `localPlayer` |
| `tbl3` | `remotesFolder` |
| `tbl4` | `state` |
| `Arg1` | `hitRemote` |
| `Arg2` | `syncRemote` |
| `Arg3` | `swingAttack` |
| `Arg4` | `onInputBegan` |
| `_l10` | `getOrSet` |
| `_l11` | `getHumanoidAndRoot` |
| `_l99` | `requestBoot` |
| `fn2` | `applyCharacterStats` |
| `v22`/`v24`/`v25`/`v29` | connection locals |

## For the AI

When the **entire** script looks like `before_extreme.lua`:

1. Do not give up or only rename 3 variables.
2. Walk top to bottom; rename **every** `v#` / `tbl#` / `Arg#` / `_l#` / `fn#`.
3. Unpack minified lines into normal blocks.
4. Delete only provable junk (`bit32` on constants, `type(123)`, empty `do end`).
5. Keep behaviour identical.

Paste [`../AI_PROMPT.md`](../AI_PROMPT.md), then `before_extreme.lua`, and compare to `after_extreme.lua`.
