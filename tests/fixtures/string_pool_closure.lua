-- Representative string-pool and nested-closure output.
local tbl1 = {
    "Players",
    "LocalPlayer",
    "Character",
    "HumanoidRootPart",
}

local function fn2(v1)
    local v2 = (v1 % #tbl1) + 1
    return tbl1[v2]
end

local v3 = {
    decode = fn2,
    read = function(v4)
        local v5 = fn2(v4)
        return function()
            return v5
        end
    end,
}

return v3.read(2)()
