import { useEffect, useMemo, useState } from 'react'
import { Pane } from 'react-leaflet'
import { fetchPlaces, fetchTracts } from './api'
import { Controls } from './components/Controls'
import { Legend } from './components/Legend'
import { MapView } from './components/MapView'
import { NearbyLayer } from './components/NearbyLayer'
import { NearbyPanel } from './components/NearbyPanel'
import { PlaceLayer } from './components/PlaceLayer'
import { TractLayer } from './components/TractLayer'
import { TractPanel } from './components/TractPanel'
import { ViewTabs } from './components/ViewTabs'
import type {
  Measure,
  PlaceCollection,
  PlaceType,
  TractCollection,
  TractLayerKind,
  View,
} from './types'
import { useNearbySearch } from './useNearbySearch'
import './App.css'

function App() {
  const [view, setView] = useState<View>('explore')
  const nearbySearch = useNearbySearch()
  const [tracts, setTracts] = useState<TractCollection | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [layerKind, setLayerKind] = useState<TractLayerKind>('food_access')
  const [measure, setMeasure] = useState<Measure>('usda_2019_supermarkets')
  const [places, setPlaces] = useState<PlaceCollection | null>(null)
  const [visiblePlaceTypes, setVisiblePlaceTypes] = useState<Set<PlaceType>>(
    new Set(['grocery', 'pantry', 'farmers_market']),
  )
  const [showPriority, setShowPriority] = useState(false)
  const [selectedGeoid, setSelectedGeoid] = useState<string | null>(null)

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

  const priorityCount = useMemo(
    () =>
      tracts?.features.filter((f) => f.properties.food_access[measure]?.priority_area).length ?? 0,
    [tracts, measure],
  )

  const selectedTract =
    tracts?.features.find((f) => f.properties.geoid === selectedGeoid)?.properties ?? null

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
          <p className="subtitle">Food access and health across Dallas County</p>
        </header>
        <ViewTabs view={view} onChange={setView} />
        {view === 'nearby' ? (
          <NearbyPanel search={nearbySearch} />
        ) : (
          <>
            <Controls
              layerKind={layerKind}
              onLayerKindChange={setLayerKind}
              measure={measure}
              onMeasureChange={setMeasure}
              visiblePlaceTypes={visiblePlaceTypes}
              onTogglePlaceType={togglePlaceType}
              placeCounts={placeCounts}
              showPriority={showPriority}
              onShowPriorityChange={setShowPriority}
              priorityCount={priorityCount}
            />
            <Legend
              layerKind={layerKind}
              measure={measure}
              showPriority={showPriority}
              obesityMedian={tracts?.obesity_median_pct ?? null}
            />
            {selectedTract ? (
              <TractPanel
                tract={selectedTract}
                measure={measure}
                onClose={() => setSelectedGeoid(null)}
              />
            ) : (
              tracts && <p className="hint">Click a tract to see its details.</p>
            )}
            {loadError && <p className="error">Couldn't load map data. Is the API running?</p>}
            {!tracts && !loadError && <p className="hint">Loading tracts…</p>}
          </>
        )}
      </aside>
      <main className="map-area">
        <MapView>
          {view === 'explore' && tracts && (
            <TractLayer
              tracts={tracts}
              layerKind={layerKind}
              measure={measure}
              showPriority={showPriority}
              selectedGeoid={selectedGeoid}
              onSelect={setSelectedGeoid}
            />
          )}
          {/* Pins get their own pane (layer) above the tracts, so tract outlines never cover them */}
          <Pane name="places" style={{ zIndex: 450 }}>
            {view === 'explore' && places && (
              <PlaceLayer places={places} visibleTypes={visiblePlaceTypes} />
            )}
            {view === 'nearby' && <NearbyLayer search={nearbySearch} />}
          </Pane>
        </MapView>
      </main>
    </div>
  )
}

export default App
