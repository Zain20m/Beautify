-- Beautified from deobfuscator output

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")

local localPlayer = Players.LocalPlayer

local function onCharacterAdded(character)
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if humanoid then
		humanoid.WalkSpeed = 50
	end
end

local characterAddedConn = localPlayer.CharacterAdded:Connect(onCharacterAdded)
