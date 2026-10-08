import type {
  GeocodeResult,
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

// "/api" is forwarded to the backend by the Vite dev server proxy (see vite.config.ts)
async function getJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const query = params ? `?${new URLSearchParams(params)}` : ''
  const response = await fetch(`/api${path}${query}`)
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : 'Something went wrong.'
    throw new ApiError(response.status, detail)
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
