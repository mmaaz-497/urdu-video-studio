const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '/api'
const CSRF_COOKIE_NAME = 'csrf_token'

export interface ApiErrorBody {
  code: string
  message: string
  requestId?: string
  resetsAt?: string
}

export class ApiError extends Error {
  code: string
  requestId?: string
  resetsAt?: string
  status: number

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.requestId = body.requestId
    this.resetsAt = body.resetsAt
  }
}

function readCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
}

async function apiRequest<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const { body, headers, method = 'GET', ...rest } = options
  const upperMethod = method.toUpperCase()

  const requestHeaders = new Headers(headers)
  if (body !== undefined && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }
  if (!SAFE_METHODS.has(upperMethod)) {
    const csrfToken = readCookie(CSRF_COOKIE_NAME)
    if (csrfToken) {
      requestHeaders.set('X-CSRF-Token', csrfToken)
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    method: upperMethod,
    headers: requestHeaders,
    credentials: 'include',
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (response.status === 204) {
    return undefined as T
  }

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const errorBody: ApiErrorBody = data?.error ?? {
      code: 'UNKNOWN_ERROR',
      message: 'Something went wrong. Please try again.',
    }
    throw new ApiError(response.status, errorBody)
  }

  return data as T
}

export const apiClient = {
  get: <T>(path: string, options?: ApiRequestOptions) =>
    apiRequest<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: ApiRequestOptions) =>
    apiRequest<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown, options?: ApiRequestOptions) =>
    apiRequest<T>(path, { ...options, method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown, options?: ApiRequestOptions) =>
    apiRequest<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: ApiRequestOptions) =>
    apiRequest<T>(path, { ...options, method: 'DELETE' }),
}
