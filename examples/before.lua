-- Deobfuscated by daily deobf
-- Detected obfuscation: Luraph v15.1
-- Local names are inferred
-- NOTE: reconstructed during the trace
-- run status: finished
-- 128 statements recorded in 2.40s

local v1 = game:GetService("Players")
local v2 = game:GetService("RunService")
local v3 = game:GetService("ReplicatedStorage")
local v4 = game:GetService("UserInputService")
local tbl1 = v1.LocalPlayer
local tbl2 = tbl1:WaitForChild("PlayerGui")
local tbl3 = v3:WaitForChild("Remotes")
local Arg1 = tbl3:WaitForChild("CombatEvent")
local Arg2 = tbl3:WaitForChild("DataFunction")
local v5 = 16
local v6 = 50
local tbl4 = {
    [1] = true,
    [2] = v5,
    ["boost"] = 1.25,
}
bit32.bxor(13680313, 7)
type(123)
local function _l173(a1)
    local v7 = a1
    if not v7 then
        return
    end
    local v8 = v7:FindFirstChildOfClass("Humanoid")
    local v9 = v7:FindFirstChild("HumanoidRootPart")
    if v8 and v9 then
        v8.WalkSpeed = v6 * (tbl4["boost"] or 1)
        v8.JumpPower = 50
        return v8, v9
    end
    return nil, nil
end
local function Arg3(a2, a3)
    local v10 = tbl1.Character
    if not v10 then
        return
    end
    local v11, v12 = _l173(v10)
    if not v11 or not v12 then
        return
    end
    Arg1:FireServer(a2, a3, v12.Position)
end
local function fn1(a4)
    local v13 = a4.KeyCode
    if v13 == Enum.KeyCode.Q then
        Arg3("ability", 1)
    elseif v13 == Enum.KeyCode.E then
        Arg3("ability", 2)
    end
end
local v14 = tbl1.CharacterAdded:Connect(function(a5)
    task.wait(0.1)
    _l173(a5)
end)
if tbl1.Character then
    _l173(tbl1.Character)
end
local v15 = v4.InputBegan:Connect(fn1)
local v16 = v2.Heartbeat:Connect(function(a6)
    local v17 = tbl1.Character
    if not v17 then
        return
    end
    local v18 = v17:FindFirstChildOfClass("Humanoid")
    if v18 and v18.Health <= 0 then
        return
    end
end)
do end
local v19 = Arg2:InvokeServer("load")
if type(v19) == "table" and v19.speed then
    v6 = v19.speed
end
