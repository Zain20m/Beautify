-- Valid generic Luau functions with typed locals and loop bindings.
local function identity<T>(value: T): T
    return value
end

local function copyAll<T>(items: {T}): {T}
    local result: {T} = {}
    for _, item in ipairs(items) do
        table.insert(result, identity(item))
    end
    return result
end

return copyAll({ 1, 2, 3 })
