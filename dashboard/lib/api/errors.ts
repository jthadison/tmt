export class APIError extends Error {
  constructor(
    public status: number,
    public userMessage: string,
    public impact: string,
    public recoveryOptions: string[],
    public technicalDetails?: string
  ) {
    super(userMessage)
    this.name = 'APIError'
  }
}

export async function apiRequest<T = any>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, options)

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new APIError(
        response.status,
        errorData.userMessage || 'An unexpected error occurred',
        errorData.impact || 'The operation could not be completed',
        errorData.recoveryOptions || ['Try again', 'Contact support'],
        errorData.technicalDetails
      )
    }

    return response.json()
  } catch (error) {
    if (error instanceof APIError) {
      throw error
    }

    // Network error
    throw new APIError(
      0,
      'Unable to connect to server',
      'Your request could not be processed',
      ['Check your internet connection', 'Try again in a moment'],
      error instanceof Error ? error.message : undefined
    )
  }
}

export function logError(error: Error, context?: Record<string, any>) {
  if (process.env.NODE_ENV === 'production') {
    // In production, send to error tracking service (e.g., Sentry)
    // Sentry.captureException(error, { extra: context })
    console.error('Production Error:', error, 'Context:', context)
  } else {
    console.error('Error:', error, 'Context:', context)
  }
}
