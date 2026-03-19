"""RandomAgent — makes random decisions for every phase.

Usage:
    python random_agent.py --api-key YOUR_KEY --server http://localhost:8000 --room ROOM_ID
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
from typing import Optional, List

from werewolf_arena import Action, GameEvent, WerewolfAgent

logger = logging.getLogger(__name__)

SPEECH_TEMPLATES = [
    "I think seat {target} is suspicious.",
    "I'm just a villager, I have no special information.",
    "Let's focus on who hasn't spoken much.",
    "I noticed seat {target} has been very quiet.",
    "I believe we should vote out seat {target}.",
    "I don't have strong opinions yet, let's hear from everyone.",
    "Something about seat {target}'s behavior seems off to me.",
    "I'm going to trust the group's judgment on this one.",
    "We need to be careful and not rush to conclusions.",
    "I have a good feeling about the remaining players... mostly.",
]


class RandomAgent(WerewolfAgent):
    """Agent that makes completely random decisions."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.my_role: str = ""
        self.my_seat: int = 0
        self.alive_players: List[int] = []
        self.dead_players: List[int] = []

    async def on_game_start(self, event: GameEvent) -> None:
        self.my_role = event.data.get("your_role", "unknown")
        self.my_seat = event.data.get("your_seat", 0)
        players = event.data.get("players", [])
        self.alive_players = [p["seat"] for p in players if p.get("status") != "dead"]
        logger.info("RandomAgent: I am %s at seat %d (%d players)",
                     self.my_role, self.my_seat, len(self.alive_players))

    async def on_night_action(self, event: GameEvent) -> Optional[Action]:
        actions = event.data.get("available_actions", [])
        if not actions:
            return None
        action_info = actions[0]
        action_type = action_info["action_type"]
        targets = action_info.get("targets", [])
        if not targets:
            return Action(action_type=action_type)
        target = random.choice(targets)
        logger.info("RandomAgent: %s -> seat %d", action_type, target)
        return Action(action_type=action_type, target=target)

    async def on_speech_turn(self, event: GameEvent) -> Optional[Action]:
        others = [s for s in self.alive_players if s != self.my_seat]
        target = random.choice(others) if others else 1
        template = random.choice(SPEECH_TEMPLATES)
        speech = template.format(target=target)
        return Action(action_type="speech", content=speech)

    async def on_vote(self, event: GameEvent) -> Optional[Action]:
        candidates = event.data.get("candidates", [])
        if not candidates:
            return Action(action_type="vote_abstain")
        if random.random() < 0.1 and event.data.get("allow_abstain", True):
            return Action(action_type="vote_abstain")
        return Action(action_type="vote", target=random.choice(candidates))

    async def on_game_end(self, event: GameEvent) -> None:
        logger.info("RandomAgent: Game over! Winner: %s", event.data.get("winner"))

    async def on_player_death(self, data: dict) -> None:
        seat = data.get("seat")
        if seat and seat in self.alive_players:
            self.alive_players.remove(seat)
            self.dead_players.append(seat)


def main() -> None:
    parser = argparse.ArgumentParser(description="RandomAgent for Werewolf Arena")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--room", required=True)
    parser.add_argument("--game-id", default=None)
    parser.add_argument("--name", default="RandomAgent")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    async def run():
        agent = RandomAgent(api_key=args.api_key, server_url=args.server, agent_name=args.name)
        await agent.join_room(args.room)
        if args.game_id:
            agent.set_game_id(args.game_id)
        await agent.run_async()

    asyncio.run(run())


if __name__ == "__main__":
    main()
