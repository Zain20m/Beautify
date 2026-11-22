--!strict
type PlayerRecord = {
    name: string,
    userId: number,
}

local function fn3<T>(
    items: {T},
    predicate: (T) -> boolean
): {T}
    local result: {T} = {}
    for _, v1 in ipairs(items) do
        if predicate(v1) then
            table.insert(result, v1)
        end
    end
    return result
end

local values = { 1, 2, 3 }
repeat
    local v2 = table.remove(values)
until v2 == nil

return fn3(values, function(item)
    return item ~= nil
end)
