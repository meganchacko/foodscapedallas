import type {
  GeocodeResult,
  HealthCheckAnswers,
  HealthCheckResult,
  ModelCard,
  NearbyResponse,
  PlaceCollection,
  TractCollection,
} from './types'

// An API error with a message that's safe to show the user (from FastAPI's "detail" field)
export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

// Where the API lives. Locally that's "/api", which the Vite dev server forwards to the backend
// (see vite.config.ts). The production build is static files on a different address than the
// API, so it's built with VITE_API_BASE_URL set to the API's URL.
export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api'

export function apiUrl(path: string, params?: Record<string, string>): string {
  const query = params ? `?${new URLSearchParams(params)}` : ''
  return `${API_BASE.replace(/\/$/, '')}${path}${query}`
}

async function getJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  return readJson<T>(await fetch(apiUrl(path, params)), path)
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return readJson<T>(response, path)
}

async function readJson<T>(response: Response, path: string): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : 'Something went wrong.'
    throw new ApiError(response.status, detail || `${path} failed`)
  }
  return response.json() as Promise<T>
}

export function fetchTracts(): Promise<TractCollection> {
  return getJson<TractCollection>('/tracts')
}

export function fetchPlaces(): Promise<PlaceCollection> {
  return getJson<PlaceCollection>('/places')
}

export function geocode(query: string): Promise<GeocodeResult> {
  return getJson<GeocodeResult>('/geocode', { q: query })
}

export function fetchNearby(
  lat: number,
  lng: number,
  radiusMiles: number,
  snapOnly: boolean,
): Promise<NearbyResponse> {
  return getJson<NearbyResponse>('/places/nearby', {
    lat: String(lat),
    lng: String(lng),
    radius: String(radiusMiles),
    snap: String(snapOnly),
  })
}

export function checkHealth(
  answers: HealthCheckAnswers,
  save: boolean,
  anonymousId: string | null,
): Promise<HealthCheckResult> {
  return postJson<HealthCheckResult>('/health-check', {
    ...answers,
    save,
    anonymous_id: save ? anonymousId : null,
  })
}

export function fetchModelCard(): Promise<ModelCard> {
  return getJson<ModelCard>('/model-card')
}
