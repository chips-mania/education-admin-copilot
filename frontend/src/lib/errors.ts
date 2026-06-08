import axios from 'axios'

export function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') {
      return detail
    }
    if (Array.isArray(detail)) {
      return detail.map((item) => JSON.stringify(item)).join(', ')
    }
    return error.message || fallback
  }

  if (error instanceof Error) {
    return error.message
  }

  return fallback
}
