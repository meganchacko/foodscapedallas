import { useEffect, useMemo, useState } from 'react'
import { fetchPlaces, fetchTracts } from './api'
import { Controls } from './components/Controls'
import { MapView } from './components/MapView'
import { PlaceLayer } from './components/PlaceLayer'
import { TractLayer } from './components/TractLayer'
import type {
  Measure,
  PlaceCollection,
  PlaceType,
  TractCollection,
  TractLayerKind,
} from './types'
import './App.css'

function App() {
  const [tracts, setTracts] = useState<TractCollection | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [layerKind, setLayerKind] = useState<TractLayerKind>('food_access')
  const [measure, setMeasure] = useState<Measure>('usda_2019_supermarkets')
  const [places, setPlaces] = useState<PlaceCollection | null>(null)
  const [visiblePlaceTypes, setVisiblePlaceTypes] = useState<Set<PlaceType>>(
    new Set(['grocery', 'pantry', 'farmers_market']),
  )

  useEffect(() => {
    // The two requests run in parallel; each part of the map appears when its data arrives
    fetchTracts()
      .then(setTracts)
      .catch(() => setLoadError(true))
    fetchPlaces()
      .then(setPlaces)
      .catch(() => setLoadError(true))
  }, [])

  const placeCounts = useMemo(() => {
    const counts: Record<PlaceType, number> = { grocery: 0, pantry: 0, farmers_market: 0 }
    for (const place of places?.features ?? []) counts[place.properties.type] += 1
    return counts
  }, [places])

  function togglePlaceType(type: PlaceType) {
    setVisiblePlaceTypes((current) => {
      const next = new Set(current) // copy: React only re-renders when state is a new object
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <header>
          <h1>FoodScape Dallas</h1>
          <p className="subtitle">Food access and health across Dallas County census tracts</p>
        </header>
        <Controls
          layerKind={layerKind}
          onLayerKindChange={setLayerKind}
          measure={measure}
          onMeasureChange={setMeasure}
          visiblePlaceTypes={visiblePlaceTypes}
          onTogglePlaceType={togglePlaceType}
          placeCounts={placeCounts}
        />
        {loadError && <p className="error">Couldn't load map data. Is the API running?</p>}
        {!tracts && !loadError && <p className="hint">Loading tracts…</p>}
      </aside>
      <main className="map-area">
        <MapView>
          {tracts && <TractLayer tracts={tracts} layerKind={layerKind} measure={measure} />}
          {/* rendered after the tracts so pins draw on top */}
          {places && <PlaceLayer places={places} visibleTypes={visiblePlaceTypes} />}
        </MapView>
      </main>
    </div>
  )
}

export default App
