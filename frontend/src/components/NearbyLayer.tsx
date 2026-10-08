import { latLng } from 'leaflet'
import { useEffect } from 'react'
import { Circle, CircleMarker, Popup, Tooltip, useMap } from 'react-leaflet'
import { INK, METERS_PER_MILE, PLACE_COLORS, SEARCH_POINT_COLOR, formatMiles } from '../mapStyle'
import type { NearbySearch } from '../useNearbySearch'

export function NearbyLayer({ search }: { search: NearbySearch }) {
  const map = useMap()
  const { point, radiusMiles } = search
  const radiusMeters = radiusMiles * METERS_PER_MILE

  // Zoom to the search area whenever the point or radius changes
  useEffect(() => {
    if (!point) return
    map.fitBounds(latLng(point.lat, point.lng).toBounds(radiusMeters * 2), { padding: [24, 24] })
  }, [map, point, radiusMeters])

  // Pan to a place when it's picked from the results list
  const selected = search.places.find((place) => place.id === search.selectedPlaceId)
  useEffect(() => {
    if (selected) map.panTo([selected.lat, selected.lng])
  }, [map, selected])

  if (!point) return null

  return (
    <>
      <Circle
        center={[point.lat, point.lng]}
        radius={radiusMeters}
        pathOptions={{ color: INK, weight: 1, dashArray: '4 4', fillOpacity: 0.04 }}
        interactive={false}
      />
      {/* The searched location: blue, the usual "you are here" color (tracts aren't shaded in
          this view, so blue doesn't clash with anything), with a label that's always shown */}
      <CircleMarker
        center={[point.lat, point.lng]}
        radius={8}
        pathOptions={{ color: '#ffffff', weight: 3, fillColor: SEARCH_POINT_COLOR, fillOpacity: 1 }}
        pane="places"
      >
        <Tooltip permanent direction="top" offset={[0, -8]}>
          {point.label === 'Your location' ? 'You' : 'Search location'}
        </Tooltip>
      </CircleMarker>
      {search.places.map((place) => {
        const isSelected = place.id === search.selectedPlaceId
        return (
          <CircleMarker
            key={place.id}
            center={[place.lat, place.lng]}
            radius={isSelected ? 9 : 6}
            pane="places"
            pathOptions={{
              fillColor: PLACE_COLORS[place.type],
              fillOpacity: 1,
              color: isSelected ? INK : '#ffffff',
              weight: isSelected ? 3 : 1.5,
            }}
            eventHandlers={{ click: () => search.setSelectedPlaceId(place.id) }}
          >
            <Popup>
              <strong>{place.name}</strong>
              <div>{formatMiles(place.distance_m)} away</div>
              {place.address && <div>{place.address}</div>}
              {place.accepts_snap && <div>Accepts SNAP</div>}
            </Popup>
          </CircleMarker>
        )
      })}
    </>
  )
}
