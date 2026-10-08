import { useEffect, useState } from 'react'
import { fetchTracts } from './api'
import { Controls } from './components/Controls'
import { MapView } from './components/MapView'
import { TractLayer } from './components/TractLayer'
import type { Measure, TractCollection, TractLayerKind } from './types'
import './App.css'

function App() {
  const [tracts, setTracts] = useState<TractCollection | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [layerKind, setLayerKind] = useState<TractLayerKind>('food_access')
  const [measure, setMeasure] = useState<Measure>('usda_2019_supermarkets')

  useEffect(() => {
    fetchTracts()
      .then(setTracts)
      .catch(() => setLoadError(true))
  }, [])

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
        />
        {loadError && <p className="error">Couldn't load map data. Is the API running?</p>}
        {!tracts && !loadError && <p className="hint">Loading tracts…</p>}
      </aside>
      <main className="map-area">
        <MapView>
          {tracts && <TractLayer tracts={tracts} layerKind={layerKind} measure={measure} />}
        </MapView>
      </main>
    </div>
  )
}

export default App
