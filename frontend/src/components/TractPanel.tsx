import {
  MEASURE_LABELS,
  formatMiles,
  formatNumber,
  foodAccessLabel,
  tractName,
} from '../mapStyle'
import type { Measure, TractProperties } from '../types'

type Props = {
  tract: TractProperties
  measure: Measure
  onClose: () => void
}

function yesNo(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return 'No data'
  return value ? 'Yes' : 'No'
}

export function TractPanel({ tract, measure, onClose }: Props) {
  const access = tract.food_access[measure]
  return (
    <section className="tract-panel" aria-label={`Details for ${tractName(tract.geoid)}`}>
      <div className="panel-header">
        <h2>{tractName(tract.geoid)}</h2>
        <button type="button" onClick={onClose} aria-label="Close tract details">
          ×
        </button>
      </div>
      <dl>
        <dt>Population (2020)</dt>
        <dd>{formatNumber(tract.population)}</dd>
        <dt>Adult obesity rate</dt>
        <dd>{tract.obesity_pct === null ? 'No data' : `${tract.obesity_pct}%`}</dd>
        <dt>Nearest grocery store</dt>
        <dd>{formatMiles(tract.nearest_grocery_m)} (straight line)</dd>
        <dt>Food access ({MEASURE_LABELS[measure]})</dt>
        <dd>{foodAccessLabel(tract, measure)}</dd>
        <dt>People with low access</dt>
        <dd>{formatNumber(access?.low_access_population ?? null)}</dd>
        <dt>Low-income tract</dt>
        <dd>{yesNo(access?.low_income)}</dd>
        <dt>Priority area</dt>
        <dd>{yesNo(access?.priority_area)}</dd>
      </dl>
      <p className="hint">GEOID {tract.geoid}</p>
    </section>
  )
}
