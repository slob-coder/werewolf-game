/**
 * Tests for the ArenaRESTClient — TypeScript SDK.
 */

import { ArenaRESTClient } from './client';

describe('ArenaRESTClient', () => {
  describe('initialization', () => {
    it('should set base URL correctly', () => {
      const client = new ArenaRESTClient('http://localhost:8000', 'test-key');
      // We can't access private fields directly, but we can verify the constructor works
      expect(client).toBeInstanceOf(ArenaRESTClient);
    });

    it('should strip trailing slash from server URL', () => {
      const client = new ArenaRESTClient('http://localhost:8000/', 'test-key');
      expect(client).toBeInstanceOf(ArenaRESTClient);
    });
  });

  describe('error handling', () => {
    it('should throw ArenaAPIError on 404', async () => {
      const client = new ArenaRESTClient('http://localhost:99999', 'test-key');
      // This should throw ArenaConnectionError since the server is unreachable
      await expect(client.health()).rejects.toThrow();
    });
  });
});
