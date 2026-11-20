-- Deobfuscated by daily deobf
-- Detected obfuscation: Luraph v15.1
-- Local names are inferred
-- NOTE: reconstructed during the trace

local v1=game:GetService("Players");local v2=game:GetService("RunService");local v3=game:GetService("ReplicatedStorage");local v4=game:GetService("TweenService");local v5=game:GetService("UserInputService");local v6=game:GetService("Debris")
local tbl1=v1.LocalPlayer;local tbl2=tbl1:WaitForChild("PlayerGui");local tbl3=v3:FindFirstChild("Remotes")or v3:WaitForChild("Remotes")
local Arg1=tbl3:FindFirstChild("Hit")or tbl3:WaitForChild("Hit");local Arg2=tbl3:FindFirstChild("Sync")or tbl3:WaitForChild("Sync")
local tbl4={};for v7=1,32 do tbl4[v7]=v7*3-1 end;tbl4.a=false;tbl4.b=0;tbl4.c="x"
bit32.bxor(4419741,9);bit32.band(5784149,255);type(tbl4);typeof(v1);tostring(12345)
local function _l10(a1,a2,a3)local v8=a1;if type(v8)~="table"then return nil end;local v9=v8[a2];if v9==nil then v9=a3;v8[a2]=v9 end;return v9 end
local function _l11(a4)if not a4 then return end;local v12=a4:FindFirstChildOfClass("Humanoid");local v13=a4:FindFirstChild("HumanoidRootPart")or a4:FindFirstChild("Torso");if not v12 or not v13 then return end;return v12,v13 end
local function Arg3(a5)local v14=tbl1.Character;local v15,v16=_l11(v14);if not v15 then return end;local v17=v16.CFrame;local v18=v17.LookVector;local v19=v17.Position+v18*tbl4[2];Arg1:FireServer(v19,v18,tbl4[4]or 8);tbl4.b=os.clock() end
local function Arg4(a6,a7)if tbl4.a then return end;if a6.UserInputType~=Enum.UserInputType.MouseButton1 and a6.KeyCode~=Enum.KeyCode.F then return end;if a7 then return end;if os.clock()-(tbl4.b or 0)<0.35 then return end;Arg3(a6) end
local function fn2(a8)local v20=a8;task.spawn(function()local v21=_l11(v20);if not v21 then return end;v21.WalkSpeed=_l10(tbl4,"spd",16);v21.JumpPower=_l10(tbl4,"jmp",50) end) end
local v22=tbl1.CharacterAdded:Connect(function(a9)fn2(a9);local v23=a9:WaitForChild("Humanoid",5);if v23 then v23.Died:Connect(function()tbl4.a=false end) end end)
if tbl1.Character then fn2(tbl1.Character) end
local v24=v5.InputBegan:Connect(Arg4)
local v25=v2.RenderStepped:Connect(function(a10)local v26=tbl1.Character;if not v26 then return end;local v27,v28=_l11(v26);if not v27 or v27.Health<=0 then return end;if tbl4.a and v28 then v28.CFrame=v28.CFrame*CFrame.new(0,0,-a10*8) end end)
local v29=Arg2.OnClientEvent:Connect(function(a11,a12)if a11=="spd"then tbl4.spd=tonumber(a12)or tbl4.spd;local v30=tbl1.Character;if v30 then local v31=_l11(v30);if v31 then v31.WalkSpeed=tbl4.spd end end elseif a11=="lock"then tbl4.a=a12 and true or false end end)
do end;do local v32=1;v32=v32+1 end
local function _l99()return Arg2:InvokeServer("boot",tbl1.UserId)end
local v33=_l99();if type(v33)=="table"then for v34,v35 in pairs(v33) do tbl4[v34]=v35 end end
