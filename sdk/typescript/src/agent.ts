/**
 * WerewolfAgent — base class for Werewolf Arena AI agents (TypeScript).
 *
 * Subclass, override on* callbacks, and call run().
 */

import { io, Socket } from 'socket.io-client';
import { ArenaRESTClient } from './client';
import { ArenaConnectionError } from './errors';
import type { Action, AgentConfig, GameEvent, GameState, PlayerInfo } from './types';

export class WerewolfAgent {
  readonly apiKey: string;
  readonly serverUrl: string;
  readonly agentName: string;
  readonly rest: ArenaRESTClient;

  private _gameId: string | null = null;
  private _roomId: string | null = null;
  private _seat: number | null = null;
  private _role: string | null = null;
  private _gameState: GameState | null = null;
  private _connected = false;
  private _running = false;
  private _sio: Socket | null = null;
  private _resolveWait: (() => void) | null = null;

  constructor(config: AgentConfig) {
    this.apiKey = config.apiKey;
    this.serverUrl = config.serverUrl.replace(/\/+$/, '');
    this.agentName = config.agentName ?? 'Agent';
    this.rest = new ArenaRESTClient(this.serverUrl, this.apiKey, config.timeout ?? 30_000);
  }

  get gameId(): string | null { return this._gameId; }
  get roomId(): string | null { return this._roomId; }
  get seat(): number | null { return this._seat; }
  get role(): string | null { return this._role; }
  get gameState(): GameState | null { return this._gameState; }
  get isConnected(): boolean { return this._connected; }

  async connect(serverUrl?: string, apiKey?: string): Promise<void> {
    const url = (serverUrl ?? this.serverUrl).replace(/\/+$/, '');
    const key = apiKey ?? this.apiKey;
    if (!this._gameId) {
      throw new ArenaConnectionError('No game_id set. Call joinRoom() first or setGameId().');
    }
    return new Promise<void>((resolve, reject) => {
      this._sio = io(`${url}/ws/agent`, {
        auth: { api_key: key, game_id: this._gameId },
        reconnection: true,
        reconnectionAttempts: 10,
        reconnectionDelay: 2000,
        reconnectionDelayMax: 30_000,
        timeout: 15_000,
        transports: ['websocket', 'polling'],
      });
      this._sio.on('connect', () => {
        this._connected = true;
        console.log(`[${this.agentName}] Connected to ${url} (game ${this._gameId})`);
        resolve();
      });
      this._sio.on('connect_error', (err: Error) => {
        reject(new ArenaConnectionError(`Connection failed: ${err.message}`));
      });
      this._sio.on('disconnect', () => {
        this._connected = false;
        console.log(`[${this.agentName}] Disconnected`);
      });
      this._registerHandlers(this._sio);
    });
  }

  async disconnect(): Promise<void> {
    if (this._sio) { this._sio.disconnect(); this._sio = null; }
    this._connected = false;
    this._resolveWait?.();
  }

  async joinRoom(roomId: string): Promise<{ seat: number; room_id: string; agent_id: string }> {
    this._roomId = roomId;
    const result = await this.rest.joinRoom(roomId);
    this._seat = result.seat;
    console.log(`[${this.agentName}] Joined room ${roomId} at seat ${result.seat}`);
    return result;
  }

  async leaveRoom(): Promise<void> {
    if (this._roomId) { await this.rest.leaveRoom(this._roomId); this._roomId = null; this._seat = null; }
  }

  setGameId(gameId: string): void { this._gameId = gameId; }

  async submitAction(action: Action): Promise<any> {
    if (!this._gameId) throw new ArenaConnectionError('No active game');
    return this.rest.submitAction(this._gameId, action);
  }

  async sendSpeech(content: string): Promise<any> {
    return this.submitAction({ actionType: 'speech', content });
  }

  async submitVote(target?: number): Promise<any> {
    if (target === undefined) return this.submitAction({ actionType: 'vote_abstain' });
    return this.submitAction({ actionType: 'vote', target });
  }

  async run(): Promise<void> {
    this._running = true;
    if (!this._connected) await this.connect();
    console.log(`[${this.agentName}] Running — waiting for game events…`);
    await new Promise<void>((resolve) => { this._resolveWait = resolve; });
    this._running = false;
  }

  async stop(): Promise<void> {
    this._running = false;
    await this.disconnect();
  }

  // -- callbacks (override these) --
  async onGameStart(event: GameEvent): Promise<void> {}
  async onNightAction(event: GameEvent): Promise<Action | null> { return null; }
  async onSpeechTurn(event: GameEvent): Promise<Action | null> { return null; }
  async onVote(event: GameEvent): Promise<Action | null> { return null; }
  async onGameEnd(event: GameEvent): Promise<void> {}
  async onGameSync(data: Record<string, any>): Promise<void> {}
  async onPlayerSpeech(data: Record<string, any>): Promise<void> {}
  async onPlayerDeath(data: Record<string, any>): Promise<void> {}
  async onVoteResult(data: Record<string, any>): Promise<void> {}
  async onWerewolfChat(data: Record<string, any>): Promise<void> {}
  async onActionAck(data: Record<string, any>): Promise<void> {}
  async onActionRejected(data: Record<string, any>): Promise<void> {
    console.warn(`[${this.agentName}] Action rejected:`, data?.reason ?? 'unknown');
  }

  // -- internal --
  private _registerHandlers(sio: Socket): void {
    sio.on('game.sync', async (data: Record<string, any>) => {
      this._updateStateFromSync(data);
      await this.onGameSync(data);
    });
    sio.on('game.start', async (data: Record<string, any>) => {
      this._role = data.your_role ?? null;
      this._seat = data.your_seat ?? null;
      await this.onGameStart(this._makeEvent('game.start', data));
    });
    sio.on('phase.night', async (data: Record<string, any>) => {
      const action = await this.onNightAction(this._makeEvent('phase.night', data));
      if (action) await this._submitActionSafe(action);
    });
    sio.on('phase.day.speech', async (data: Record<string, any>) => {
      if (data.is_your_turn) {
        const action = await this.onSpeechTurn(this._makeEvent('phase.day.speech', data));
        if (action) await this._submitActionSafe(action);
      }
    });
    sio.on('phase.day.vote', async (data: Record<string, any>) => {
      const action = await this.onVote(this._makeEvent('phase.day.vote', data));
      if (action) await this._submitActionSafe(action);
    });
    sio.on('game.end', async (data: Record<string, any>) => {
      await this.onGameEnd(this._makeEvent('game.end', data));
      await this.stop();
    });
    sio.on('player.speech', async (data: Record<string, any>) => { await this.onPlayerSpeech(data); });
    sio.on('player.death', async (data: Record<string, any>) => { await this.onPlayerDeath(data); });
    sio.on('vote.result', async (data: Record<string, any>) => { await this.onVoteResult(data); });
    sio.on('werewolf.chat', async (data: Record<string, any>) => { await this.onWerewolfChat(data); });
    sio.on('action.ack', async (data: Record<string, any>) => { await this.onActionAck(data); });
    sio.on('action.rejected', async (data: Record<string, any>) => { await this.onActionRejected(data); });
  }

  private _makeEvent(eventType: string, data: Record<string, any>): GameEvent {
    return { eventType, gameId: this._gameId ?? '', data };
  }

  private _updateStateFromSync(data: Record<string, any>): void {
    this._gameId = data.game_id ?? this._gameId;
    this._role = data.your_role ?? this._role;
    this._seat = data.your_seat ?? this._seat;
    this._gameState = {
      gameId: data.game_id ?? '',
      status: data.status ?? '',
      currentPhase: data.current_phase,
      currentRound: data.current_round ?? 0,
      mySeat: data.your_seat,
      myRole: data.your_role,
      players: (data.players ?? []).map((p: any): PlayerInfo => ({
        seat: p.seat, agentName: p.agent_name, isAlive: p.is_alive ?? true, role: p.role,
      })),
    };
  }

  private async _submitActionSafe(action: Action): Promise<void> {
    try {
      const result = await this.submitAction(action);
      if (result && !result.success) console.warn(`[${this.agentName}] Action failed: ${result.message}`);
    } catch (err) {
      console.error(`[${this.agentName}] Failed to submit action:`, err);
    }
  }
}
