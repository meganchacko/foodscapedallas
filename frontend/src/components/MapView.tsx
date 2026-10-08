import 'leaflet/dist/leaflet.css'
import type { ReactNode } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'

// Downtown Dallas, zoomed out enough to show most of the county
const DALLAS_CENTER: [number, number] = [32.8, -96.78]
const INITIAL_ZOOM = 10

// CARTO "Positron": a light gray base map built from OpenStreetMap data, designed for drawing
// your own data on top. Free with attribution; no API key.
const CARTO_TILES = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'
const CARTO_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
  '&copy; <a href="https://carto.com/attributions">CARTO</a>'

export function MapView({ children }: { children: ReactNode }) {
  return (
    <MapContainer center={DALLAS_CENTER} zoom={INITIAL_ZOOM} className="map">
      <TileLayer url={CARTO_TILES} attribution={CARTO_ATTRIBUTION} subdomains="abcd" />
      {children}
    </MapContainer>
  )
}
