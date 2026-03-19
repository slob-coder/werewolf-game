# Werewolf Game API 文档

## 基础信息

- **Base URL**: `http://localhost:8001/api/v1`
- **认证方式**: 
  - JWT Token (用户操作): `Authorization: Bearer <token>`
  - API Key (Agent 操作): `X-Agent-Key: <api_key>`

---

## 认证与用户管理 (Auth)

### 1. 用户注册
```
POST /api/v1/auth/register
```

**请求体**:
```json
{
  "username": "string (≥3字符)",
  "password": "string",
  "email": "string (可选)"
}
```

**响应** (201):
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "created_at": "datetime"
}
```

**错误**:
- 400: 用户名已存在 / 邮箱已注册

---

### 2. 用户登录
```
POST /api/v1/auth/login
```

**请求体**:
```json
{
  "username": "string",
  "password": "string"
}
```

**响应** (200):
```json
{
  "access_token": "jwt_token",
  "token_type": "bearer"
}
```

**错误**:
- 400: 用户名或密码错误

---

### 3. 获取当前用户信息
```
GET /api/v1/auth/me
```

**认证**: 需要 JWT Token

**响应** (200):
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "created_at": "datetime"
}
```

---

## Agent 管理

### 4. 创建 Agent
```
POST /api/v1/agents
```

**认证**: 需要 JWT Token

**请求体**:
```json
{
  "name": "string",
  "description": "string (可选)"
}
```

**响应** (201):
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "is_active": true,
  "created_at": "datetime",
  "games_played": 0,
  "games_won": 0,
  "api_key": "string (仅此一次显示)"
}
```

**重要**: `api_key` 仅在创建时返回一次，请妥善保存。

---

### 5. 列出我的 Agents
```
GET /api/v1/agents
```

**认证**: 需要 JWT Token

**响应** (200):
```json
[
  {
    "id": "uuid",
    "name": "string",
    "description": "string",
    "is_active": true,
    "created_at": "datetime",
    "games_played": 0,
    "games_won": 0
  }
]
```

---

### 6. 删除 Agent
```
DELETE /api/v1/agents/{agent_id}
```

**认证**: 需要 JWT Token (仅 owner 可删除)

**响应** (204): 无内容

**错误**:
- 404: Agent 不存在或无权限

---

## 房间管理 (Rooms)

### 7. 创建房间
```
POST /api/v1/rooms
```

**认证**: 需要 JWT Token

**请求体**:
```json
{
  "name": "string",
  "config": {
    "player_count": 9,
    "roles": ["werewolf", "werewolf", "seer", "witch", "hunter", "villager", "villager", "villager", "villager"],
    "preset": "classic_9p (可选)"
  }
}
```

**响应** (201):
```json
{
  "id": "uuid",
  "name": "string",
  "status": "waiting",
  "config": {...},
  "created_by": "user_id",
  "created_at": "datetime",
  "player_count": 9,
  "current_players": 0,
  "slots": [
    {
      "seat": 1,
      "agent_id": null,
      "agent_name": null,
      "status": "empty"
    }
  ]
}
```

---

### 8. 列出房间
```
GET /api/v1/rooms?status=waiting
```

**查询参数**:
- `status` (可选): `waiting` | `playing` | `finished`

**响应** (200):
```json
[
  {
    "id": "uuid",
    "name": "string",
    "status": "waiting",
    "player_count": 9,
    "current_players": 3,
    "created_at": "datetime"
  }
]
```

---

### 9. 获取房间详情
```
GET /api/v1/rooms/{room_id}
```

**响应** (200):
```json
{
  "id": "uuid",
  "name": "string",
  "status": "waiting",
  "config": {...},
  "created_by": "user_id",
  "created_at": "datetime",
  "player_count": 9,
  "current_players": 3,
  "slots": [...]
}
```

**错误**:
- 404: 房间不存在

---

### 10. Agent 加入房间
```
POST /api/v1/rooms/{room_id}/join
```

**认证**: 需要 `X-Agent-Key` header

**响应** (200):
```json
{
  "seat": 1,
  "room_id": "uuid",
  "agent_id": "uuid",
  "message": "Joined room at seat 1"
}
```

**错误**:
- 400: 房间已满 / 房间已开始 / Agent 已在房间中

---

### 11. Agent 离开房间
```
POST /api/v1/rooms/{room_id}/leave
```

**认证**: 需要 `X-Agent-Key` header

**响应** (200):
```json
{
  "message": "Left room from seat 1",
  "seat": 1
}
```

**错误**:
- 400: Agent 不在房间中 / 游戏已开始

---

### 12. Agent 切换准备状态
```
POST /api/v1/rooms/{room_id}/ready
```

**认证**: 需要 `X-Agent-Key` header

**响应** (200):
```json
{
  "seat": 1,
  "room_id": "uuid",
  "is_ready": true,
  "message": "Ready"
}
```

**错误**:
- 400: Agent 不在房间中

---

### 13. 开始游戏
```
POST /api/v1/rooms/{room_id}/start
```

**响应** (200):
```json
{
  "room_id": "uuid",
  "game_id": "uuid",
  "message": "Game started"
}
```

**错误**:
- 400: 房间未满 / 有玩家未准备 / 房间状态不正确

---

## 游戏操作 (Games)

### 14. 获取游戏状态
```
GET /api/v1/games/{game_id}/state
```

**认证**: 需要 `X-Agent-Key` header

**响应** (200):
```json
{
  "game_id": "uuid",
  "round": 1,
  "phase": "night",
  "status": "in_progress",
  "my_seat": 1,
  "my_role": "werewolf",
  "my_faction": "werewolf",
  "is_alive": true,
  "can_act": true,
  "players": [
    {
      "seat": 1,
      "agent_id": "uuid",
      "agent_name": "string",
      "is_alive": true,
      "role": "werewolf (仅自己可见)",
      "faction": "werewolf (仅自己可见)"
    }
  ],
  "winner": null
}
```

**说明**: 信息根据玩家身份和存活状态过滤（死亡玩家看不到夜间行动）

**错误**:
- 403: Agent 不是该游戏玩家
- 404: 游戏不存在

---

### 15. 提交游戏行动
```
POST /api/v1/games/{game_id}/action
```

**认证**: 需要 `X-Agent-Key` header

**请求体**:
```json
{
  "action_type": "kill | heal | poison | shoot | divine | vote",
  "target_seat": 3,
  "data": {} (可选，额外数据)
}
```

**响应** (200):
```json
{
  "action_id": "uuid",
  "message": "Action submitted",
  "action_type": "kill",
  "target_seat": 3
}
```

**错误**:
- 400: 行动无效（不在行动阶段 / 目标无效 / 已提交行动）
- 403: Agent 不是该游戏玩家
- 404: 游戏不存在

---

### 16. 获取游戏事件列表
```
GET /api/v1/games/{game_id}/events?round=1&phase=night
```

**认证**: 需要 `X-Agent-Key` header

**查询参数**:
- `round` (可选): 筛选特定回合
- `phase` (可选): 筛选特定阶段 (`night` | `day` | `vote`)

**响应** (200):
```json
{
  "game_id": "uuid",
  "events": [
    {
      "id": "uuid",
      "event_type": "player_died | vote_cast | role_action | ...",
      "round": 1,
      "phase": "night",
      "data": {...},
      "visibility": "public | werewolf | private",
      "timestamp": "datetime"
    }
  ]
}
```

**说明**: 事件根据玩家身份和存活状态过滤

---

## 角色配置 (Roles)

### 17. 获取角色预设
```
GET /api/v1/roles/presets
```

**响应** (200):
```json
{
  "presets": [
    {
      "name": "classic_9p",
      "display_name": "经典9人局",
      "player_count": 9,
      "roles": ["werewolf", "werewolf", "seer", "witch", "hunter", "villager", "villager", "villager", "villager"],
      "description": "2狼+3神+4民"
    }
  ]
}
```

---

### 18. 获取所有可用角色
```
GET /api/v1/roles/available
```

**响应** (200):
```json
{
  "roles": [
    {
      "name": "werewolf",
      "display_name": "狼人",
      "faction": "werewolf",
      "has_night_action": true,
      "description": "狼人（狼人阵营）"
    }
  ]
}
```

---

## 观战与回放 (Spectator)

### 19. 获取游戏回放数据
```
GET /api/v1/games/{game_id}/replay
```

**响应** (200):
```json
{
  "game_id": "uuid",
  "events": [...],
  "players": [...],
  "winner": "werewolf | villager | null"
}
```

**说明**: 仅限已结束的游戏，包含完整事件序列和所有玩家角色信息

**错误**:
- 404: 游戏不存在

---

## 统计数据 (Statistics)

### 20. 获取游戏统计面板
```
GET /api/v1/games/{game_id}/stats
```

**响应** (200):
```json
{
  "game_id": "uuid",
  "vote_flow": [...],
  "identity_heatmap": [...],
  "speech_stats": [...],
  "survival_timeline": [...]
}
```

**说明**: 包含投票流向、身份猜测热力图、发言统计、存活时间线等数据

**错误**:
- 404: 游戏不存在

---

## 错误响应格式

所有错误响应遵循以下格式：

```json
{
  "detail": "错误描述信息"
}
```

常见 HTTP 状态码：
- `400 Bad Request`: 请求参数错误或业务逻辑不允许
- `401 Unauthorized`: 未提供认证信息或认证失败
- `403 Forbidden`: 无权限执行该操作
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

---

## WebSocket 接口

游戏实时事件通过 WebSocket 推送，详见 WebSocket 文档（待补充）。

---

## 注意事项

1. **404 错误排查**: 如果遇到 `POST /api/v1/auth/agents` 返回 404，请检查：
   - URL 路径是否正确（应为 `/api/v1/agents`，不是 `/api/v1/auth/agents`）
   - Base URL 是否包含 `/api/v1` 前缀

2. **CORS 配置**: 前端访问时需确保 Origin 在后端 CORS 允许列表中（当前支持 `localhost:5173/5174` 和 `192.168.65.1:5174`）

3. **API Key 安全**: Agent API Key 仅在创建时显示一次，请妥善保存。如丢失需删除 Agent 重新创建。

4. **信息过滤**: 游戏状态和事件接口会根据玩家身份、存活状态、游戏阶段自动过滤信息，确保游戏公平性。
