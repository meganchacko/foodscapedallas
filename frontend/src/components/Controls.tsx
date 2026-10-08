import { MEASURE_DESCRIPTIONS, MEASURE_LABELS, PLACE_TYPES } from '../mapStyle'
import type { Measure, PlaceType, TractLayerKind } from '../types'

type Props = {
  layerKind: TractLayerKind
  onLayerKindChange: (kind: TractLayerKind) => void
  measure: Measure
  onMeasureChange: (measure: Measure) => void
  visiblePlaceTypes: Set<PlaceType>
  onTogglePlaceType: (type: PlaceType) => void
  placeCounts: Record<PlaceType, number>
  showPriority: boolean
  onShowPriorityChange: (show: boolean) => void
  priorityCount: number
}

const LAYER_LABELS: Record<TractLayerKind, string> = {
  food_access: 'Food access',
  obesity: 'Adult obesity rate',
}

export function Controls({
  layerKind,
  onLayerKindChange,
  measure,
  onMeasureChange,
  visiblePlaceTypes,
  onTogglePlaceType,
  placeCounts,
  showPriority,
  onShowPriorityChange,
  priorityCount,
}: Props) {
  return (
    <section className="controls">
      <fieldset>
        <legend>Shade tracts by</legend>
        {(Object.keys(LAYER_LABELS) as TractLayerKind[]).map((kind) => (
          <label key={kind} className="option">
            <input
              type="radio"
              name="layer"
              checked={layerKind === kind}
              onChange={() => onLayerKindChange(kind)}
            />
            {LAYER_LABELS[kind]}
          </label>
        ))}
      </fieldset>

      <fieldset>
        <legend>Food access definition</legend>
        {(Object.keys(MEASURE_LABELS) as Measure[]).map((option) => (
          <label key={option} className="option">
            <input
              type="radio"
              name="measure"
              checked={measure === option}
              onChange={() => onMeasureChange(option)}
            />
            {MEASURE_LABELS[option]}
          </label>
        ))}
        <p className="hint">{MEASURE_DESCRIPTIONS[measure]}</p>
      </fieldset>

      <fieldset>
        <legend>Priority areas</legend>
        <label className="option">
          <input
            type="checkbox"
            checked={showPriority}
            onChange={(event) => onShowPriorityChange(event.target.checked)}
          />
          Highlight low access + high obesity{' '}
          <span className="count">({priorityCount} tracts)</span>
        </label>
      </fieldset>

      <fieldset>
        <legend>Show places</legend>
        {PLACE_TYPES.map(({ type, label, color }) => (
          <label key={type} className="option">
            <input
              type="checkbox"
              checked={visiblePlaceTypes.has(type)}
              onChange={() => onTogglePlaceType(type)}
            />
            <span className="swatch dot" style={{ background: color }} aria-hidden="true" />
            {label} <span className="count">({placeCounts[type]})</span>
          </label>
        ))}
      </fieldset>
    </section>
  )
}
