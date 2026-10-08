import { geoJSON, type GeoJSON as LeafletGeoJSON, type PathOptions } from 'leaflet'
import { useCallback, useEffect, useRef } from 'react'
import { GeoJSON, useMap } from 'react-leaflet'
import { foodAccessColor, obesityColor } from '../mapStyle'
import type { Measure, TractCollection, TractFeature, TractLayerKind } from '../types'

type Props = {
  tracts: TractCollection
  layerKind: TractLayerKind
  measure: Measure
}

export function TractLayer({ tracts, layerKind, measure }: Props) {
  const layerRef = useRef<LeafletGeoJSON>(null)
  const map = useMap()

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
      return {
        fillColor: layerKind === 'obesity' ? obesityColor(tract) : foodAccessColor(tract, measure),
        fillOpacity: 0.75,
        color: '#ffffff', // thin white borders keep neighboring tracts visually separate
        weight: 0.6,
      }
    },
    [layerKind, measure],
  )

  // react-leaflet only applies `style` when the layer is first created, so restyle the existing
  // layer when a toggle changes instead of rebuilding all 645 shapes
  useEffect(() => {
    layerRef.current?.setStyle(style as (feature?: GeoJSON.Feature) => PathOptions)
  }, [style])

  return (
    <GeoJSON
      ref={layerRef}
      data={tracts}
      style={style as (feature?: GeoJSON.Feature) => PathOptions}
    />
  )
}
