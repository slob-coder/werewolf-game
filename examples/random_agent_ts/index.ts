/**
 * RandomAgent (TypeScript) — makes random decisions for every phase.
 *
 * Usage:
 *   npx ts-node index.ts --api-key KEY --server http://localhost:8000 --room ROOM_ID
 */

import { WerewolfAgent, GameEvent, Action, AgentConfig } from '@werewolf-arena/sdk';

const SPEECH_TEMPLATES = [
  'I think seat {target} is suspicious.',
  "I'm just a villager, I have no special information.",
  "Let's focus on who hasn't spoken much.",
  'I noticed seat {target} has been very quiet.',
  'I believe we should vote out seat {target}.',
  "I don't have strong opinions yet, let's hear from everyone.",
  "Something about seat {target}'s behavior seems off to me.",
  "I'm going to trust the group's judgment on this one.",
  'We need to be careful and not rush to conclusions.',
  'I have a good feeling about the remaining players... mostly.',
];

function pickRandom<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

class RandomAgent extends WerewolfAgent {
  private myRole = '';
  private mySeat = 0;
  private alivePlayers: number[] = [];

  async onGameStart(event: GameEvent): Promise<void> {
    this.myRole = event.data.your_role ?? 'unknown';
    this.mySeat = event.data.your_seat ?? 0;
    const players: any[] = event.data.players ?? [];
    this.alivePlayers = players.filter((p) => p.status !== 'dead').map((p) => p.seat);
    console.log(
      `[RandomAgent] Game started! I am ${this.myRole} at seat ${this.mySeat} (${this.alivePlayers.length} players)`,
    );
  }

  async onNightAction(event: GameEvent): Promise<Action | null> {
    const actions: any[] = event.data.available_actions ?? [];
    if (actions.length === 0) return null;
    const actionInfo = actions[0];
    const actionType: string = actionInfo.action_type;
    const targets: number[] = actionInfo.targets ?? [];
    if (targets.length === 0) return { actionType };
    const target = pickRandom(targets);
    console.log(`[RandomAgent] Night: ${actionType} -> seat ${target}`);
    return { actionType, target };
  }

  async onSpeechTurn(event: GameEvent): Promise<Action | null> {
    const others = this.alivePlayers.filter((s) => s !== this.mySeat);
    const target = others.length > 0 ? pickRandom(others) : 1;
    const content = pickRandom(SPEECH_TEMPLATES).replace('{target}', String(target));
    return { actionType: 'speech', content };
  }

  async onVote(event: GameEvent): Promise<Action | null> {
    const candidates: number[] = event.data.candidates ?? [];
    if (candidates.length === 0) return { actionType: 'vote_abstain' };
    if (Math.random() < 0.1 && event.data.allow_abstain) return { actionType: 'vote_abstain' };
    return { actionType: 'vote', target: pickRandom(candidates) };
  }

  async onGameEnd(event: GameEvent): Promise<void> {
    console.log(`[RandomAgent] Game over! Winner: ${event.data.winner}`);
  }

  async onPlayerDeath(data: Record<string, any>): Promise<void> {
    if (data.seat !== undefined) {
      this.alivePlayers = this.alivePlayers.filter((s) => s !== data.seat);
    }
  }
}

// CLI
async function main() {
  const args = process.argv.slice(2);
  const getArg = (name: string, def?: string): string => {
    const idx = args.indexOf(`--${name}`);
    if (idx >= 0 && idx + 1 < args.length) return args[idx + 1];
    if (def !== undefined) return def;
    console.error(`Missing --${name}`);
    process.exit(1);
  };

  const agent = new RandomAgent({
    apiKey: getArg('api-key'),
    serverUrl: getArg('server', 'http://localhost:8000'),
    agentName: getArg('name', 'RandomAgent-TS'),
  });

  await agent.joinRoom(getArg('room'));
  const gid = getArg('game-id', '');
  if (gid) agent.setGameId(gid);
  await agent.run();
}

main().catch((err) => { console.error('Fatal:', err); process.exit(1); });
