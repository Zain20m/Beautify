-- Beautified from deobfuscator output
-- Notes: client combat/input loop; Sync remote can set speed or lock flag

local Players = game:GetService("Players")
local RunService = game:GetService("RunService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local TweenService = game:GetService("TweenService")
local UserInputService = game:GetService("UserInputService")
local Debris = game:GetService("Debris")

local localPlayer = Players.LocalPlayer
local playerGui = localPlayer:WaitForChild("PlayerGui")

local remotesFolder = ReplicatedStorage:FindFirstChild("Remotes") or ReplicatedStorage:WaitForChild("Remotes")
local hitRemote = remotesFolder:FindFirstChild("Hit") or remotesFolder:WaitForChild("Hit")
local syncRemote = remotesFolder:FindFirstChild("Sync") or remotesFolder:WaitForChild("Sync")

local state = {}
for index = 1, 32 do
	state[index] = index * 3 - 1
end
state.locked = false
state.lastSwing = 0
state.tag = "x"

local function getOrSet(tableRef, key, defaultValue)
	if type(tableRef) ~= "table" then
		return nil
	end
	local value = tableRef[key]
	if value == nil then
		value = defaultValue
		tableRef[key] = value
	end
	return value
end

local function getHumanoidAndRoot(character)
	if not character then
		return
	end
	local humanoid = character:FindFirstChildOfClass("Humanoid")
	local rootPart = character:FindFirstChild("HumanoidRootPart") or character:FindFirstChild("Torso")
	if not humanoid or not rootPart then
		return
	end
	return humanoid, rootPart
end

local function swingAttack()
	local character = localPlayer.Character
	local humanoid, rootPart = getHumanoidAndRoot(character)
	if not humanoid then
		return
	end

	local look = rootPart.CFrame.LookVector
	local hitPosition = rootPart.CFrame.Position + look * state[2]
	hitRemote:FireServer(hitPosition, look, state[4] or 8)
	state.lastSwing = os.clock()
end

local function onInputBegan(input, gameProcessed)
	if state.locked then
		return
	end
	if input.UserInputType ~= Enum.UserInputType.MouseButton1 and input.KeyCode ~= Enum.KeyCode.F then
		return
	end
	if gameProcessed then
		return
	end
	if os.clock() - (state.lastSwing or 0) < 0.35 then
		return
	end
	swingAttack()
end

local function applyCharacterStats(character)
	task.spawn(function()
		local humanoid = getHumanoidAndRoot(character)
		if not humanoid then
			return
		end
		humanoid.WalkSpeed = getOrSet(state, "spd", 16)
		humanoid.JumpPower = getOrSet(state, "jmp", 50)
	end)
end

local characterAddedConn = localPlayer.CharacterAdded:Connect(function(character)
	applyCharacterStats(character)
	local humanoid = character:WaitForChild("Humanoid", 5)
	if humanoid then
		humanoid.Died:Connect(function()
			state.locked = false
		end)
	end
end)

if localPlayer.Character then
	applyCharacterStats(localPlayer.Character)
end

local inputBeganConn = UserInputService.InputBegan:Connect(onInputBegan)

local renderConn = RunService.RenderStepped:Connect(function(deltaTime)
	local character = localPlayer.Character
	if not character then
		return
	end
	local humanoid, rootPart = getHumanoidAndRoot(character)
	if not humanoid or humanoid.Health <= 0 then
		return
	end
	if state.locked and rootPart then
		rootPart.CFrame = rootPart.CFrame * CFrame.new(0, 0, -deltaTime * 8)
	end
end)

local syncConn = syncRemote.OnClientEvent:Connect(function(action, value)
	if action == "spd" then
		state.spd = tonumber(value) or state.spd
		local character = localPlayer.Character
		if character then
			local humanoid = getHumanoidAndRoot(character)
			if humanoid then
				humanoid.WalkSpeed = state.spd
			end
		end
	elseif action == "lock" then
		state.locked = value and true or false
	end
end)

local function requestBoot()
	return syncRemote:InvokeServer("boot", localPlayer.UserId)
end

local bootData = requestBoot()
if type(bootData) == "table" then
	for key, value in pairs(bootData) do
		state[key] = value
	end
end
