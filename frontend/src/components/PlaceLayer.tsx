import { CircleMarker, Popup } from 'react-leaflet'
import { PLACE_COLORS, PLACE_TYPES } from '../mapStyle'
import type { PlaceCollection, PlaceType } from '../types'

type Props = {
  places: PlaceCollection
  visibleTypes: Set<PlaceType>
}

const TYPE_LABELS = Object.fromEntries(PLACE_TYPES.map(({ type, label }) => [type, label]))

function yesNoUnknown(value: boolean | null): string {
  if (value === null) return 'Unknown'
  return value ? 'Yes' : 'No'
}

export function PlaceLayer({ places, visibleTypes }: Props) {
  return (
    <>
      {places.features
        .filter((place) => visibleTypes.has(place.properties.type))
        .map((place) => {
          const [lng, lat] = place.geometry.coordinates
          const info = place.properties
          return (
            <CircleMarker
              key={info.id}
              center={[lat, lng]}
              radius={5}
              pathOptions={{
                fillColor: PLACE_COLORS[info.type],
                fillOpacity: 1,
                color: '#ffffff', // white ring keeps the pin visible on any tract color
                weight: 1.5,
              }}
              // a click on a pin opens its popup without also selecting the tract underneath
              bubblingMouseEvents={false}
            >
              <Popup>
                <strong>{info.name}</strong>
                <div>{TYPE_LABELS[info.type]}</div>
                {info.address && <div>{info.address}</div>}
                {info.hours && <div>Hours: {info.hours}</div>}
                <div>
                  SNAP: {yesNoUnknown(info.accepts_snap)} · WIC: {yesNoUnknown(info.accepts_wic)}
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
    </>
  )
}
