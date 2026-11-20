-- Beautified from deobfuscator output
-- Notes: combat client stub; speed may come from DataFunction "load"

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local UserInputService = game:GetService("UserInputService")

local localPlayer = Players.LocalPlayer
local playerGui = localPlayer:WaitForChild("PlayerGui")

local remotes = ReplicatedStorage:WaitForChild("Remotes")
local combatEvent = remotes:WaitForChild("CombatEvent")
local dataFunction = remotes:WaitForChild("DataFunction")

local DEFAULT_RANGE = 16
local walkSpeed = 50

local config = {
	[1] = true,
	[2] = DEFAULT_RANGE,
	boost = 1.25,
}

local function setupCharacter(character)
	if not character then
		return
	end

	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local rootPart = character:FindFirstChild("HumanoidRootPart")
	if humanoid and rootPart then
		humanoid.WalkSpeed = walkSpeed * (config.boost or 1)
		humanoid.JumpPower = 50
		return humanoid, rootPart
	end

	return nil, nil
end

local function fireCombat(actionName, actionId)
	local character = localPlayer.Character
	if not character then
		return
	end

	local humanoid, rootPart = setupCharacter(character)
	if not humanoid or not rootPart then
		return
	end

	combatEvent:FireServer(actionName, actionId, rootPart.Position)
end

local function onInputBegan(input)
	if input.KeyCode == Enum.KeyCode.Q then
		fireCombat("ability", 1)
	elseif input.KeyCode == Enum.KeyCode.E then
		fireCombat("ability", 2)
	end
end

local characterAddedConn = localPlayer.CharacterAdded:Connect(function(character)
	task.wait(0.1)
	setupCharacter(character)
end)

if localPlayer.Character then
	setupCharacter(localPlayer.Character)
end

local inputBeganConn = UserInputService.InputBegan:Connect(onInputBegan)

local heartbeatConn = RunService.Heartbeat:Connect(function()
	local character = localPlayer.Character
	if not character then
		return
	end

	local humanoid = character:FindFirstChildOfClass("Humanoid")
	if humanoid and humanoid.Health <= 0 then
		return
	end
end)

local loadedData = dataFunction:InvokeServer("load")
if type(loadedData) == "table" and loadedData.speed then
	walkSpeed = loadedData.speed
end
