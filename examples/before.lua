-- Deobfuscated by daily deobf
-- Detected obfuscation: Luraph v15
-- Local names are inferred

local v1 = game:GetService("Players")
local v2 = game:GetService("RunService")
local tbl1 = v1.LocalPlayer
local function Arg1(a1)
  local v3 = a1.Character
  if v3 then
    local v4 = v3:FindFirstChildOfClass("Humanoid")
    if v4 then
      v4.WalkSpeed = 50
    end
  end
end
bit32.bxor(1, 2)
local v5 = tbl1.CharacterAdded:Connect(Arg1)
