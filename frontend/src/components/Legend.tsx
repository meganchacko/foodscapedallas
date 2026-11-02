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

// "Dallas County median: 35.8%" for the selected tract's county, otherwise every county's
function medianText(medians: Record<string, number | null>, county: string | null): string {
  if (county !== null && medians[county] != null) {
    return `${county} County median: ${medians[county]}%`
  }
  const known = Object.entries(medians).filter(([, median]) => median !== null)
  if (known.length === 0) return ''
  return `County medians: ${known.map(([name, median]) => `${name} ${median}%`).join(', ')}`
}

type Props = {
  layerKind: TractLayerKind
  measure: Measure
  showPriority: boolean
  obesityMedians: Record<string, number | null>
  // the selected tract's county, whose median applies to it; null when no tract is selected
  selectedCounty: string | null
}

export function Legend({ layerKind, measure, showPriority, obesityMedians, selectedCounty }: Props) {
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
          </p>
          <p className="hint">{medianText(obesityMedians, selectedCounty)}</p>
          <p className="hint">{NOT_CAUSATION}</p>
        </div>
      )}
    </section>
  )
}
