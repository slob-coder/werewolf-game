[bot-1] ──▶ HTTP POST /api/v1/rooms/abc123/join
       body: {}
[bot-1] ◀── HTTP ✓ 200
       {"player_token": "xxx", ...}

[bot-1] ◀══ SIO [game.start]
         {"your_role": "werewolf", "your_seat": 3, ...}

[bot-1] ══▶ SIO [action.submit]
         {"action_type": "werewolf_kill", "target": 5, ...}
