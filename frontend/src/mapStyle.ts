// Map colors and labels in one place, so the map, legend, and panel always agree.
// Colors come from the validated data-viz palette: one blue ramp for tract values (light = less).
// Pins avoid blue so a pin never looks like part of the tract shading: grocery stores (the
// most common) are near-black, the other types take the palette's orange and aqua.
import type { Measure, PlaceType, TractProperties } from './types'

export const MEASURE_LABELS: Record<Measure, string> = {
  usda_2019_supermarkets: 'Supermarkets (USDA 2019)',
  usda_2025_snap_retailers: 'Any SNAP store (USDA 2025)',
}

export const MEASURE_DESCRIPTIONS: Record<Measure, string> = {
  usda_2019_supermarkets: 'Counts supermarkets and large grocery stores as food access.',
  usda_2025_snap_retailers:
    'Counts any store that accepts SNAP, including convenience and dollar stores.',
}

export const NO_DATA_COLOR = '#e1e0d9'

// Food access: three ordered classes
export const FOOD_ACCESS_CLASSES = [
  { label: 'Not low access', color: '#f0efec' },
  { label: 'Low access', color: '#86b6ef' },
  { label: 'Low income and low access', color: '#1c5cab' },
] as const

// Obesity: five bins of adult obesity %, light to dark
export const OBESITY_BINS = [
  { label: 'Under 30%', max: 30, color: '#86b6ef' },
  { label: '30–35%', max: 35, color: '#5598e7' },
  { label: '35–40%', max: 40, color: '#2a78d6' },
  { label: '40–45%', max: 45, color: '#1c5cab' },
  { label: '45% and up', max: Infinity, color: '#0d366b' },
] as const

export const PLACE_TYPES: { type: PlaceType; label: string; color: string }[] = [
  { type: 'grocery', label: 'Grocery stores', color: '#0b0b0b' },
  { type: 'pantry', label: 'Food pantries', color: '#eb6834' },
  { type: 'farmers_market', label: 'Farmers markets', color: '#1baf7a' },
]

export const PLACE_COLORS = Object.fromEntries(
  PLACE_TYPES.map(({ type, color }) => [type, color]),
) as Record<PlaceType, string>

export function foodAccessColor(tract: TractProperties, measure: Measure): string {
  const access = tract.food_access[measure]
  if (!access || access.low_access === null) return NO_DATA_COLOR
  if (access.low_income_low_access) return FOOD_ACCESS_CLASSES[2].color
  if (access.low_access) return FOOD_ACCESS_CLASSES[1].color
  return FOOD_ACCESS_CLASSES[0].color
}

export function obesityColor(tract: TractProperties): string {
  if (tract.obesity_pct === null) return NO_DATA_COLOR
  const bin = OBESITY_BINS.find((b) => tract.obesity_pct! < b.max)
  return (bin ?? OBESITY_BINS[OBESITY_BINS.length - 1]).color
}

export const METERS_PER_MILE = 1609.344

export function formatMiles(meters: number | null): string {
  if (meters === null) return 'Unknown'
  return `${(meters / METERS_PER_MILE).toFixed(1)} mi`
}

export function formatNumber(value: number | null): string {
  return value === null ? 'Unknown' : value.toLocaleString()
}
