import {
  geoJSON,
  type GeoJSON as LeafletGeoJSON,
  type Layer,
  type Path,
  type PathOptions,
} from 'leaflet'
import { useCallback, useEffect, useRef } from 'react'
import { GeoJSON, useMap } from 'react-leaflet'
import { INK, foodAccessColor, foodAccessLabel, obesityColor, tractName } from '../mapStyle'
import type { Measure, TractCollection, TractFeature, TractLayerKind } from '../types'

type Props = {
  tracts: TractCollection
  layerKind: TractLayerKind
  measure: Measure
  showPriority: boolean
  selectedGeoid: string | null
  onSelect: (geoid: string) => void
}

type StyleFn = (feature?: GeoJSON.Feature) => PathOptions

export function TractLayer({
  tracts,
  layerKind,
  measure,
  showPriority,
  selectedGeoid,
  onSelect,
}: Props) {
  const layerRef = useRef<LeafletGeoJSON>(null)
  const map = useMap()

  // Leaflet event handlers are attached once per tract. They read these refs so they always see
  // the current toggles instead of the values from when they were attached.
  const settingsRef = useRef({ layerKind, measure })
  const onSelectRef = useRef(onSelect)
  useEffect(() => {
    settingsRef.current = { layerKind, measure }
    onSelectRef.current = onSelect
  }, [layerKind, measure, onSelect])

  // Zoom to fit the whole county when the tract data arrives. The bounds are computed from the
  // data itself, so this doesn't depend on when react-leaflet finishes creating the layer.
  useEffect(() => {
    const bounds = geoJSON(tracts).getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [16, 16] })
  }, [map, tracts])

  const style = useCallback(
    (feature?: TractFeature): PathOptions => {
      if (!feature) return {}
      const tract = feature.properties
      const isPriority = tract.food_access[measure]?.priority_area === true
      const highlighted = showPriority && isPriority
      const selected = tract.geoid === selectedGeoid
      return {
        fillColor: layerKind === 'obesity' ? obesityColor(tract) : foodAccessColor(tract, measure),
        // With priority areas on, everything else fades so the outlined tracts stand out
        fillOpacity: showPriority && !isPriority ? 0.15 : 0.75,
        // Thin white borders separate neighbors; priority and selected tracts get a dark outline
        color: selected || highlighted ? INK : '#ffffff',
        weight: selected ? 3 : highlighted ? 1.5 : 0.6,
      }
    },
    [layerKind, measure, showPriority, selectedGeoid],
  )

  // react-leaflet only applies `style` when the layer is first created, so restyle the existing
  // layer when a toggle changes instead of rebuilding all 645 shapes
  useEffect(() => {
    const layer = layerRef.current
    if (!layer) return
    layer.setStyle(style as StyleFn)
    // Draw outlined tracts last, so their outlines aren't hidden under neighbors' borders
    layer.eachLayer((tractLayer) => {
      const tract = (tractLayer as Layer & { feature: TractFeature }).feature.properties
      const isPriority = showPriority && tract.food_access[measure]?.priority_area === true
      if (isPriority || tract.geoid === selectedGeoid) (tractLayer as Path).bringToFront()
    })
  }, [style, showPriority, measure, selectedGeoid])

  function onEachFeature(feature: GeoJSON.Feature, layer: Layer) {
    const tract = (feature as TractFeature).properties
    layer.on('click', () => onSelectRef.current(tract.geoid))
    // A function, so the hover text reflects the current toggles each time it opens
    layer.bindTooltip(
      () => {
        const { layerKind: kind, measure: currentMeasure } = settingsRef.current
        const value =
          kind === 'obesity'
            ? tract.obesity_pct === null
              ? 'No data'
              : `${tract.obesity_pct}% adult obesity`
            : foodAccessLabel(tract, currentMeasure)
        return `${tractName(tract.geoid)}: ${value}`
      },
      { sticky: true },
    )
  }

  return (
    <GeoJSON
      ref={layerRef}
      data={tracts}
      style={style as StyleFn}
      onEachFeature={onEachFeature}
    />
  )
}
