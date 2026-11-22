import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import beautify


class BeautifyTests(unittest.TestCase):
    def test_strings_and_comments_are_not_renamed(self):
        source = 'local v1 = "v1 fn2 -- still text" -- v1 in comment\nprint(v1)\n'
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
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
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn('local Players = game:GetService("Players")', result)
        self.assertIn('local state = {}', result)
        self.assertIn('state.Value = 4', result)
        self.assertIn('print(Players)', result)
        self.assertEqual(result.count('print(Players)'), 1)

    def test_function_parameters_do_not_leak_between_functions(self):
        source = '''local function fn1(a1) return a1.Name end
local function fn2(a1) return a1.Health end
'''
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn('return localValue.Name', result)
        self.assertIn('return humanoid.Health', result)
        self.assertNotIn('a1', result)

    def test_missing_service_alias_is_inferred(self):
        result, report = beautify.beautify('print(Players:GetPlayers())\n', return_report=True, formatter="fallback")
        self.assertIn('local Players = game:GetService("Players")', result)
        self.assertEqual(report["inferred_services"], ["Players"])

    def test_inline_blocks_and_semicolons_are_expanded(self):
        source = 'local function fn1(a1) if a1 then print(a1.Name) else print("end then v1") end end;local v1=Players:GetPlayers()'
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn('local function eventHandler(localValue)\n    if localValue then\n', result)
        self.assertIn('        print("end then v1")', result)
        self.assertIn('local localValue2 = Players:GetPlayers()', result)

    def test_member_names_and_string_literals_are_not_treated_as_locals(self):
        source = '''local v1 = {}
v1.v2 = "v3"
return v1.v2
'''
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn('state.v2 = "v3"', result)
        self.assertIn('return state.v2', result)

    def test_malformed_input_is_preserved_and_reported(self):
        result, report = beautify.beautify('local v1 = 1\nend\n', return_report=True, formatter="fallback")
        self.assertIn('\nend\n', result)
        self.assertTrue(any("unmatched 'end'" in item for item in report["diagnostics"]))


    def test_reuses_existing_service_aliases(self):
        source = """local ReplicatedStorage = game:GetService("ReplicatedStorage")
game:GetService("ReplicatedStorage"):WaitForChild("requests"):FireServer()
"""
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertIn('ReplicatedStorage:WaitForChild("requests")\n    :FireServer()', result)
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
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertIn('game:GetService("Players")\n    :GetPlayers()', result)
        self.assertIn('Players:GetPlayers()', result)
        self.assertEqual(report["canonicalized_service_calls"], 1)

    def test_clean_indentation_and_function_spacing(self):
        source = """local function fn1(a1) if a1 then return false else local v1=2;print(v1) end end
local function fn2() local v2=3;return v2 end
"""
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn("""local function eventHandler(localValue)
    if localValue then
        return false
    else
        local localValue2 = 2
        print(localValue2)
    end
end

local function eventHandler2()
    local localValue3 = 3
    return localValue3
end""", result)
        self.assertNotRegex(result, r"(?m)^        (?:end|else|elseif)\s*$")
        self.assertNotRegex(result, r"(?m)^.*[ \t]+$")

    def test_binary_operator_spacing_is_normalized(self):
        result = beautify.beautify('local v1=2;local v2=v1+ -1;if v2>=1 and v2~=3 then print("a==b") end', formatter="fallback")
        self.assertIn('local localValue = 2', result)
        self.assertIn('local localValue2 = localValue + -1', result)
        self.assertIn('if localValue2 >= 1 and localValue2 ~= 3 then', result)
        self.assertIn('print("a==b")', result)

    def test_unbound_generated_names_are_reported_not_guessed(self):
        result, report = beautify.beautify('return H_1() + fn14(1)\n', return_report=True, formatter="fallback")
        self.assertIn('return H_1() + fn14(1)', result)
        self.assertEqual(report["unresolved_generated_identifiers"], ["fn14", "H_1"])
        self.assertGreater(report["remaining_garbage"], 0)

 
    def test_chain_calls_are_formatted_one_per_line(self):
        source = '''local v1 = game:GetService("ReplicatedStorage")
v1:WaitForChild("requests"):WaitForChild("character"):WaitForChild("spawn"):FireServer()
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertIn('ReplicatedStorage:WaitForChild("requests")\n    :WaitForChild("character")\n    :WaitForChild("spawn")\n    :FireServer()', result)
        self.assertEqual(report["chain_breaks"], 3)

    def test_table_fields_are_split_without_breaking_call_arguments(self):
        source = 'local v1 = { first = math.max(1, 2), second = { 3, 4 }, third = "x,y" }'
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertIn('first = math.max(1, 2),\n', result)
        self.assertIn('second = { 3, 4 },\n', result)
        self.assertEqual(report["table_field_breaks"], 2)

    def test_auto_falls_back_for_incomplete_devirtualized_input(self):
        source = 'local v1 = 1\nprint(v1)\nend\n'
        result, report = beautify.beautify(source, return_report=True, formatter="auto")
        self.assertIn('local localValue = 1', result)
        self.assertIn('unmatched', " ".join(report["diagnostics"]))
        self.assertEqual(report["formatter_used"], "fallback")
        self.assertTrue(report["formatter_warning"])

    def test_stylua_formats_valid_luau_when_installed(self):
        if not beautify.find_stylua():
            self.skipTest("StyLua is not installed")
        source = 'local Players=game:GetService("Players")\nlocal function f()return Players:GetPlayers()end'
        result, report = beautify.beautify(source, return_report=True, formatter="stylua")
        self.assertEqual(report["formatter_used"], "stylua")
        self.assertTrue(report["ast_formatted"])
        self.assertIn('local Players = game:GetService("Players")', result)



    def test_semantic_function_names_use_function_body(self):
        source = '''local function handleEvent()
    local live = workspace:FindFirstChild("Live")
    for _, entry in pairs(live:GetChildren()) do
        if string.sub(entry.Name, 1, 7) == prefix then
            return entry
        end
    end
end
'''
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn("local function findLiveEntityByPrefix()", result)
        self.assertNotIn("handleEvent", result)

    def test_semantic_names_infer_engine_objects_and_data(self):
        source = '''local v1 = Instance.new("BodyVelocity")
local v2 = Instance.new("BodyGyro")
local value12 = raidDefinitions[selectedRaid]
'''
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn("local bodyVelocity = Instance.new", result)
        self.assertIn("local bodyGyro = Instance.new", result)
        self.assertIn("local raidDefinition = raidDefinitions[selectedRaid]", result)

    def test_unused_generated_literal_is_removed_but_effectful_initializer_stays(self):
        source = '''local v1 = 123
local v2 = doWork()
print(v2)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertNotIn("local v1", result)
        self.assertIn("doWork()", result)
        self.assertIn("print(localValue)", result)
        self.assertEqual(report["removed_junk_statements"], 1)

    def test_pure_cleanup_does_not_drop_effectful_table_pack_arguments(self):
        source = '''table.pack(doWork())
table.pack(1, 2, true)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertIn("table.pack(doWork())", result)
        self.assertNotIn("table.pack(1, 2, true)", result)
        self.assertEqual(report["removed_junk_statements"], 1)



    def test_renames_fluent_option_temporaries_from_their_value_source(self):
        source = '''local value = fluentLibrary.Options.TargetPlayer.Value
print(value)
'''
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn("local targetPlayerName = fluentLibrary.Options.TargetPlayer.Value", result)
        self.assertIn("print(targetPlayerName)", result)

    def test_callback_boolean_parameter_uses_function_context(self):
        source = '''local function updateButtonAppearance(argument)
    if argument then
        return Color3.fromRGB(255, 255, 255)
    end
end
'''
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn("local function updateButtonAppearance(isHovered)", result)
        self.assertIn("if isHovered then", result)



    def test_tree_sitter_ast_handles_nested_shadowing(self):
        source = '''local v1 = "outer"
local function fn2(p1)
    do
        local v1 = "inner"
        print(v1)
    end
    return v1
end
print(v1)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertIn('local textValue = "outer"', result)
        self.assertIn('local textValue2 = "inner"', result)
        self.assertIn("print(textValue2)", result)
        self.assertIn("return textValue", result)
        self.assertIn("print(textValue)", result)

    def test_ast_loop_and_repeat_scopes_are_resolved(self):
        source = '''local v1 = "outside"
for v1 = 1, 3 do
    print(v1)
end
repeat
    local v2 = 1
until v2 > 2
print(v1)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertIn('local textValue = "outside"', result)
        self.assertIn("for localValue = 1, 3 do", result)
        self.assertIn("print(localValue)", result)
        self.assertIn("until numberValue > 2", result)
        self.assertIn("print(textValue)", result)

    def test_ast_function_name_uses_syntax_evidence(self):
        fixture = ROOT / "tests" / "fixtures" / "register_vm_style.lua"
        result, report = beautify.beautify(fixture.read_text(encoding="utf-8"), return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertIn("local function isCharacterAlive", result)
        self.assertGreater(report["ast_scope_count"], 1)

    def test_ast_parses_typed_luau_and_generic_functions(self):
        fixture = ROOT / "tests" / "fixtures" / "luau_typed_scopes.luau"
        result, report = beautify.beautify(fixture.read_text(encoding="utf-8"), return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertEqual(report["ast_syntax_errors"], 0)
        self.assertIn("type PlayerRecord", result)
        self.assertIn("local function", result)

    def test_fixture_corpus_covers_register_string_pool_and_partial_outputs(self):
        fixtures = ROOT / "tests" / "fixtures"
        valid_names = ("register_vm_style.lua", "string_pool_closure.lua", "luau_typed_scopes.luau")
        for name in valid_names:
            source = (fixtures / name).read_text(encoding="utf-8")
            _, report = beautify.beautify(source, return_report=True, formatter="fallback")
            self.assertEqual(report["ast_backend"], "tree-sitter-luau", name)
            self.assertEqual(report["ast_syntax_errors"], 0, name)

        partial_source = (fixtures / "partial_vm_lifter.lua").read_text(encoding="utf-8")
        _, partial_report = beautify.beautify(partial_source, return_report=True, formatter="fallback")
        self.assertGreater(partial_report["ast_syntax_errors"], 0)
        self.assertTrue(partial_report["partial_functions"])
        self.assertTrue(partial_report["possible_missing_upvalues"])

    def test_unbound_upvalues_are_reported_without_fabricated_definitions(self):
        source = '''local function fn14(player)
    if player then
        return H_1(player) + UPVALUE_3
    end
    return fn77
end
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        names = {item["name"] for item in report["possible_missing_upvalues"]}
        self.assertTrue({"H_1", "UPVALUE_3", "fn77"}.issubset(names))
        self.assertNotIn("local H_1", result)
        self.assertNotIn("local UPVALUE_3", result)
        self.assertTrue(any("possible missing upvalue" in item.lower() for item in report["diagnostics"]))



    def test_tree_sitter_ast_handles_nested_shadowing(self):
        source = '''local v1 = "outer"
local function fn2(p1)
    do
        local v1 = "inner"
        print(v1)
    end
    return v1
end
print(v1)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertIn('local textValue = "outer"', result)
        self.assertIn('local textValue2 = "inner"', result)
        self.assertIn("print(textValue2)", result)
        self.assertIn("return textValue", result)
        self.assertIn("print(textValue)", result)

    def test_ast_loop_and_repeat_scopes_are_resolved(self):
        source = '''local v1 = "outside"
for v1 = 1, 3 do
    print(v1)
end
repeat
    local v2 = 1
until v2 > 2
print(v1)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertIn('local textValue = "outside"', result)
        self.assertIn("for localValue = 1, 3 do", result)
        self.assertIn("print(localValue)", result)
        self.assertIn("until localValue2 > 2", result)
        self.assertIn("print(textValue)", result)

    def test_ast_function_name_uses_syntax_evidence(self):
        fixture = ROOT / "tests" / "fixtures" / "register_vm_style.lua"
        result, report = beautify.beautify(fixture.read_text(encoding="utf-8"), return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertIn("local function isCharacterAlive", result)
        self.assertGreater(report["ast_scope_count"], 1)
        self.assertTrue(report["semantic_name_decisions"])

    def test_ast_parses_typed_luau_and_generic_functions(self):
        fixture = ROOT / "tests" / "fixtures" / "luau_typed_scopes.luau"
        result, report = beautify.beautify(fixture.read_text(encoding="utf-8"), return_report=True, formatter="fallback")
        self.assertEqual(report["ast_backend"], "tree-sitter-luau")
        self.assertEqual(report["ast_syntax_errors"], 0)
        self.assertIn("type PlayerRecord", result)
        self.assertIn("local function", result)

    def test_fixture_corpus_covers_register_string_pool_and_partial_outputs(self):
        fixtures = ROOT / "tests" / "fixtures"
        valid_names = ("register_vm_style.lua", "string_pool_closure.lua", "luau_typed_scopes.luau")
        for name in valid_names:
            source = (fixtures / name).read_text(encoding="utf-8")
            _, report = beautify.beautify(source, return_report=True, formatter="fallback")
            self.assertEqual(report["ast_backend"], "tree-sitter-luau", name)
            self.assertEqual(report["ast_syntax_errors"], 0, name)

        partial_source = (fixtures / "partial_vm_lifter.lua").read_text(encoding="utf-8")
        _, partial_report = beautify.beautify(partial_source, return_report=True, formatter="fallback")
        self.assertGreater(partial_report["ast_syntax_errors"], 0)
        self.assertTrue(partial_report["partial_functions"])
        self.assertTrue(partial_report["possible_missing_upvalues"])

    def test_unbound_upvalues_are_reported_without_fabricated_definitions(self):
        source = '''local function fn14(player)
    if player then
        return H_1(player) + UPVALUE_3
    end
    return fn77
end
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        names = {item["name"] for item in report["possible_missing_upvalues"]}
        self.assertTrue({"H_1", "UPVALUE_3", "fn77"}.issubset(names))
        self.assertNotIn("local H_1", result)
        self.assertNotIn("local UPVALUE_3", result)
        self.assertTrue(any("possible missing upvalue" in item.lower() for item in report["diagnostics"]))


    def test_trace_only_output_is_not_presented_as_source(self):
        source = '-- BEHAVIOUR TRACE ONLY\n-- 12 statements recorded\nfunction x() end\nDescendantAdded math_floor_precision\n'
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn('NOT SOURCE', result)
        self.assertIn('No recoverable game logic', result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
