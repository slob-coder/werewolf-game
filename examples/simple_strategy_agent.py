"""SimpleStrategyAgent — role-aware heuristic strategy agent.

Strategies:
- Werewolf: kill gods first, avoid teammates
- Seer: check suspicious players, reveal after round 1
- Witch: save round 1, poison high-suspicion targets
- Guard: protect seer claimers
- Hunter: shoot most suspicious on death
- Villager: vote by suspicion score

Usage:
    python simple_strategy_agent.py --api-key KEY --server URL --room ROOM_ID
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import random
from collections import defaultdict
from typing import Optional, List, Dict

from werewolf_arena import Action, GameEvent, WerewolfAgent

logger = logging.getLogger(__name__)


class SimpleStrategyAgent(WerewolfAgent):
    """Agent with basic role-aware strategies."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.my_role: str = ""
        self.my_seat: int = 0
        self.my_faction: str = ""
        self.alive_seats: List[int] = []
        self.dead_seats: List[int] = []
        self.teammates: List[int] = []
        self.current_round: int = 0
        self.speeches: List[dict] = []
        self.suspicion: Dict[int, float] = defaultdict(float)
        self.seer_results: Dict[int, str] = {}
        self.witch_has_save: bool = True
        self.witch_has_poison: bool = True
        self.guard_last_target: Optional[int] = None
        self.claimed_seer: List[int] = []

    async def on_game_start(self, event: GameEvent) -> None:
        self.my_role = event.data.get("your_role", "villager")
        self.my_seat = event.data.get("your_seat", 0)
        self.my_faction = event.data.get("your_faction", "villager")
        players = event.data.get("players", [])
        self.alive_seats = [p["seat"] for p in players]
        if self.my_role == "werewolf":
            self.teammates = [t["seat"] for t in event.data.get("teammates", [])]
        logger.info("SimpleStrategy: I am %s (seat %d)", self.my_role, self.my_seat)

    async def on_night_action(self, event: GameEvent) -> Optional[Action]:
        self.current_round = event.data.get("round", self.current_round)
        actions = event.data.get("available_actions", [])
        if not actions:
            return None
        a = actions[0]
        at = a["action_type"]
        targets = a.get("targets", [])

        if at == "werewolf_kill":
            return self._werewolf_kill(targets)
        elif at == "seer_check":
            return self._seer_check(targets)
        elif at in ("witch_save", "witch_poison", "witch_skip"):
            return self._witch(event.data, targets)
        elif at == "guard_protect":
            return self._guard(targets)
        elif at == "hunter_shoot":
            return self._hunter(targets)
        else:
            return Action(action_type=at, target=random.choice(targets) if targets else None)

    async def on_speech_turn(self, event: GameEvent) -> Optional[Action]:
        for s in event.data.get("previous_speeches", []):
            self._analyze_speech(s)
        return Action(action_type="speech", content=self._gen_speech())

    async def on_vote(self, event: GameEvent) -> Optional[Action]:
        candidates = event.data.get("candidates", [])
        if not candidates:
            return Action(action_type="vote_abstain")
        target = self._pick_vote(candidates)
        return Action(action_type="vote", target=target)

    async def on_game_end(self, event: GameEvent) -> None:
        winner = event.data.get("winner", "unknown")
        logger.info("SimpleStrategy: Game over! Winner: %s", winner)

    async def on_player_speech(self, data: dict) -> None:
        self.speeches.append(data)
        self._analyze_speech(data)

    async def on_player_death(self, data: dict) -> None:
        seat = data.get("seat")
        if seat and seat in self.alive_seats:
            self.alive_seats.remove(seat)
            self.dead_seats.append(seat)

    # -- role strategies --

    def _werewolf_kill(self, targets: List[int]) -> Action:
        valid = [t for t in targets if t not in self.teammates] or targets
        seer = [t for t in valid if t in self.claimed_seer]
        if seer:
            return Action(action_type="werewolf_kill", target=random.choice(seer))
        target = sorted(valid, key=lambda s: self.suspicion.get(s, 0))[0]
        return Action(action_type="werewolf_kill", target=target)

    def _seer_check(self, targets: List[int]) -> Action:
        unchecked = [t for t in targets if t not in self.seer_results] or targets
        target = sorted(unchecked, key=lambda s: self.suspicion.get(s, 0), reverse=True)[0]
        return Action(action_type="seer_check", target=target)

    def _witch(self, data: dict, targets: List[int]) -> Action:
        if self.witch_has_save and data.get("killed_seat") and self.current_round <= 1:
            self.witch_has_save = False
            return Action(action_type="witch_save")
        if self.witch_has_poison and targets:
            sus = [t for t in targets if self.suspicion.get(t, 0) > 2.0]
            if sus:
                self.witch_has_poison = False
                return Action(action_type="witch_poison", target=max(sus, key=lambda s: self.suspicion[s]))
        return Action(action_type="witch_skip")

    def _guard(self, targets: List[int]) -> Action:
        valid = [t for t in targets if t != self.guard_last_target] or targets
        seer = [t for t in valid if t in self.claimed_seer]
        target = random.choice(seer) if seer else random.choice([t for t in valid if t != self.my_seat] or valid)
        self.guard_last_target = target
        return Action(action_type="guard_protect", target=target)

    def _hunter(self, targets: List[int]) -> Action:
        if not targets:
            return Action(action_type="hunter_skip")
        return Action(action_type="hunter_shoot", target=max(targets, key=lambda s: self.suspicion.get(s, 0)))

    # -- speech --

    def _gen_speech(self) -> str:
        if self.my_role == "seer" and self.seer_results and self.current_round >= 1:
            seat, result = list(self.seer_results.items())[-1]
            if result == "bad":
                return f"I am the Seer. Seat {seat} is a WEREWOLF!"
            return f"I am the Seer. Seat {seat} is good."
        if self.my_role == "werewolf":
            others = [s for s in self.alive_seats if s != self.my_seat and s not in self.teammates]
            if others:
                return f"I think seat {random.choice(others)} is suspicious."
        alive_others = [s for s in self.alive_seats if s != self.my_seat]
        if alive_others:
            most_sus = max(alive_others, key=lambda s: self.suspicion.get(s, 0))
            if self.suspicion.get(most_sus, 0) > 1.0:
                return f"Seat {most_sus} seems the most suspicious. Let's vote for them."
        return "I don't have strong opinions yet. Let's keep discussing."

    def _analyze_speech(self, speech: dict) -> None:
        seat = speech.get("seat", 0)
        content = speech.get("content", "").lower()
        if seat == self.my_seat:
            return
        if "seer" in content or "预言家" in content:
            if seat not in self.claimed_seer:
                self.claimed_seer.append(seat)
        if len(content) < 30:
            self.suspicion[seat] += 0.3
        accusation_words = ["suspicious", "vote", "werewolf", "kill", "可疑", "狼"]
        if any(w in content for w in accusation_words):
            self.suspicion[seat] += 0.2

    def _pick_vote(self, candidates: List[int]) -> int:
        if self.my_role == "werewolf":
            god_c = [c for c in candidates if c in self.claimed_seer]
            if god_c:
                return random.choice(god_c)
            non_team = [c for c in candidates if c not in self.teammates]
            if non_team:
                return max(non_team, key=lambda s: self.suspicion.get(s, 0))
        if self.my_role == "seer":
            wolves = [c for c in candidates if self.seer_results.get(c) == "bad"]
            if wolves:
                return random.choice(wolves)
        return max(candidates, key=lambda s: self.suspicion.get(s, 0))


def main() -> None:
    parser = argparse.ArgumentParser(description="SimpleStrategyAgent")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--server", default="http://localhost:8000")
    parser.add_argument("--room", required=True)
    parser.add_argument("--game-id", default=None)
    parser.add_argument("--name", default="SimpleStrategy")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    async def run():
        agent = SimpleStrategyAgent(
            api_key=args.api_key, server_url=args.server, agent_name=args.name,
        )
        await agent.join_room(args.room)
        if args.game_id:
            agent.set_game_id(args.game_id)
        await agent.run_async()

    asyncio.run(run())


if __name__ == "__main__":
    main()
