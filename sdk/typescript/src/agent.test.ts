/**
 * Tests for the WerewolfAgent base class — TypeScript SDK.
 */

import { WerewolfAgent } from './agent';
import { ArenaConnectionError } from './errors';
import type { Action, AgentConfig, GameEvent } from './types';

// ── Test subclass ───────────────────────────────────────────────

class TestAgent extends WerewolfAgent {
  started = false;
  ended = false;
  nightCalled = false;
  speechCalled = false;
  voteCalled = false;
  lastEvent: GameEvent | null = null;

  async onGameStart(event: GameEvent): Promise<void> {
    this.started = true;
    this.lastEvent = event;
  }

  async onNightAction(event: GameEvent): Promise<Action | null> {
    this.nightCalled = true;
    this.lastEvent = event;
    return { actionType: 'werewolf_kill', target: 1 };
  }

  async onSpeechTurn(event: GameEvent): Promise<Action | null> {
    this.speechCalled = true;
    this.lastEvent = event;
    return { actionType: 'speech', content: 'test' };
  }

  async onVote(event: GameEvent): Promise<Action | null> {
    this.voteCalled = true;
    this.lastEvent = event;
    return { actionType: 'vote', target: 3 };
  }

  async onGameEnd(event: GameEvent): Promise<void> {
    this.ended = true;
    this.lastEvent = event;
  }
}

// ── Tests ───────────────────────────────────────────────────────

describe('WerewolfAgent', () => {
  const config: AgentConfig = {
    apiKey: 'test-key',
    serverUrl: 'http://localhost:8000',
    agentName: 'TestBot',
  };

  describe('initialization', () => {
    it('should set properties correctly', () => {
      const agent = new TestAgent(config);
      expect(agent.apiKey).toBe('test-key');
      expect(agent.serverUrl).toBe('http://localhost:8000');
      expect(agent.agentName).toBe('TestBot');
      expect(agent.gameId).toBeNull();
      expect(agent.roomId).toBeNull();
      expect(agent.seat).toBeNull();
      expect(agent.role).toBeNull();
      expect(agent.isConnected).toBe(false);
    });

    it('should strip trailing slash from server URL', () => {
      const agent = new TestAgent({
        ...config,
        serverUrl: 'http://localhost:8000/',
      });
      expect(agent.serverUrl).toBe('http://localhost:8000');
    });

    it('should use default agent name', () => {
      const agent = new TestAgent({
        apiKey: 'key',
        serverUrl: 'http://localhost:8000',
      });
      expect(agent.agentName).toBe('Agent');
    });
  });

  describe('setGameId', () => {
    it('should set the game ID', () => {
      const agent = new TestAgent(config);
      expect(agent.gameId).toBeNull();
      agent.setGameId('game-123');
      expect(agent.gameId).toBe('game-123');
    });
  });

  describe('connect', () => {
    it('should throw if no game ID is set', async () => {
      const agent = new TestAgent(config);
      await expect(agent.connect()).rejects.toThrow(ArenaConnectionError);
    });
  });

  describe('state sync', () => {
    it('should update internal state from sync data', () => {
      const agent = new TestAgent(config);
      // Access private method via any cast for testing
      (agent as any)._updateStateFromSync({
        game_id: 'g-1',
        status: 'in_progress',
        current_phase: 'night_werewolf',
        current_round: 2,
        your_seat: 3,
        your_role: 'seer',
        players: [
          { seat: 1, is_alive: true },
          { seat: 2, is_alive: false },
        ],
      });

      expect(agent.gameId).toBe('g-1');
      expect(agent.role).toBe('seer');
      expect(agent.seat).toBe(3);
      expect(agent.gameState).not.toBeNull();
      expect(agent.gameState!.status).toBe('in_progress');
      expect(agent.gameState!.currentRound).toBe(2);
      expect(agent.gameState!.players).toHaveLength(2);
    });
  });

  describe('event creation', () => {
    it('should create GameEvent from data', () => {
      const agent = new TestAgent(config);
      agent.setGameId('game-1');
      const event = (agent as any)._makeEvent('test.event', { key: 'value' });
      expect(event.eventType).toBe('test.event');
      expect(event.gameId).toBe('game-1');
      expect(event.data.key).toBe('value');
    });
  });
});
