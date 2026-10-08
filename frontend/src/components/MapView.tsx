import 'leaflet/dist/leaflet.css'
import type { ReactNode } from 'react'
import { MapContainer, TileLayer } from 'react-leaflet'

// Downtown Dallas, zoomed out enough to show most of the county
const DALLAS_CENTER: [number, number] = [32.8, -96.78]
const INITIAL_ZOOM = 10

// CARTO "Positron": a light gray base map built from OpenStreetMap data, designed for drawing
// your own data on top. Since September 2026 CARTO requires a (free) API key; without one the
// tiles still load but carry an "API key required" watermark.
// Vite only exposes env vars starting with VITE_ to browser code. A map tile key always ends up
// in the browser (it's in every tile URL), so it's a public identifier, not a secret.
const CARTO_API_KEY = import.meta.env.VITE_CARTO_API_KEY as string | undefined
const CARTO_TILES =
  'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png' +
  (CARTO_API_KEY ? `?key=${encodeURIComponent(CARTO_API_KEY)}` : '')
const CARTO_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors ' +
  '&copy; <a href="https://carto.com/attributions">CARTO</a>'

export function MapView({ children }: { children: ReactNode }) {
  return (
    // zoomSnap 0.25 allows quarter zoom levels, so fitting the county fills the screen instead
    // of snapping down to the next whole level
    <MapContainer center={DALLAS_CENTER} zoom={INITIAL_ZOOM} zoomSnap={0.25} className="map">
      <TileLayer url={CARTO_TILES} attribution={CARTO_ATTRIBUTION} subdomains="abcd" />
      {children}
    </MapContainer>
  )
}
