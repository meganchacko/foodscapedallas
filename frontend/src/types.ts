// Shapes of the API responses. These mirror the Pydantic schemas in backend/app/schemas/.
import type { Feature, FeatureCollection, MultiPolygon, Point } from 'geojson'

export type Measure = 'usda_2019_supermarkets' | 'usda_2025_snap_retailers'

export type FoodAccess = {
  low_income: boolean | null
  low_access: boolean | null
  low_income_low_access: boolean | null
  low_access_population: number | null
  priority_area: boolean
}

export type TractProperties = {
  geoid: string
  population: number | null
  obesity_pct: number | null
  nearest_grocery_m: number | null
  food_access: Partial<Record<Measure, FoodAccess>>
}

export type TractFeature = Feature<MultiPolygon, TractProperties>

export type TractCollection = FeatureCollection<MultiPolygon, TractProperties> & {
  obesity_median_pct: number | null
}

export type PlaceType = 'grocery' | 'pantry' | 'farmers_market'

export type PlaceProperties = {
  id: number
  name: string
  type: PlaceType
  address: string | null
  hours: string | null
  accepts_snap: boolean | null
  accepts_wic: boolean | null
}

export type PlaceFeature = Feature<Point, PlaceProperties>

export type PlaceCollection = FeatureCollection<Point, PlaceProperties>

// Which data the tract colors show
export type TractLayerKind = 'food_access' | 'obesity'
