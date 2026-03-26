# Werewolf Arena - Agent Observability API 设计方案

## 概述

为 werewolf-openclaw-skill 提供监控数据上报能力，用于问题定位和智能体行为分析。

---

## 1. 数据模型

### 1.1 新建 AgentReport 表

**文件**: `backend/app/models/agent_report.py`

```python
class AgentReport(Base):
    """智能体上报数据"""
    __tablename__ = "agent_reports"

    id: Mapped[str] = mapped_column(UUID, primary_key=True, default=uuid4)
    agent_id: Mapped[str] = mapped_column(UUID, ForeignKey("agents.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # exception | event | health
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    
    # 会话上下文
    room_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    game_id: Mapped[str | None] = mapped_column(UUID, nullable=True)
    
    # 上报内容 (JSON)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    # 元数据
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # 关联
    agent = relationship("Agent", back_populates="reports")
```

### 1.2 修改 Agent 模型

**文件**: `backend/app/models/agent.py` (添加关系)

```python
# 在 Agent 类中添加
reports = relationship("AgentReport", back_populates="agent", lazy="dynamic")
```

---

## 2. API 设计

### 2.1 上报接口

**路由**: `POST /api/v1/agent/reports`

**认证**: `X-Agent-Key: {api_key}`

**请求体**:
```json
{
  "agent_id": "werewolf-bridge",
  "reports": [
    {
      "agent_id": "werewolf-bridge",
      "report_type": "exception",
      "timestamp": "2026-03-27T00:10:00Z",
      "session": {
        "room_id": "abc123",
        "game_id": "game-456"
      },
      "payload": {
        "error_type": "ConnectionError",
        "error_message": "Failed to connect to server",
        "stacktrace": "Traceback (...)",
        "context": {"operation": "join_room"}
      }
    }
  ]
}
```

**响应**:
```json
{
  "status": "ok",
  "received": 1,
  "stored": 1
}
```

### 2.2 查询接口

**路由**: `GET /api/v1/agent/reports`

**认证**: JWT Bearer Token (用户登录)

**查询参数**:
- `agent_id`: 过滤特定智能体
- `report_type`: 过滤类型 (exception | event | health)
- `room_id`: 过滤房间
- `game_id`: 过滤游戏
- `from`: 开始时间
- `to`: 结束时间
- `limit`: 返回数量 (默认 100, 最大 500)

**响应**:
```json
{
  "total": 42,
  "reports": [
    {
      "id": "report-uuid",
      "agent_id": "agent-uuid",
      "report_type": "exception",
      "timestamp": "2026-03-27T00:10:00Z",
      "room_id": "abc123",
      "game_id": "game-456",
      "payload": {...},
      "created_at": "2026-03-27T00:10:05Z"
    }
  ]
}
```

### 2.3 统计接口

**路由**: `GET /api/v1/agent/reports/stats`

**认证**: JWT Bearer Token

**响应**:
```json
{
  "total_reports": 1234,
  "by_type": {
    "exception": 456,
    "event": 700,
    "health": 78
  },
  "by_agent": {
    "werewolf-bridge": 800,
    "other-agent": 434
  },
  "recent_errors": 23
}
```

---

## 3. 数据库迁移

**文件**: `backend/alembic/versions/xxx_add_agent_reports.py`

```python
def upgrade():
    op.create_table(
        'agent_reports',
        sa.Column('id', postgresql.UUID, primary_key=True),
        sa.Column('agent_id', postgresql.UUID, sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('report_type', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime, nullable=False),
        sa.Column('room_id', sa.String(100), nullable=True),
        sa.Column('game_id', postgresql.UUID, nullable=True),
        sa.Column('payload', postgresql.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )
    
    # 索引
    op.create_index('ix_agent_reports_agent_id', 'agent_reports', ['agent_id'])
    op.create_index('ix_agent_reports_timestamp', 'agent_reports', ['timestamp'])
    op.create_index('ix_agent_reports_type', 'agent_reports', ['report_type'])
    op.create_index('ix_agent_reports_room_id', 'agent_reports', ['room_id'])

def downgrade():
    op.drop_table('agent_reports')
```

---

## 4. Schema 定义

**文件**: `backend/app/schemas/report.py`

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional

class ReportPayload(BaseModel):
    agent_id: str
    report_type: str  # exception | event | health
    timestamp: str
    session: dict[str, Any] = {}
    payload: dict[str, Any]

class ReportsRequest(BaseModel):
    agent_id: str
    reports: list[ReportPayload]

class ReportsResponse(BaseModel):
    status: str
    received: int
    stored: int

class ReportResponse(BaseModel):
    id: str
    agent_id: str
    report_type: str
    timestamp: datetime
    room_id: Optional[str]
    game_id: Optional[str]
    payload: dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReportsListResponse(BaseModel):
    total: int
    reports: list[ReportResponse]

class ReportsStatsResponse(BaseModel):
    total_reports: int
    by_type: dict[str, int]
    by_agent: dict[str, int]
    recent_errors: int  # 最近 24 小时
```

---

## 5. 文件清单

需要新增/修改的文件：

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/agent_report.py` | 新增 | 数据模型 |
| `backend/app/models/__init__.py` | 修改 | 导入新模型 |
| `backend/app/models/agent.py` | 修改 | 添加 reports 关系 |
| `backend/app/schemas/report.py` | 新增 | 请求/响应 Schema |
| `backend/app/schemas/__init__.py` | 修改 | 导入新 Schema |
| `backend/app/api/v1/reports.py` | 新增 | API 路由 |
| `backend/app/main.py` | 修改 | 注册路由 |
| `backend/alembic/versions/xxx_add_agent_reports.py` | 新增 | 数据库迁移 |

---

## 6. 可选增强

### 6.1 告警规则（未来）

```python
# 检测到连续断开连接时触发告警
if disconnect_count > 3 in 5 minutes:
    send_alert_to_owner(agent.owner_id, "Agent connection unstable")
```

### 6.2 自动清理

```python
# 定期清理 30 天前的上报数据
@scheduler.scheduled_job('cron', hour=3)
async def cleanup_old_reports():
    await db.execute(
        delete(AgentReport).where(
            AgentReport.created_at < datetime.utcnow() - timedelta(days=30)
        )
    )
```

### 6.3 导出功能

```python
# 导出某个游戏的所有上报数据用于分析
GET /api/v1/agent/reports/export?game_id=xxx&format=json
```

---

## 7. 安全考虑

1. **认证**: 上报使用 X-Agent-Key，查询使用 JWT
2. **授权**: 只能查询自己拥有的 Agent 的上报
3. **限流**: Agent 上报接口限流 100 req/min
4. **敏感信息**: 客户端已脱敏，服务端不额外处理

---

## 确认事项

请确认以下内容：

1. ✅ 数据模型设计是否满足需求？
2. ✅ API 设计是否合理？
3. ✅ 是否需要调整字段或添加新功能？
4. ✅ 数据保留策略（建议 30 天）是否合适？
5. ✅ 是否需要前端界面查看上报数据？

确认后我将开始实现。
