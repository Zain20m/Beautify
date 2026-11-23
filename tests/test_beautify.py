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

    def test_s_numbered_generated_locals_are_renamed_but_properties_and_strings_are_preserved(self):
        source = '''local s68 = {}
s68.Value = "s69"
print(s68)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertNotIn("s68", result)
        self.assertIn('Value = "s69"', result)
        self.assertEqual(report["remaining_garbage"], 0)

    def test_generated_ui_instance_locals_are_renamed_semantically(self):
        source = '''local Frame183 = Instance.new("Frame")
Frame183.BackgroundTransparency = 1
local TextLabel120 = Instance.new("TextLabel")
TextLabel120.Text = "Hello"
local UIListLayout46 = Instance.new("UIListLayout")
UIListLayout46.Padding = UDim.new(0, 6)
'''
        result, report = beautify.beautify(source, return_report=True, formatter="fallback")
        self.assertIn("local frame = Instance.new(\"Frame\")", result)
        self.assertIn("local textLabel = Instance.new(\"TextLabel\")", result)
        self.assertIn("local uiListLayout = Instance.new(\"UIListLayout\")", result)
        self.assertNotRegex(result, r"\\b(?:Frame183|TextLabel120|UIListLayout46)\\b")
        self.assertEqual(report["remaining_garbage"], 0)

    def test_generated_ui_property_spacing_is_compacted(self):
        source = '''local Frame183 = Instance.new("Frame")

Frame183.BackgroundTransparency = 1

Frame183.AutomaticSize = Enum.AutomaticSize.Y

Frame183.Size = UDim2.new(1, 0, 0, 0)
'''
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn("frame.BackgroundTransparency = 1\\nframe.AutomaticSize", result)
        self.assertIn("frame.AutomaticSize = Enum.AutomaticSize.Y\\nframe.Size", result)
        self.assertNotIn("BackgroundTransparency = 1\\n\\n", result)

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



    def test_trace_only_output_is_not_presented_as_source(self):
        source = '-- BEHAVIOUR TRACE ONLY\n-- 12 statements recorded\nfunction x() end\nDescendantAdded math_floor_precision\n'
        result = beautify.beautify(source, formatter="fallback")
        self.assertIn('NOT SOURCE', result)
        self.assertIn('No recoverable game logic', result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
