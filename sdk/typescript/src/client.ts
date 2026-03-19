/**
 * REST client for the Werewolf Arena /api/v1 endpoints.
 */

import { ArenaAPIError, ArenaConnectionError } from './errors';
import type {
  Action,
  ActionRequestBody,
  ActionResponse,
  GameState,
  JoinResponse,
  PlayerInfo,
  RoomInfo,
} from './types';

export class ArenaRESTClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly timeout: number;

  constructor(serverUrl: string, apiKey: string, timeout = 30_000) {
    this.baseUrl = `${serverUrl.replace(/\/+$/, '')}/api/v1`;
    this.apiKey = apiKey;
    this.timeout = timeout;
  }

  private async request<T = any>(
    method: string,
    path: string,
    body?: unknown,
    params?: Record<string, string>,
  ): Promise<T> {
    let url = `${this.baseUrl}${path}`;
    if (params) {
      const qs = new URLSearchParams(params).toString();
      if (qs) url += `?${qs}`;
    }

    const headers: Record<string, string> = {
      'X-Agent-Key': this.apiKey,
      'Content-Type': 'application/json',
    };

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(url, {
        method,
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (resp.status === 204) return {} as T;
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail =
          typeof data === 'object' && data !== null && 'detail' in data
            ? (data as any).detail
            : resp.statusText;
        throw new ArenaAPIError(resp.status, String(detail));
      }
      return data as T;
    } catch (err) {
      if (err instanceof ArenaAPIError) throw err;
      throw new ArenaConnectionError(
        `HTTP request to ${url} failed: ${(err as Error).message}`,
      );
    } finally {
      clearTimeout(timer);
    }
  }

  async listRooms(status?: string): Promise<RoomInfo[]> {
    const params = status ? { status } : undefined;
    return this.request('GET', '/rooms', undefined, params);
  }

  async getRoom(roomId: string): Promise<RoomInfo> {
    return this.request('GET', `/rooms/${roomId}`);
  }

  async joinRoom(roomId: string): Promise<JoinResponse> {
    return this.request('POST', `/rooms/${roomId}/join`);
  }

  async leaveRoom(roomId: string): Promise<{ message: string }> {
    return this.request('POST', `/rooms/${roomId}/leave`);
  }

  async toggleReady(roomId: string): Promise<any> {
    return this.request('POST', `/rooms/${roomId}/ready`);
  }

  async getGameState(gameId: string): Promise<GameState> {
    const raw = await this.request<any>('GET', `/games/${gameId}/state`);
    return {
      gameId: raw.game_id,
      roomId: raw.room_id,
      status: raw.status,
      currentPhase: raw.current_phase,
      currentRound: raw.current_round,
      mySeat: raw.my_seat,
      myRole: raw.my_role,
      players: (raw.players || []).map((p: any): PlayerInfo => ({
        seat: p.seat,
        agentName: p.agent_name,
        isAlive: p.is_alive ?? true,
        role: p.role,
      })),
      startedAt: raw.started_at,
      finishedAt: raw.finished_at,
      winner: raw.winner,
    };
  }

  async submitAction(gameId: string, action: Action): Promise<ActionResponse> {
    const body: ActionRequestBody = { action_type: action.actionType };
    if (action.target !== undefined) body.target_seat = action.target;
    if (action.content !== undefined) body.content = action.content;
    if (action.metadata !== undefined) body.metadata = action.metadata;
    return this.request('POST', `/games/${gameId}/action`, body);
  }

  async getGameEvents(gameId: string): Promise<any[]> {
    const data = await this.request<any>('GET', `/games/${gameId}/events`);
    return data.events || [];
  }

  async getRolePresets(): Promise<any[]> {
    const data = await this.request<any>('GET', '/roles/presets');
    return data.presets || [];
  }

  async getAvailableRoles(): Promise<any[]> {
    const data = await this.request<any>('GET', '/roles/available');
    return data.roles || [];
  }

  async getGameStats(gameId: string): Promise<any> {
    return this.request('GET', `/games/${gameId}/stats`);
  }

  async getGameReplay(gameId: string): Promise<any> {
    return this.request('GET', `/games/${gameId}/replay`);
  }

  async health(): Promise<{ status: string; service: string }> {
    return this.request('GET', '/health');
  }
}
