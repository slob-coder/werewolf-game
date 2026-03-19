/**
 * API response type definitions.
 */

export interface ApiResponse<T = unknown> {
  status: string
  data?: T
  message?: string
}

export interface HealthResponse {
  status: string
  service: string
  version?: string
}
