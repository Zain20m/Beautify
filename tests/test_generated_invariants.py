"""Deterministic generated-input invariants for the Luau beautifier.

These tests complement hand-written fixtures by exercising many combinations of
nested scopes, closures, loops, Unicode comments, and generated identifiers.
They are not a substitute for a real-world obfuscator corpus.
"""
from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_luau

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import beautify


def make_parser() -> Parser:
    return Parser(Language(tree_sitter_luau.language()))


def generated_program(seed: int) -> tuple[str, str]:
    rng = random.Random(seed)
    outer = rng.randint(1, 900)
    inner = rng.randint(1, 900)
    loop_value = rng.randint(1, 900)
    marker = f"literal-marker-{seed}"
    source = f'''-- Unicode comment: café 🐈 seed={seed}
local v{outer} = {rng.randint(1, 100)}
local function fn{seed}(a{seed})
    local v{inner} = a{seed} + {rng.randint(1, 20)}
    do
        local v{outer} = "{marker}"
        print(v{outer})
    end
    local total{seed} = 0
    for _, item{seed} in ipairs({{1, 2, 3}}) do
        local v{loop_value} = item{seed} + v{inner}
        total{seed} = total{seed} + v{loop_value}
    end
    return total{seed} + v{inner}
end
print(fn{seed}(v{outer}))
'''
    return source, marker


class GeneratedInvariantTests(unittest.TestCase):
    def test_generated_nested_scope_programs_remain_parseable(self):
        parser = make_parser()
        for seed in range(64):
            with self.subTest(seed=seed):
                source, marker = generated_program(seed)
                output = beautify.beautify(source, formatter="fallback")
                tree = parser.parse(output.encode("utf-8"))
                self.assertFalse(
                    tree.root_node.has_error,
                    f"Beautifier produced invalid Luau for seed {seed}:\n{output}",
                )
                self.assertIn(marker, output)
                self.assertIn(f"seed={seed}", output)

    def test_generated_output_is_stable_on_second_pass(self):
        for seed in range(16):
            with self.subTest(seed=seed):
                source, _ = generated_program(seed)
                once = beautify.beautify(source, formatter="fallback")
                twice = beautify.beautify(once, formatter="fallback")
                self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main(verbosity=2)
