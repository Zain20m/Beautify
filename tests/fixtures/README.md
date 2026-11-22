# Regression fixtures

These fixtures are small, synthetic source fragments designed to exercise parser and recovery patterns. They are not claimed to be exact captures from proprietary obfuscators.

- `register_vm_style.lua`: generated register-like locals and local function.
- `string_pool_closure.lua`: lookup table, nested closure, and captured local.
- `luau_typed_scopes.luau`: generic function declarations and typed parameters/locals.
- `partial_vm_lifter.lua`: intentionally incomplete function and generated upvalue placeholders.

Run all fixtures through the AST analysis and fallback pipeline with:

```bash
python3 -m unittest discover -s tests -v
```
