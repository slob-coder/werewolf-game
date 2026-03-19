/**
 * Tests for error classes — TypeScript SDK.
 */

import {
  ArenaAPIError,
  ArenaAuthError,
  ArenaConnectionError,
  ArenaError,
  ArenaTimeoutError,
} from './errors';

describe('Error classes', () => {
  it('ArenaError should be an Error', () => {
    const err = new ArenaError('test');
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe('ArenaError');
    expect(err.message).toBe('test');
  });

  it('ArenaConnectionError should extend ArenaError', () => {
    const err = new ArenaConnectionError('conn failed');
    expect(err).toBeInstanceOf(ArenaError);
    expect(err.name).toBe('ArenaConnectionError');
  });

  it('ArenaAPIError should include status code and detail', () => {
    const err = new ArenaAPIError(404, 'Not found');
    expect(err).toBeInstanceOf(ArenaError);
    expect(err.statusCode).toBe(404);
    expect(err.detail).toBe('Not found');
    expect(err.message).toBe('API error 404: Not found');
  });

  it('ArenaTimeoutError should extend ArenaError', () => {
    const err = new ArenaTimeoutError('timed out');
    expect(err).toBeInstanceOf(ArenaError);
    expect(err.name).toBe('ArenaTimeoutError');
  });

  it('ArenaAuthError should extend ArenaError', () => {
    const err = new ArenaAuthError('bad key');
    expect(err).toBeInstanceOf(ArenaError);
    expect(err.name).toBe('ArenaAuthError');
  });
});
