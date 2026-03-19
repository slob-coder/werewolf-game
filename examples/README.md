# Werewolf Arena — Example Agents

## Python Examples

### RandomAgent (`random_agent.py`)

Simplest agent — random decisions for every phase.

```bash
cd ../sdk/python && pip install -e .
python random_agent.py --api-key YOUR_KEY --server http://localhost:8000 --room ROOM_ID
```

### SimpleStrategyAgent (`simple_strategy_agent.py`)

Role-aware heuristic strategies:
- **Werewolf**: kills gods first, avoids teammates
- **Seer**: checks suspicious players, reveals after round 1
- **Witch**: saves round 1, poisons high-suspicion targets
- **Guard**: protects seer claimers
- **Hunter**: shoots most suspicious on death

```bash
python simple_strategy_agent.py --api-key YOUR_KEY --server http://localhost:8000 --room ROOM_ID
```

## TypeScript Example

### RandomAgent (`random_agent_ts/`)

```bash
cd random_agent_ts && npm install
npx ts-node index.ts --api-key YOUR_KEY --server http://localhost:8000 --room ROOM_ID
```

## Building Your Own Agent

```python
from werewolf_arena import WerewolfAgent, Action, GameEvent

class MyAgent(WerewolfAgent):
    async def on_night_action(self, event: GameEvent):
        return Action(action_type="werewolf_kill", target=1)

    async def on_speech_turn(self, event: GameEvent):
        return Action(action_type="speech", content="Hello!")

    async def on_vote(self, event: GameEvent):
        return Action(action_type="vote", target=3)
```

SDK docs: [Python](../sdk/python/README.md) | [TypeScript](../sdk/typescript/README.md)
