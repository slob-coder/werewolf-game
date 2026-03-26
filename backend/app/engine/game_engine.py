"""GameEngine — central coordinator for a werewolf game.

Ties together the StateMachine, NightResolver, ActionValidator,
WinChecker, InformationFilter, EventBus, TimeoutScheduler, and
ReconnectionManager to drive a complete game from start to finish.
"""

from __future__ import annotations

import logging
import random
from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.engine.action_validator import ActionValidator, ValidationResult
from app.engine.information_filter import InformationFilter, PlayerContext, information_filter
from app.engine.night_resolver import NightAction, NightResolver, NightResult
from app.engine.state_machine import GameContext, GamePhase, PhaseResult, StateMachine
from app.engine.win_checker import PlayerInfo, WinChecker, WinResult
from app.models.action import GameAction
from app.models.event import GameEvent
from app.models.game import Game
from app.models.player import GamePlayer
from app.roles.base import ActionType, Faction, RoleBase
from app.roles.registry import RoleRegistry
from app.scheduler.timeout_scheduler import TimeoutScheduler
from app.websocket.event_bus import EventBus
from app.websocket.reconnection import ReconnectionManager

logger = logging.getLogger(__name__)


class GameEngine:
    """Coordinates a single game's lifecycle.

    One GameEngine instance per active game.  It is created when a game
    starts and discarded when the game ends.

    Attributes:
        game_id: The UUID of the game being managed.
        state_machine: The deterministic phase state machine.
    """

    def __init__(
        self,
        game_id: str,
        event_bus: EventBus,
        scheduler: TimeoutScheduler,
        reconnection_manager: ReconnectionManager,
        *,
        same_guard_save_dies: bool = False,
    ) -> None:
        self.game_id = game_id
        self._event_bus = event_bus
        self._scheduler = scheduler
        self._reconnection = reconnection_manager

        # Sub-engines
        self.state_machine = StateMachine()
        self._night_resolver = NightResolver(same_guard_save_dies=same_guard_save_dies)
        self._action_validator = ActionValidator()
        self._win_checker = WinChecker()

        # Per-game in-memory state
        self._night_actions: list[NightAction] = []
        self._votes: dict[int, int | None] = {}  # voter_seat → target_seat (None = abstain)
        self._speech_order: list[int] = []  # ordered list of seats for speech
        self._current_speaker_idx: int = 0
        self._player_items: dict[int, dict[str, Any]] = {}  # seat → role-specific state
        self._last_guard_target: int | None = None

    # ══════════════════════════════════════════════════════════
    #  Game Lifecycle
    # ══════════════════════════════════════════════════════════

    async def start_game(self) -> None:
        """Initialize and start a game.  Called once after RoomManager.start_game()
        has created the Game + GamePlayer rows."""
        async with async_session_factory() as db:
            game = await self._get_game(db)
            players = await self._get_players(db)

            # Initialize player items (witch potions, guard state, etc.)
            for p in players:
                self._init_player_items(p.seat, p.role)

            # Advance: WAITING → ROLE_ASSIGNMENT
            ctx = self._build_context(players)
            result = self.state_machine.advance(ctx)
            await self._persist_phase(db, result)
            await self._emit_event(
                "game.start",
                {
                    "game_id": self.game_id,
                    "player_count": len(players),
                    "round": result.round_number,
                },
                phase=result.current_phase.value,
                round_number=result.round_number,
            )

            # Send role assignment to each player (private)
            for p in players:
                role_cls = RoleRegistry.get(p.role)
                await self._emit_event(
                    "role.assigned",
                    {
                        "seat": p.seat,
                        "role": p.role,
                        "display_name": role_cls.display_name if role_cls else p.role,
                        "faction": role_cls.faction.value if role_cls else "villager",
                    },
                    phase=GamePhase.ROLE_ASSIGNMENT.value,
                    round_number=result.round_number,
                    visibility="private",
                )

            # Reveal werewolf teammates to each other
            wolf_seats = [p.seat for p in players if p.role == "werewolf"]
            if len(wolf_seats) > 1:
                for p in players:
                    if p.role == "werewolf":
                        teammates = [s for s in wolf_seats if s != p.seat]
                        await self._emit_event(
                            "werewolf.teammates",
                            {"seat": p.seat, "teammates": teammates, "faction": "werewolf"},
                            phase=GamePhase.ROLE_ASSIGNMENT.value,
                            round_number=result.round_number,
                            visibility="role",
                        )

            await db.commit()

        # Auto-advance through ROLE_ASSIGNMENT → NIGHT_START
        await self._advance_phase()

    async def _advance_phase(self) -> None:
        """Advance the state machine and handle the new phase."""
        async with async_session_factory() as db:
            game = await self._get_game(db)
            players = await self._get_players(db)
            ctx = self._build_context(players)

            # Check win before advancing
            win = self._check_win(players)
            if win:
                ctx.game_over = True
                ctx.winner = win.winner
                ctx.win_reason = win.reason

            result = self.state_machine.advance(ctx)
            await self._persist_phase(db, result)
            await db.commit()

        # Handle the new phase
        await self._on_phase_enter(result)

    async def _on_phase_enter(self, result: PhaseResult) -> None:
        """Execute phase-entry logic: emit events, schedule timeouts, etc."""
        phase = result.current_phase
        rn = result.round_number

        logger.info(
            "Game %s entered phase %s (round %d)",
            self.game_id, phase.value, rn,
        )

        if phase == GamePhase.GAME_OVER:
            await self._handle_game_over(result)
            return

        if phase == GamePhase.NIGHT_START:
            self._night_actions.clear()
            await self._emit_event(
                "phase.night",
                {"round": rn, "message": f"第 {rn} 夜，天黑请闭眼"},
                phase=phase.value,
                round_number=rn,
            )
            # Auto-advance to first night sub-phase
            await self._advance_phase()
            return

        if phase == GamePhase.NIGHT_WEREWOLF:
            await self._emit_event(
                "phase.night.werewolf",
                {"round": rn, "message": "狼人请睁眼，选择你们的目标"},
                phase=phase.value,
                round_number=rn,
                visibility="role",
            )
            await self._schedule_timeout(phase)
            return

        if phase == GamePhase.NIGHT_SEER:
            await self._emit_event(
                "phase.night.seer",
                {"round": rn, "message": "预言家请睁眼，选择你要查验的人"},
                phase=phase.value,
                round_number=rn,
                visibility="private",
            )
            await self._schedule_timeout(phase)
            return

        if phase == GamePhase.NIGHT_WITCH:
            # Tell witch who was killed (so they can decide to save)
            killed_seat = self._get_werewolf_target()
            await self._emit_event(
                "phase.night.witch",
                {
                    "round": rn,
                    "message": "女巫请睁眼",
                    "killed_seat": killed_seat,
                },
                phase=phase.value,
                round_number=rn,
                visibility="private",
            )
            await self._schedule_timeout(phase)
            return

        if phase == GamePhase.NIGHT_HUNTER:
            await self._emit_event(
                "phase.night.hunter",
                {"round": rn, "message": "猎人被毒，是否开枪？"},
                phase=phase.value,
                round_number=rn,
                visibility="private",
            )
            await self._schedule_timeout(phase)
            return

        if phase == GamePhase.NIGHT_END:
            # Resolve night
            await self._resolve_night()
            # Auto-advance to day
            await self._advance_phase()
            return

        if phase == GamePhase.DAY_ANNOUNCEMENT:
            await self._announce_night_results()
            # Check win after night deaths
            async with async_session_factory() as db:
                players = await self._get_players(db)
                win = self._check_win(players)
            if win:
                await self._advance_phase()
                return
            # Auto-advance to speech
            await self._advance_phase()
            return

        if phase == GamePhase.DAY_SPEECH:
            await self._start_speech_phase(rn)
            return

        if phase == GamePhase.DAY_VOTE:
            self._votes.clear()
            await self._emit_event(
                "phase.day.vote",
                {"round": rn, "message": "请投票"},
                phase=phase.value,
                round_number=rn,
            )
            await self._schedule_timeout(phase)
            return

        if phase == GamePhase.DAY_VOTE_RESULT:
            await self._resolve_vote()
            # Check win after vote
            async with async_session_factory() as db:
                players = await self._get_players(db)
                win = self._check_win(players)
            if win:
                await self._advance_phase()
                return
            await self._advance_phase()
            return

        if phase == GamePhase.HUNTER_SHOOT:
            await self._emit_event(
                "phase.hunter_shoot",
                {"round": rn, "message": "猎人发动技能，选择开枪目标"},
                phase=phase.value,
                round_number=rn,
                visibility="public",
            )
            await self._schedule_timeout(phase)
            return

        if phase == GamePhase.LAST_WORDS:
            await self._emit_event(
                "phase.last_words",
                {"round": rn, "message": "请发表遗言"},
                phase=phase.value,
                round_number=rn,
            )
            await self._schedule_timeout(phase)
            return

        # Fallback: auto-advance for any unhandled transitional phase
        await self._advance_phase()

    # ══════════════════════════════════════════════════════════
    #  Action Processing
    # ══════════════════════════════════════════════════════════

    async def process_action(
        self,
        player_id: str,
        action_type_str: str,
        target_seat: int | None = None,
        content: str | None = None,
    ) -> dict[str, Any]:
        """Process an action submitted by a player.

        Returns a dict with ``success``, ``message``, and optional ``action_id``.
        """
        async with async_session_factory() as db:
            game = await self._get_game(db)
            player = await self._get_player_by_id(db, player_id)
            if player is None:
                return {"success": False, "message": "Player not found"}

            # Parse action type
            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                return {"success": False, "message": f"Unknown action: {action_type_str}"}

            current_phase = GamePhase(game.current_phase) if game.current_phase else GamePhase.WAITING

            # Get role instance
            role_instance = RoleRegistry.create(player.role)

            # Check if already acted
            existing = await db.execute(
                select(GameAction).where(
                    GameAction.game_id == self.game_id,
                    GameAction.player_id == player.id,
                    GameAction.round == game.current_round,
                    GameAction.phase == game.current_phase,
                )
            )
            already_acted = existing.scalar_one_or_none() is not None

            # Get alive seats
            all_players = await self._get_players(db)
            alive_seats = {p.seat for p in all_players if p.is_alive}

            # Build extra context for validation
            items = self._player_items.get(player.seat, {})
            extra = {
                "has_save_potion": items.get("has_save_potion", True),
                "has_poison_potion": items.get("has_poison_potion", True),
                "last_protected_seat": self._last_guard_target,
                "can_vote": items.get("can_vote", True),
            }

            # Validate
            vr = self._action_validator.validate(
                action_type=action_type,
                actor_seat=player.seat,
                role=role_instance,
                current_phase=current_phase,
                is_alive=player.is_alive,
                target_seat=target_seat,
                alive_seats=alive_seats,
                already_acted=already_acted,
                extra=extra,
            )
            if not vr.valid:
                return {"success": False, "message": vr.reason}

            # Record action in DB
            action_row = GameAction(
                game_id=self.game_id,
                player_id=player.id,
                action_type=action_type_str,
                round=game.current_round,
                phase=game.current_phase or "",
                target_seat=target_seat,
                content=content,
            )
            db.add(action_row)
            await db.flush()
            await db.refresh(action_row)
            action_id = action_row.id

            # Apply action side-effects
            await self._apply_action(
                db, player, action_type, target_seat, content, all_players
            )

            await db.commit()

        # Check if phase is complete
        await self._check_phase_complete()

        return {"success": True, "message": "Action recorded", "action_id": action_id}

    async def _apply_action(
        self,
        db: AsyncSession,
        player: GamePlayer,
        action_type: ActionType,
        target_seat: int | None,
        content: str | None,
        all_players: list[GamePlayer],
    ) -> None:
        """Apply immediate side-effects of an action."""

        # ── Night actions: buffer for resolution ──
        if action_type in (
            ActionType.WEREWOLF_KILL,
            ActionType.SEER_CHECK,
            ActionType.WITCH_SAVE,
            ActionType.WITCH_POISON,
            ActionType.WITCH_SKIP,
            ActionType.GUARD_PROTECT,
            ActionType.HUNTER_SHOOT,
            ActionType.HUNTER_SKIP,
        ):
            self._night_actions.append(
                NightAction(
                    actor_seat=player.seat,
                    role=player.role,
                    action_type=action_type,
                    target_seat=target_seat,
                )
            )

            # Update player items for witch
            if action_type == ActionType.WITCH_SAVE:
                items = self._player_items.setdefault(player.seat, {})
                items["has_save_potion"] = False
            elif action_type == ActionType.WITCH_POISON:
                items = self._player_items.setdefault(player.seat, {})
                items["has_poison_potion"] = False

            # Update guard state
            if action_type == ActionType.GUARD_PROTECT:
                self._last_guard_target = target_seat

        # ── Day vote: record ──
        if action_type == ActionType.VOTE:
            self._votes[player.seat] = target_seat
        elif action_type == ActionType.VOTE_ABSTAIN:
            self._votes[player.seat] = None

        # ── Speech: broadcast ──
        if action_type in (ActionType.SPEECH, ActionType.LAST_WORDS):
            game = await self._get_game(db)
            await self._emit_event(
                "player.speech",
                {
                    "seat": player.seat,
                    "content": content or "",
                    "phase": game.current_phase,
                },
                phase=game.current_phase or "",
                round_number=game.current_round,
                visibility="public",
            )

        # ── Werewolf chat: broadcast to faction ──
        if action_type == ActionType.WEREWOLF_CHAT:
            game = await self._get_game(db)
            await self._emit_event(
                "werewolf.chat",
                {
                    "seat": player.seat,
                    "content": content or "",
                },
                phase=game.current_phase or "",
                round_number=game.current_round,
                visibility="role",
            )

        # ── Hunter shoot resolution ──
        if action_type == ActionType.HUNTER_SHOOT and target_seat is not None:
            await self._kill_player(db, target_seat, "hunter_shot")
            await self._emit_event(
                "player.death",
                {
                    "seat": target_seat,
                    "cause": "hunter_shot",
                    "killer_seat": player.seat,
                },
                phase=self.state_machine.phase.value,
                round_number=self.state_machine.round_number,
                visibility="public",
            )

    # ══════════════════════════════════════════════════════════
    #  Phase Completion Check
    # ══════════════════════════════════════════════════════════

    async def _check_phase_complete(self) -> None:
        """Check if all expected actions for the current phase have been received.
        If so, advance the phase."""
        phase = self.state_machine.phase

        async with async_session_factory() as db:
            players = await self._get_players(db)
            alive = [p for p in players if p.is_alive]

        complete = False

        if phase == GamePhase.NIGHT_WEREWOLF:
            # Need: all alive werewolves voted + guard (if alive)
            wolves_acted = self._count_night_actions_by_role("werewolf", alive)
            wolf_count = sum(1 for p in alive if p.role == "werewolf")
            guard_ok = True
            if any(p.role == "guard" for p in alive):
                guard_acted = self._count_night_actions_by_role("guard", alive)
                guard_ok = guard_acted >= 1
            # Werewolves need at least one kill action
            has_kill = any(
                a.action_type == ActionType.WEREWOLF_KILL for a in self._night_actions
            )
            complete = has_kill and guard_ok

        elif phase == GamePhase.NIGHT_SEER:
            seer_acted = self._count_night_actions_by_role("seer", alive)
            complete = seer_acted >= 1

        elif phase == GamePhase.NIGHT_WITCH:
            witch_acted = self._count_night_actions_by_role("witch", alive)
            complete = witch_acted >= 1

        elif phase == GamePhase.NIGHT_HUNTER:
            hunter_acted = any(
                a.action_type in (ActionType.HUNTER_SHOOT, ActionType.HUNTER_SKIP)
                for a in self._night_actions
                if a.role == "hunter"
            )
            complete = hunter_acted

        elif phase == GamePhase.DAY_VOTE:
            # All alive players should have voted
            complete = len(self._votes) >= len(alive)

        elif phase == GamePhase.HUNTER_SHOOT:
            hunter_acted = any(
                a.action_type in (ActionType.HUNTER_SHOOT, ActionType.HUNTER_SKIP)
                for a in self._night_actions
                if a.role == "hunter"
            )
            complete = hunter_acted

        elif phase == GamePhase.LAST_WORDS:
            # Auto-complete after timeout or speech action
            async with async_session_factory() as db:
                game = await self._get_game(db)
                result = await db.execute(
                    select(GameAction).where(
                        GameAction.game_id == self.game_id,
                        GameAction.round == game.current_round,
                        GameAction.phase == game.current_phase,
                        GameAction.action_type == ActionType.LAST_WORDS.value,
                    )
                )
                complete = result.scalar_one_or_none() is not None

        if complete:
            await self._scheduler.cancel(self.game_id, phase.value)
            await self._advance_phase()

    def _count_night_actions_by_role(
        self, role_name: str, alive_players: list[GamePlayer]
    ) -> int:
        """Count how many night actions have been submitted by a specific role."""
        return sum(1 for a in self._night_actions if a.role == role_name)

    # ══════════════════════════════════════════════════════════
    #  Night Resolution
    # ══════════════════════════════════════════════════════════

    async def _resolve_night(self) -> None:
        """Resolve all buffered night actions using NightResolver."""
        async with async_session_factory() as db:
            players = await self._get_players(db)
            alive_seats = {p.seat for p in players if p.is_alive}
            seat_to_role = {p.seat: p.role for p in players}

            night_result = self._night_resolver.resolve(
                self._night_actions, alive_seats, seat_to_role
            )

            # Apply deaths
            for seat in night_result.killed:
                await self._kill_player(db, seat, "night")

            # Emit seer results (private to seer)
            for target_seat, faction in night_result.seer_results.items():
                await self._emit_event(
                    "seer.result",
                    {"target_seat": target_seat, "result": faction},
                    phase=GamePhase.NIGHT_END.value,
                    round_number=self.state_machine.round_number,
                    visibility="private",
                )

            # Store night result for day announcement
            self._last_night_result = night_result
            await db.commit()

        # Clear night actions for next round
        self._night_actions.clear()

    async def _announce_night_results(self) -> None:
        """Announce deaths from the previous night."""
        result = getattr(self, "_last_night_result", None)
        if result is None:
            return

        rn = self.state_machine.round_number
        deaths = result.killed

        if deaths:
            message = f"昨晚 {', '.join(str(s) + '号' for s in deaths)} 死亡"
        else:
            message = "昨晚是平安夜，没有人死亡"

        await self._emit_event(
            "day.announcement",
            {
                "round": rn,
                "deaths": deaths,
                "message": message,
            },
            phase=GamePhase.DAY_ANNOUNCEMENT.value,
            round_number=rn,
            visibility="public",
        )

        # Emit individual death events
        for seat in deaths:
            await self._emit_event(
                "player.death",
                {"seat": seat, "cause": "night", "round": rn},
                phase=GamePhase.DAY_ANNOUNCEMENT.value,
                round_number=rn,
                visibility="public",
            )

            # Check hunter on_death trigger
            await self._check_death_trigger(seat, "night")

    # ══════════════════════════════════════════════════════════
    #  Vote Resolution
    # ══════════════════════════════════════════════════════════

    async def _resolve_vote(self) -> None:
        """Count votes and determine the outcome."""
        rn = self.state_machine.round_number

        # Count votes (excluding abstentions)
        vote_counts: Counter[int] = Counter()
        for voter_seat, target_seat in self._votes.items():
            if target_seat is not None:
                vote_counts[target_seat] += 1

        if not vote_counts:
            # All abstained — no one dies
            await self._emit_event(
                "vote.result",
                {"round": rn, "result": "no_kill", "message": "全体弃票，无人出局", "votes": dict(self._votes)},
                phase=GamePhase.DAY_VOTE_RESULT.value,
                round_number=rn,
            )
            return

        max_votes = max(vote_counts.values())
        top_targets = [seat for seat, count in vote_counts.items() if count == max_votes]

        if len(top_targets) > 1:
            # Tie — no one dies (standard rule)
            await self._emit_event(
                "vote.result",
                {
                    "round": rn,
                    "result": "tie",
                    "tied_seats": top_targets,
                    "message": f"平票（{', '.join(str(s) + '号' for s in top_targets)}），无人出局",
                    "votes": dict(self._votes),
                },
                phase=GamePhase.DAY_VOTE_RESULT.value,
                round_number=rn,
            )
            return

        # Single target with most votes
        target_seat = top_targets[0]

        # Check idiot special case
        async with async_session_factory() as db:
            players = await self._get_players(db)
            target_player = next((p for p in players if p.seat == target_seat), None)

            if target_player and target_player.role == "idiot":
                items = self._player_items.get(target_seat, {})
                if not items.get("idiot_revealed", False):
                    # Idiot reveals and survives
                    items["idiot_revealed"] = True
                    items["can_vote"] = False
                    self._player_items[target_seat] = items
                    await self._emit_event(
                        "vote.result",
                        {
                            "round": rn,
                            "result": "idiot_reveal",
                            "target_seat": target_seat,
                            "message": f"{target_seat}号是白痴，翻牌存活，但失去投票权",
                            "votes": dict(self._votes),
                        },
                        phase=GamePhase.DAY_VOTE_RESULT.value,
                        round_number=rn,
                    )
                    return

            # Normal vote kill
            cause = "voted"
            await self._kill_player(db, target_seat, cause)
            await db.commit()

        await self._emit_event(
            "vote.result",
            {
                "round": rn,
                "result": "killed",
                "target_seat": target_seat,
                "vote_count": max_votes,
                "message": f"{target_seat}号被投票出局",
                "votes": dict(self._votes),
            },
            phase=GamePhase.DAY_VOTE_RESULT.value,
            round_number=rn,
        )

        await self._emit_event(
            "player.death",
            {"seat": target_seat, "cause": cause, "round": rn},
            phase=GamePhase.DAY_VOTE_RESULT.value,
            round_number=rn,
            visibility="public",
        )

        await self._check_death_trigger(target_seat, cause)

    # ══════════════════════════════════════════════════════════
    #  Speech Phase
    # ══════════════════════════════════════════════════════════

    async def _start_speech_phase(self, round_number: int) -> None:
        """Begin the day speech phase with a randomized speaking order."""
        async with async_session_factory() as db:
            players = await self._get_players(db)
            alive_seats = [p.seat for p in players if p.is_alive]

        # Randomize speech order
        self._speech_order = sorted(alive_seats)
        random.shuffle(self._speech_order)
        self._current_speaker_idx = 0

        await self._emit_event(
            "phase.day.speech",
            {
                "round": round_number,
                "speech_order": self._speech_order,
                "message": "白天讨论阶段开始",
            },
            phase=GamePhase.DAY_SPEECH.value,
            round_number=round_number,
        )

        await self._schedule_timeout(GamePhase.DAY_SPEECH)

    # ══════════════════════════════════════════════════════════
    #  Death Triggers
    # ══════════════════════════════════════════════════════════

    async def _check_death_trigger(self, seat: int, cause: str) -> None:
        """Check if a death triggers special role abilities (e.g. hunter)."""
        async with async_session_factory() as db:
            players = await self._get_players(db)
            player = next((p for p in players if p.seat == seat), None)
            if player is None:
                return

            role_instance = RoleRegistry.create(player.role)
            trigger = role_instance.on_death(cause)

            if trigger and trigger.get("hunter_can_shoot"):
                # Set state machine context for hunter shoot
                # The state machine will route to HUNTER_SHOOT on next advance
                pass  # Handled via GameContext in _build_context

    # ══════════════════════════════════════════════════════════
    #  Game Over
    # ══════════════════════════════════════════════════════════

    async def _handle_game_over(self, result: PhaseResult) -> None:
        """Finalize the game when GAME_OVER phase is reached."""
        winner = result.data.get("winner", "unknown")
        win_reason = result.data.get("win_reason", "")

        async with async_session_factory() as db:
            game = await self._get_game(db)
            game.status = "finished"
            game.finished_at = datetime.utcnow()
            game.winner = winner
            game.win_reason = win_reason
            
            room_id = game.room_id
            
            # 更新房间状态为 finished
            from app.models.room import Room as RoomModel
            stmt = select(RoomModel).where(RoomModel.id == room_id)
            room_result = await db.execute(stmt)
            room = room_result.scalar_one_or_none()
            if room:
                room.status = "finished"
            
            await db.commit()

        await self._emit_event(
            "game.end",
            {
                "game_id": self.game_id,
                "winner": winner,
                "win_reason": win_reason,
            },
            phase=GamePhase.GAME_OVER.value,
            round_number=result.round_number,
        )

        # Cancel all timers
        await self._scheduler.cancel_all(self.game_id)

        # Cleanup reconnection state
        self._reconnection.cleanup_game(self.game_id)
        
        # Cleanup room in-memory state
        from app.rooms.manager import room_manager
        room_manager.cleanup_room(room_id)

        logger.info("Game %s finished. Winner: %s", self.game_id, winner)

    # ══════════════════════════════════════════════════════════
    #  Timeout Handling
    # ══════════════════════════════════════════════════════════

    async def _schedule_timeout(self, phase: GamePhase) -> None:
        """Schedule a timeout for the current phase."""
        timeout = self.state_machine.get_timeout()
        if timeout <= 0:
            return

        await self._scheduler.schedule(
            self.game_id,
            phase.value,
            timeout,
            self._on_timeout,
        )

    async def _on_timeout(self, game_id: str, phase_key: str) -> None:
        """Called when a phase timer expires.  Apply default actions
        for players who haven't acted, then advance."""
        logger.info("Timeout in game %s, phase %s", game_id, phase_key)

        try:
            phase = GamePhase(phase_key)
        except ValueError:
            logger.error("Unknown phase key on timeout: %s", phase_key)
            return

        # Only advance if we're still in the same phase
        if self.state_machine.phase != phase:
            return

        # Apply timeout defaults
        async with async_session_factory() as db:
            players = await self._get_players(db)
            alive = [p for p in players if p.is_alive]

            if phase == GamePhase.NIGHT_WEREWOLF:
                # If no kill action, pick random target
                has_kill = any(
                    a.action_type == ActionType.WEREWOLF_KILL for a in self._night_actions
                )
                if not has_kill:
                    non_wolves = [p.seat for p in alive if p.role != "werewolf"]
                    if non_wolves:
                        target = random.choice(non_wolves)
                        wolf = next((p for p in alive if p.role == "werewolf"), None)
                        if wolf:
                            self._night_actions.append(
                                NightAction(
                                    actor_seat=wolf.seat,
                                    role="werewolf",
                                    action_type=ActionType.WEREWOLF_KILL,
                                    target_seat=target,
                                )
                            )

            elif phase == GamePhase.NIGHT_WITCH:
                # Witch skips if didn't act
                has_witch_action = any(
                    a.role == "witch" for a in self._night_actions
                )
                if not has_witch_action:
                    witch = next((p for p in alive if p.role == "witch"), None)
                    if witch:
                        self._night_actions.append(
                            NightAction(
                                actor_seat=witch.seat,
                                role="witch",
                                action_type=ActionType.WITCH_SKIP,
                            )
                        )

            elif phase == GamePhase.DAY_VOTE:
                # Absent voters abstain
                for p in alive:
                    if p.seat not in self._votes:
                        self._votes[p.seat] = None  # abstain

            elif phase in (GamePhase.HUNTER_SHOOT, GamePhase.NIGHT_HUNTER):
                # Hunter skips if didn't act
                has_hunter_action = any(
                    a.action_type in (ActionType.HUNTER_SHOOT, ActionType.HUNTER_SKIP)
                    for a in self._night_actions
                    if a.role == "hunter"
                )
                if not has_hunter_action:
                    hunter = next((p for p in alive if p.role == "hunter"), None)
                    if hunter:
                        self._night_actions.append(
                            NightAction(
                                actor_seat=hunter.seat,
                                role="hunter",
                                action_type=ActionType.HUNTER_SKIP,
                            )
                        )

        await self._advance_phase()

    # ══════════════════════════════════════════════════════════
    #  Player State
    # ══════════════════════════════════════════════════════════

    def _init_player_items(self, seat: int, role: str) -> None:
        """Initialize per-player state based on role."""
        items: dict[str, Any] = {}

        if role == "witch":
            items["has_save_potion"] = True
            items["has_poison_potion"] = True
        elif role == "idiot":
            items["idiot_revealed"] = False
            items["can_vote"] = True

        self._player_items[seat] = items

    async def _kill_player(
        self, db: AsyncSession, seat: int, cause: str
    ) -> None:
        """Mark a player as dead in the database."""
        result = await db.execute(
            select(GamePlayer).where(
                GamePlayer.game_id == self.game_id,
                GamePlayer.seat == seat,
            )
        )
        player = result.scalar_one_or_none()
        if player and player.is_alive:
            player.is_alive = False
            player.death_round = self.state_machine.round_number
            player.death_cause = cause
            logger.info(
                "Game %s: Player at seat %d killed (%s)",
                self.game_id, seat, cause,
            )

    def _get_werewolf_target(self) -> int | None:
        """Get the werewolf kill target from buffered night actions."""
        for a in self._night_actions:
            if a.action_type == ActionType.WEREWOLF_KILL:
                return a.target_seat
        return None

    # ══════════════════════════════════════════════════════════
    #  Context Builders
    # ══════════════════════════════════════════════════════════

    def _build_context(self, players: list[GamePlayer]) -> GameContext:
        """Build a GameContext for the state machine from current player state."""
        alive_roles = {p.role for p in players if p.is_alive}

        # Check if witch poisoned hunter (for night_hunter phase trigger)
        witch_poisoned_hunter = any(
            a.action_type == ActionType.WITCH_POISON
            and a.target_seat is not None
            and any(
                p.seat == a.target_seat and p.role == "hunter"
                for p in players
            )
            for a in self._night_actions
        )

        # Check hunter pending shot (voted out hunter)
        hunter_pending = False
        vote_killed_hunter = False
        for p in players:
            if p.role == "hunter" and not p.is_alive:
                if p.death_cause == "voted":
                    vote_killed_hunter = True
                    hunter_pending = True

        # Check win condition
        win = self._check_win(players)
        game_over = win is not None

        return GameContext(
            alive_roles=alive_roles,
            witch_poisoned_hunter=witch_poisoned_hunter,
            hunter_pending_shot=hunter_pending,
            vote_killed_hunter=vote_killed_hunter,
            game_over=game_over,
            winner=win.winner if win else None,
            win_reason=win.reason if win else None,
        )

    def _check_win(self, players: list[GamePlayer]) -> WinResult | None:
        """Check win conditions using the WinChecker."""
        player_infos = []
        for p in players:
            role_cls = RoleRegistry.get(p.role)
            faction = role_cls.faction if role_cls else Faction.VILLAGER
            player_infos.append(
                PlayerInfo(
                    seat=p.seat,
                    role_name=p.role,
                    faction=faction,
                    is_alive=p.is_alive,
                )
            )
        return self._win_checker.check(player_infos)

    # ══════════════════════════════════════════════════════════
    #  Persistence Helpers
    # ══════════════════════════════════════════════════════════

    async def _persist_phase(self, db: AsyncSession, result: PhaseResult) -> None:
        """Write the new phase and round to the Game row."""
        await db.execute(
            update(Game)
            .where(Game.id == self.game_id)
            .values(
                current_phase=result.current_phase.value,
                current_round=result.round_number,
            )
        )

    async def _emit_event(
        self,
        event_type: str,
        data: dict[str, Any],
        *,
        phase: str = "",
        round_number: int = 0,
        visibility: str = "public",
    ) -> None:
        """Persist event to DB and publish via EventBus."""
        # Persist
        async with async_session_factory() as db:
            event = GameEvent(
                game_id=self.game_id,
                event_type=event_type,
                round=round_number,
                phase=phase,
                data=data,
                visibility=visibility,
            )
            db.add(event)
            await db.commit()

        # Publish via EventBus
        await self._event_bus.publish_game_event(
            self.game_id,
            event_type,
            data,
            phase=phase,
            round_number=round_number,
            visibility=visibility,
        )

    # ══════════════════════════════════════════════════════════
    #  DB Queries
    # ══════════════════════════════════════════════════════════

    async def _get_game(self, db: AsyncSession) -> Game:
        result = await db.execute(select(Game).where(Game.id == self.game_id))
        game = result.scalar_one_or_none()
        if game is None:
            raise RuntimeError(f"Game {self.game_id} not found")
        return game

    async def _get_players(self, db: AsyncSession) -> list[GamePlayer]:
        result = await db.execute(
            select(GamePlayer).where(GamePlayer.game_id == self.game_id)
        )
        return list(result.scalars().all())

    async def _get_player_by_id(
        self, db: AsyncSession, player_id: str
    ) -> GamePlayer | None:
        result = await db.execute(
            select(GamePlayer).where(
                GamePlayer.game_id == self.game_id,
                GamePlayer.id == player_id,
            )
        )
        return result.scalar_one_or_none()


# ══════════════════════════════════════════════════════════════
#  Engine Registry (one GameEngine per active game)
# ══════════════════════════════════════════════════════════════


class GameEngineRegistry:
    """Manages GameEngine instances for active games."""

    def __init__(self) -> None:
        self._engines: dict[str, GameEngine] = {}

    def create(
        self,
        game_id: str,
        event_bus: EventBus,
        scheduler: TimeoutScheduler,
        reconnection_manager: ReconnectionManager,
        **kwargs: Any,
    ) -> GameEngine:
        """Create and register a new GameEngine for a game."""
        engine = GameEngine(
            game_id, event_bus, scheduler, reconnection_manager, **kwargs
        )
        self._engines[game_id] = engine
        return engine

    def get(self, game_id: str) -> GameEngine | None:
        return self._engines.get(game_id)

    def remove(self, game_id: str) -> None:
        self._engines.pop(game_id, None)

    @property
    def active_count(self) -> int:
        return len(self._engines)


# Singleton
engine_registry = GameEngineRegistry()
