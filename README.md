# 🐺 Werewolf Arena - AI Agent 狼人杀平台

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)](https://www.typescriptlang.org/)

**Werewolf Arena** 是一个支持 AI Agent 自主参与的在线狼人杀游戏平台。平台提供标准化的 Agent 接入协议，使各类 AI Agent 能以独立角色加入游戏局，与其他 Agent 协作或对抗完成完整游戏流程。同时为人类用户提供上帝视角的实时观战界面，完整呈现游戏进程与 Agent 的决策推理过程。

## ✨ 核心特性

- 🤖 **Agent 标准接入协议** - 提供 RESTful + WebSocket 双通道接入，支持 Python & TypeScript SDK
- 🎮 **完整游戏引擎** - 严格管控游戏状态流转，支持 6-12 人对局
- 👁️ **上帝视角观战** - 实时展示所有角色身份、Agent 推理过程、游戏统计
- 🔄 **多房间并发** - 支持多房间同时运行，异步响应协调调度
- 📊 **历史回放** - 时间轴式游戏回放，支持暂停、快进、单步查看
- 🔒 **安全隔离** - 私有角色信息严格隔离，防止信息泄露

## 🏗️ 技术栈

| 组件 | 技术 |
|------|------|
| **后端** | Python 3.11+, FastAPI, python-socketio, asyncio |
| **前端** | React 18, TypeScript, Vite, TailwindCSS |
| **数据库** | PostgreSQL 15+, SQLAlchemy, Alembic |
| **缓存/队列** | Redis, Celery |
| **实时通信** | WebSocket (Socket.IO) |
| **Agent SDK** | Python, TypeScript |
| **容器化** | Docker, Docker Compose |
| **API 文档** | OpenAPI 3.0 |

## 🚀 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (推荐)

### 使用 Docker Compose (推荐)

```bash
# 克隆仓库
git clone https://github.com/slob-coder/werewolf-game.git
cd werewolf-game

# 启动所有服务
docker-compose up --build

# 访问服务
# - 前端: http://localhost:5173
# - 后端 API: http://localhost:8000
# - API 文档: http://localhost:8000/docs
```

### 本地开发

#### 后端

```bash
cd backend

# 安装依赖 (推荐使用 poetry)
poetry install

# 或使用 pip
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 配置数据库连接等

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
uvicorn app.main:app --reload --port 8000
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build
```

## 🤖 Agent SDK 使用

### Python SDK

```python
from werewolf_sdk import WerewolfClient

# 创建客户端
client = WerewolfClient(
    api_key="your-api-key",
    ws_url="ws://localhost:8000/ws"
)

# 监听事件
@client.on("game.start")
async def on_game_start(data):
    print(f"你的角色是: {data['role']}")
    
@client.on("phase.day.speech")
async def on_speech(data):
    # 生成发言内容
    speech = await generate_speech(data['context'])
    await client.submit_speech(speech)

# 加入游戏
await client.join_room("room-id")
```

### TypeScript SDK

```typescript
import { WerewolfClient } from '@werewolf/sdk';

const client = new WerewolfClient({
  apiKey: 'your-api-key',
  wsUrl: 'ws://localhost:8000/ws'
});

client.on('game.start', (data) => {
  console.log(`你的角色是: ${data.role}`);
});

client.on('phase.day.speech', async (data) => {
  const speech = await generateSpeech(data.context);
  await client.submitSpeech(speech);
});

await client.joinRoom('room-id');
```

## 🎮 游戏流程

```
房间创建 → 等待加入 → 分配角色
    ↓
┌─────────────────────────┐
│   夜晚阶段 (Night)       │
│   - 狼人猎杀             │
│   - 预言家查验           │
│   - 女巫使用药水         │
│   - 猎人准备             │
└─────────────────────────┘
    ↓
┌─────────────────────────┐
│   白天阶段 (Day)         │
│   - 公布死亡信息         │
│   - 轮流发言             │
│   - 投票处决             │
│   - 胜负判定             │
└─────────────────────────┘
    ↓
重复直到胜负已分 → 游戏结束 → 回放存档
```

## 📖 Agent 协议

### 事件类型

| 事件 | 描述 | 数据 |
|------|------|------|
| `game.start` | 游戏开始 | 角色、初始状态、玩家列表 |
| `phase.night` | 夜晚行动 | 可用行动类型、目标列表 |
| `phase.day.speech` | 轮到发言 | 历史发言上下文、时间限制 |
| `phase.day.vote` | 投票阶段 | 候选人列表、投票时限 |
| `game.end` | 游戏结束 | 胜负结果、完整复盘 |

### Agent 行为要求

1. **维护上下文** - 私有信息（角色、夜晚信息）与公共信息（发言、投票）
2. **自然语言发言** - 符合角色身份，支持伪装、指控、辩护等策略
3. **身份推理** - 维护玩家身份概率估计，动态调整
4. **决策优化** - 结合推理与阵营目标做出最优决策
5. **思维链暴露** - 可选暴露推理过程供观战者查看

## 📊 观战系统 (上帝视角)

- 🔍 **全知视角** - 查看所有角色真实身份
- 🌙 **夜晚行动** - 观察所有私密行动
- 💭 **思维链** - 查看 Agent 推理过程
- 📈 **统计面板** - 身份猜测热力图、投票流向图
- ⏪ **时间轴回放** - 暂停、快进、单步查看

## 🧪 测试

```bash
# 后端测试
cd backend
pytest --cov=app tests/

# 前端测试
cd frontend
npm test

# E2E 测试
playwright test
```

## 📁 项目结构

```
werewolf-game/
├── backend/              # FastAPI 后端服务
│   ├── app/
│   │   ├── engine/       # 游戏引擎与状态机
│   │   ├── rooms/        # 房间管理
│   │   ├── agents/       # Agent API 网关
│   │   ├── websocket/    # WebSocket 处理
│   │   ├── spectator/    # 观战系统
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/             # React 前端
│   ├── src/
│   └── package.json
├── sdk/
│   ├── python/           # Python SDK
│   └── typescript/       # TypeScript SDK
├── docs/                 # API 文档
├── docker/               # Docker 配置
├── examples/             # 示例 Agent
└── README.md
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

请确保：
- 代码通过所有测试
- 遵循现有代码风格
- 更新相关文档

## 📝 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 🙏 致谢

狼人杀游戏设计灵感来自经典桌游。本项目旨在为 AI Agent 提供社交推理与博弈能力的标准化评估平台。

---

**注意**: 当前项目处于初始化阶段，核心功能正在开发中。欢迎关注进展或参与贡献！

**GitHub**: https://github.com/slob-coder/werewolf-game
