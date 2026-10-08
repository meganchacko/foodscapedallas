import {
  FOOD_ACCESS_CLASSES,
  INK,
  MEASURE_LABELS,
  NOT_CAUSATION,
  NO_DATA_COLOR,
  OBESITY_BINS,
  PRIORITY_EXPLANATION,
} from '../mapStyle'
import type { Measure, TractLayerKind } from '../types'

type Props = {
  layerKind: TractLayerKind
  measure: Measure
  showPriority: boolean
  obesityMedian: number | null
}

export function Legend({ layerKind, measure, showPriority, obesityMedian }: Props) {
  const items: { label: string; color: string }[] =
    layerKind === 'obesity' ? [...OBESITY_BINS] : [...FOOD_ACCESS_CLASSES]

  return (
    <section className="legend" aria-label="Map legend">
      <h2>{layerKind === 'obesity' ? 'Adult obesity rate (CDC)' : MEASURE_LABELS[measure]}</h2>
      <ul>
        {items.map(({ label, color }) => (
          <li key={label}>
            <span className="swatch" style={{ background: color }} aria-hidden="true" />
            {label}
          </li>
        ))}
        <li>
          <span className="swatch" style={{ background: NO_DATA_COLOR }} aria-hidden="true" />
          No data
        </li>
      </ul>

      {showPriority && (
        <div className="priority-note">
          <p>
            <span className="swatch outline" style={{ borderColor: INK }} aria-hidden="true" />
            {PRIORITY_EXPLANATION}
            {obesityMedian !== null && ` (median: ${obesityMedian}%)`}
          </p>
          <p className="hint">{NOT_CAUSATION}</p>
        </div>
      )}
    </section>
  )
}
