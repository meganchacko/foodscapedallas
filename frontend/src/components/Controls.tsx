import { MEASURE_DESCRIPTIONS, MEASURE_LABELS } from '../mapStyle'
import type { Measure, TractLayerKind } from '../types'

type Props = {
  layerKind: TractLayerKind
  onLayerKindChange: (kind: TractLayerKind) => void
  measure: Measure
  onMeasureChange: (measure: Measure) => void
}

const LAYER_LABELS: Record<TractLayerKind, string> = {
  food_access: 'Food access',
  obesity: 'Adult obesity rate',
}

export function Controls({ layerKind, onLayerKindChange, measure, onMeasureChange }: Props) {
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
    </section>
  )
}
