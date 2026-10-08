import type { GeoJSON as LeafletGeoJSON, PathOptions } from 'leaflet'
import { useCallback, useEffect, useRef } from 'react'
import { GeoJSON } from 'react-leaflet'
import { foodAccessColor, obesityColor } from '../mapStyle'
import type { Measure, TractCollection, TractFeature, TractLayerKind } from '../types'

type Props = {
  tracts: TractCollection
  layerKind: TractLayerKind
  measure: Measure
}

export function TractLayer({ tracts, layerKind, measure }: Props) {
  const layerRef = useRef<LeafletGeoJSON>(null)

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
