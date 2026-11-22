import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import beautify


class BeautifyTests(unittest.TestCase):
    def test_strings_and_comments_are_not_renamed(self):
        source = 'local v1 = "v1 fn2 -- still text" -- v1 in comment\nprint(v1)\n'
        result, report = beautify.beautify(source, return_report=True)
        self.assertIn('"v1 fn2 -- still text"', result)
        self.assertIn('-- v1 in comment', result)
        self.assertIn('print(textValue)', result)
        self.assertEqual(report["remaining_garbage"], 0)

    def test_shadowed_locals_get_separate_bindings(self):
        source = '''local v1 = game:GetService("Players")
do
    local v1 = {}
    v1.Value = 4
    print(v1)
end
print(v1)
'''
        result = beautify.beautify(source)
        self.assertIn('local Players = game:GetService("Players")', result)
        self.assertIn('local state = {}', result)
        self.assertIn('state.Value = 4', result)
        self.assertIn('print(Players)', result)
        self.assertEqual(result.count('print(Players)'), 1)

    def test_function_parameters_do_not_leak_between_functions(self):
        source = '''local function fn1(a1) return a1.Name end
local function fn2(a1) return a1.Health end
'''
        result = beautify.beautify(source)
        self.assertIn('return value.Name', result)
        self.assertIn('return humanoid.Health', result)
        self.assertNotIn('a1', result)

    def test_missing_service_alias_is_inferred(self):
        result, report = beautify.beautify('print(Players:GetPlayers())\n', return_report=True)
        self.assertIn('local Players = game:GetService("Players")', result)
        self.assertEqual(report["inferred_services"], ["Players"])

    def test_inline_blocks_and_semicolons_are_expanded(self):
        source = 'local function fn1(a1) if a1 then print(a1.Name) else print("end then v1") end end;local v1=Players:GetPlayers()'
        result = beautify.beautify(source)
        self.assertIn('local function handleEvent(value)\n    if value then\n', result)
        self.assertIn('        print("end then v1")', result)
        self.assertIn('local value2 = Players:GetPlayers()', result)

    def test_member_names_and_string_literals_are_not_treated_as_locals(self):
        source = '''local v1 = {}
v1.v2 = "v3"
return v1.v2
'''
        result = beautify.beautify(source)
        self.assertIn('state.v2 = "v3"', result)
        self.assertIn('return state.v2', result)

    def test_malformed_input_is_preserved_and_reported(self):
        result, report = beautify.beautify('local v1 = 1\nend\n', return_report=True)
        self.assertIn('\nend\n', result)
        self.assertTrue(any("unmatched 'end'" in item for item in report["diagnostics"]))


    def test_reuses_existing_service_aliases(self):
        source = """local ReplicatedStorage = game:GetService("ReplicatedStorage")
game:GetService("ReplicatedStorage"):WaitForChild("requests"):FireServer()
"""
        result, report = beautify.beautify(source, return_report=True)
        self.assertIn('ReplicatedStorage:WaitForChild("requests"):FireServer()', result)
        self.assertNotIn('game:GetService("ReplicatedStorage"):WaitForChild', result)
        self.assertEqual(report["canonicalized_service_calls"], 1)

    def test_does_not_reuse_service_alias_before_or_under_shadowing(self):
        source = """game:GetService("Players"):GetPlayers()
local Players = game:GetService("Players")
do
    local Players = {}
    game:GetService("Players"):GetPlayers()
end
game:GetService("Players"):GetPlayers()
"""
        result, report = beautify.beautify(source, return_report=True)
        self.assertIn('game:GetService("Players"):GetPlayers()', result)
        self.assertIn('Players:GetPlayers()', result)
        self.assertEqual(report["canonicalized_service_calls"], 1)

    def test_clean_indentation_and_function_spacing(self):
        source = """local function fn1(a1) if a1 then return false else local v1=2 end end
local function fn2() local v2=3;return v2 end
"""
        result = beautify.beautify(source)
        self.assertIn("""local function handleEvent(value)
    if value then
        return false
    else
        local value2 = 2
    end
end

local function handleEvent2()
    local value3 = 3
    return value3
end""", result)
        self.assertNotRegex(result, r"(?m)^        (?:end|else|elseif)\\s*$")
        self.assertNotRegex(result, r"(?m)^.*[ \\t]+$")

    def test_binary_operator_spacing_is_normalized(self):
        result = beautify.beautify('local v1=2;local v2=v1+ -1;if v2>=1 and v2~=3 then print("a==b") end')
        self.assertIn('local value = 2', result)
        self.assertIn('local value2 = value + -1', result)
        self.assertIn('if value2 >= 1 and value2 ~= 3 then', result)
        self.assertIn('print("a==b")', result)

    def test_unbound_generated_names_are_reported_not_guessed(self):
        result, report = beautify.beautify('return H_1() + fn14(1)\n', return_report=True)
        self.assertIn('return H_1() + fn14(1)', result)
        self.assertEqual(report["unresolved_generated_identifiers"], ["fn14", "H_1"])
        self.assertGreater(report["remaining_garbage"], 0)

    def test_trace_only_output_is_not_presented_as_source(self):
        source = '-- BEHAVIOUR TRACE ONLY\n-- 12 statements recorded\nfunction x() end\nDescendantAdded math_floor_precision\n'
        result = beautify.beautify(source)
        self.assertIn('NOT SOURCE', result)
        self.assertIn('No recoverable game logic', result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
