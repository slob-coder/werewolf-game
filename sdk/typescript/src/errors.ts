/**
 * Custom error types for the Werewolf Arena SDK.
 */

export class ArenaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ArenaError';
  }
}

export class ArenaConnectionError extends ArenaError {
  constructor(message: string) {
    super(message);
    this.name = 'ArenaConnectionError';
  }
}

export class ArenaAPIError extends ArenaError {
  public readonly statusCode: number;
  public readonly detail: string;

  constructor(statusCode: number, detail: string) {
    super(`API error ${statusCode}: ${detail}`);
    this.name = 'ArenaAPIError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

export class ArenaTimeoutError extends ArenaError {
  constructor(message: string) {
    super(message);
    this.name = 'ArenaTimeoutError';
  }
}

export class ArenaAuthError extends ArenaError {
  constructor(message: string) {
    super(message);
    this.name = 'ArenaAuthError';
  }
}
