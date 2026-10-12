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

// GET /geocode
export type GeocodeResult = {
  lat: number
  lng: number
  display_name: string
}

// GET /places/nearby
export type NearbyPlace = PlaceProperties & {
  lat: number
  lng: number
  distance_m: number
}

export type SearchLocation = {
  lat: number
  lng: number
  in_dallas_county: boolean
  tract_geoid: string | null
  low_access: boolean | null
}

export type NearbyResponse = {
  location: SearchLocation
  radius_miles: number
  places: NearbyPlace[]
}

// Which tab the app shows
export type View = 'explore' | 'nearby' | 'health'

// POST /health-check (field names and values match backend/app/schemas/health_check.py)
export type HealthCheckAnswers = {
  sex: 'Female' | 'Male'
  age: number
  family_history_overweight: boolean
  high_calorie_food_often: boolean
  vegetables: number
  main_meals_per_day: number
  snacking: 'no' | 'Sometimes' | 'Frequently' | 'Always'
  smokes: boolean
  water: number
  tracks_calories: boolean
  physical_activity: number
  screen_time: number
  alcohol: 'no' | 'Sometimes' | 'Frequently' | 'Always'
  transportation: 'Automobile' | 'Bike' | 'Motorbike' | 'Public_Transportation' | 'Walking'
}

export type HealthCheckFactor = {
  field: keyof HealthCheckAnswers
  label: string
  effect: number
  direction: 'raises' | 'lowers'
  changeable: boolean
  actionable: boolean
}

export type HealthCheckResult = {
  probability: number
  model_version: string
  factors: HealthCheckFactor[]
  suggestion: { place_type: 'grocery' | 'farmers_market' | null; message: string } | null
  notes: string[]
  saved: boolean
}

// GET /model-card (only the parts the page shows)
export type Metrics = {
  n: number
  obese_share: number
  accuracy: number
  precision: number
  recall: number
  brier_score: number
  roc_auc?: number
  baseline_accuracy?: number
}

export type ModelCard = {
  name: string
  model_version: string
  trained_on: string
  intended_use: string
  not_intended_for: string[]
  training_data: {
    source: string
    citation: string
    license: string
    rows_used: number
    notes: string
  }
  target: string
  features: { name: string; description: string }[]
  excluded_features: { name: string; reason: string }[]
  model: { type: string; selection: string; train_rows: number }
  test_metrics: Metrics
  test_metrics_survey_like_rows: Metrics & { description: string }
  performance_by_group: Record<string, Record<string, Metrics>>
  synthetic_data_effects: string[]
  limitations: string[]
}
