-- Representative register-style decompiler output.
local t_1 = game:GetService("Players")
local v2 = t_1.LocalPlayer
local tbl3 = {}

local function fn4(a1)
    local v5 = a1.Character
    if v5 == nil then
        return nil
    end

    local p6 = v5:FindFirstChildOfClass("Humanoid")
    if p6 and p6.Health > 0 then
        table.insert(tbl3, a1.Name)
    end

    return p6
end

return fn4(v2)
