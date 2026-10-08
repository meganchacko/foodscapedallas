import type { PlaceCollection, TractCollection } from './types'

// "/api" is forwarded to the backend by the Vite dev server proxy (see vite.config.ts)
async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`)
  if (!response.ok) {
    throw new Error(`${path} failed with ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function fetchTracts(): Promise<TractCollection> {
  return getJson<TractCollection>('/tracts')
}

export function fetchPlaces(): Promise<PlaceCollection> {
  return getJson<PlaceCollection>('/places')
}
