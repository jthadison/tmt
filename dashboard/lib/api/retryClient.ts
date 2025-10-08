/**
 * Retryable API Client with Exponential Backoff
 *
 * Implements automatic retry logic for transient errors:
 * - Attempt 1: Immediate (0ms)
 * - Attempt 2: 2 seconds delay (2^1 = 2s)
 * - Attempt 3: 4 seconds delay (2^2 = 4s)
 *
 * Only retries transient errors (500, 503, timeouts).
 * Permanent errors (400, 401, 404) fail immediately.
 */

export interface RetryOptions {
  maxAttempts?: number
  retryableStatuses?: number[]
  onRetry?: (attempt: number, error: Error) => void
}

export class RetryableAPIClient {
  private async fetchWithRetry(
    url: string,
    options: RequestInit = {},
    retryOptions: RetryOptions = {}
  ): Promise<Response> {
    const {
      maxAttempts = 3,
      retryableStatuses = [408, 429, 500, 502, 503, 504],
      onRetry,
    } = retryOptions

    let lastError: Error | null = null

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const response = await fetch(url, options)

        // Success - return response
        if (response.ok) {
          return response
        }

        // Check if error is retryable
        if (!retryableStatuses.includes(response.status)) {
          // Non-retryable error (e.g., 400 Bad Request, 401 Unauthorized)
          return response
        }

        // Retryable error
        lastError = new Error(`HTTP ${response.status}: ${response.statusText}`)

        // Don't retry on last attempt
        if (attempt < maxAttempts) {
          const delayMs = Math.pow(2, attempt) * 1000 // Exponential backoff: 2s, 4s
          onRetry?.(attempt + 1, lastError)

          await new Promise(resolve => setTimeout(resolve, delayMs))
        }
      } catch (error) {
        // Network error (timeout, no connection)
        lastError = error as Error

        if (attempt < maxAttempts) {
          const delayMs = Math.pow(2, attempt) * 1000
          onRetry?.(attempt + 1, lastError)

          await new Promise(resolve => setTimeout(resolve, delayMs))
        }
      }
    }

    // All attempts failed
    throw lastError || new Error('Request failed after all retry attempts')
  }

  async post<T>(url: string, data: unknown, retryOptions?: RetryOptions): Promise<T> {
    const response = await this.fetchWithRetry(
      url,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      },
      retryOptions
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  async get<T>(url: string, retryOptions?: RetryOptions): Promise<T> {
    const response = await this.fetchWithRetry(url, { method: 'GET' }, retryOptions)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  async patch<T>(url: string, data: unknown, retryOptions?: RetryOptions): Promise<T> {
    const response = await this.fetchWithRetry(
      url,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      },
      retryOptions
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  async delete<T>(url: string, retryOptions?: RetryOptions): Promise<T> {
    const response = await this.fetchWithRetry(url, { method: 'DELETE' }, retryOptions)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }
}

// Global instance for use across the application
export const apiClient = new RetryableAPIClient()
