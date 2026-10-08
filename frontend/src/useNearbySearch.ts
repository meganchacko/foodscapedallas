// State and actions for "Find food near me", shared by the sidebar panel and the map.
// A custom hook keeps this logic in one place and out of the components that display it.
import { useEffect, useMemo, useState } from 'react'
import { ApiError, fetchNearby, geocode } from './api'
import type { NearbyResponse, PlaceType } from './types'

export const RADIUS_OPTIONS = [0.5, 1, 2, 5, 10] as const

export type SearchPoint = { lat: number; lng: number; label: string }

export function useNearbySearch() {
  const [point, setPoint] = useState<SearchPoint | null>(null)
  const [radiusMiles, setRadiusMiles] = useState<number>(1)
  const [snapOnly, setSnapOnly] = useState(false)
  const [visibleTypes, setVisibleTypes] = useState<Set<PlaceType>>(
    new Set(['grocery', 'pantry', 'farmers_market']),
  )
  const [locating, setLocating] = useState(false)
  const [inputError, setInputError] = useState<string | null>(null)
  const [selectedPlaceId, setSelectedPlaceId] = useState<number | null>(null)
  // Each result remembers which search it answers, so we can tell whether it's current
  const [result, setResult] = useState<
    { key: string; response: NearbyResponse } | { key: string; error: string } | null
  >(null)

  // Identifies the current search: point + radius + SNAP filter
  const searchKey = point ? `${point.lat},${point.lng},${radiusMiles},${snapOnly}` : null

  // Search whenever the point, radius, or SNAP filter changes
  useEffect(() => {
    if (!point || !searchKey) return
    // If the user changes something before this request finishes, ignore its (stale) answer
    let cancelled = false
    fetchNearby(point.lat, point.lng, radiusMiles, snapOnly)
      .then((response) => {
        if (!cancelled) setResult({ key: searchKey, response })
      })
      .catch((err) => {
        if (!cancelled)
          setResult({
            key: searchKey,
            error: err instanceof ApiError ? err.message : "Couldn't reach the server.",
          })
      })
    return () => {
      cancelled = true
    }
  }, [point, radiusMiles, snapOnly, searchKey])

  // Derived, not stored: "searching" just means the latest search hasn't been answered yet
  const current = result && result.key === searchKey ? result : null
  const searching = searchKey !== null && current === null
  const response = current && 'response' in current ? current.response : null
  const error = inputError ?? (current && 'error' in current ? current.error : null)

  // The API returns every type; the type checkboxes filter here, so toggling one is instant
  const places = useMemo(
    () => response?.places.filter((place) => visibleTypes.has(place.type)) ?? [],
    [response, visibleTypes],
  )

  function startSearch(newPoint: SearchPoint) {
    setLocating(false)
    setInputError(null)
    setSelectedPlaceId(null)
    setPoint(newPoint)
  }

  function fail(message: string) {
    setLocating(false)
    setInputError(message)
  }

  async function searchAddress(query: string) {
    if (query.trim().length < 3) {
      fail('Enter an address, intersection, or place name.')
      return
    }
    setInputError(null)
    setLocating(true)
    try {
      const found = await geocode(query.trim())
      startSearch({ lat: found.lat, lng: found.lng, label: found.display_name })
    } catch (err) {
      fail(err instanceof ApiError ? err.message : "Couldn't reach the server.")
    }
  }

  function locateMe() {
    if (!navigator.geolocation) {
      fail("Your browser can't share its location. Try typing an address.")
      return
    }
    setInputError(null)
    setLocating(true)
    // The browser asks the user for permission first. The coordinates are only sent to our API
    // for this search; they aren't stored.
    navigator.geolocation.getCurrentPosition(
      (position) =>
        startSearch({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          label: 'Your location',
        }),
      () => fail("Couldn't get your location. Check location permissions or type an address."),
      { timeout: 10000 },
    )
  }

  function toggleType(type: PlaceType) {
    setVisibleTypes((current) => {
      const next = new Set(current)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }

  return {
    point,
    radiusMiles,
    setRadiusMiles,
    snapOnly,
    setSnapOnly,
    visibleTypes,
    toggleType,
    response,
    places,
    locating,
    searching,
    error,
    selectedPlaceId,
    setSelectedPlaceId,
    searchAddress,
    locateMe,
  }
}

export type NearbySearch = ReturnType<typeof useNearbySearch>
