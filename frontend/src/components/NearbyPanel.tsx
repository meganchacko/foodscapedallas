import { type FormEvent, useState } from 'react'
import { PLACE_COLORS, PLACE_TYPES, formatMiles } from '../mapStyle'
import { directionsUrl } from '../directions'
import { RADIUS_OPTIONS, type NearbySearch, type SearchPoint } from '../useNearbySearch'
import type { NearbyPlace } from '../types'

const TYPE_LABELS = Object.fromEntries(PLACE_TYPES.map(({ type, label }) => [type, label]))

export function NearbyPanel({ search }: { search: NearbySearch }) {
  const [query, setQuery] = useState('')
  const busy = search.locating || search.searching

  function onSubmit(event: FormEvent) {
    event.preventDefault() // stop the browser from reloading the page on submit
    search.searchAddress(query)
  }

  return (
    <section className="nearby">
      <form onSubmit={onSubmit} className="search-form">
        <label htmlFor="address">Address or place</label>
        <div className="search-row">
          <input
            id="address"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="e.g. 1500 Marilla St, Dallas"
            autoComplete="street-address"
          />
          <button type="submit" disabled={busy}>
            Search
          </button>
        </div>
        <button type="button" className="link-button" onClick={search.locateMe} disabled={busy}>
          Use my location
        </button>
      </form>

      <fieldset>
        <legend>Within</legend>
        <select
          value={search.radiusMiles}
          onChange={(event) => search.setRadiusMiles(Number(event.target.value))}
          aria-label="Search radius"
        >
          {RADIUS_OPTIONS.map((miles) => (
            <option key={miles} value={miles}>
              {miles} {miles === 1 ? 'mile' : 'miles'}
            </option>
          ))}
        </select>
      </fieldset>

      <fieldset>
        <legend>Show</legend>
        {PLACE_TYPES.map(({ type, label, color }) => (
          <label key={type} className="option">
            <input
              type="checkbox"
              checked={search.visibleTypes.has(type)}
              onChange={() => search.toggleType(type)}
            />
            <span className="swatch dot" style={{ background: color }} aria-hidden="true" />
            {label}
          </label>
        ))}
        <label className="option">
          <input
            type="checkbox"
            checked={search.snapOnly}
            onChange={(event) => search.setSnapOnly(event.target.checked)}
          />
          Accepts SNAP only
        </label>
      </fieldset>

      {busy && <p className="hint">Searching…</p>}
      {search.error && (
        <p className="error" role="alert">
          {search.error}
        </p>
      )}

      {search.point && search.response && !busy && (
        <>
          <p className="hint">Near: {search.point.label}</p>
          <LocationNotices search={search} />
          <ResultsList
            origin={search.point}
            places={search.places}
            selectedPlaceId={search.selectedPlaceId}
            onSelect={search.setSelectedPlaceId}
          />
        </>
      )}
    </section>
  )
}

// Messages about the searched location and its results
function LocationNotices({ search }: { search: NearbySearch }) {
  const location = search.response!.location
  const nextRadius = RADIUS_OPTIONS.find((miles) => miles > search.radiusMiles)
  const filtersOn = search.snapOnly || search.visibleTypes.size < PLACE_TYPES.length

  return (
    <>
      {!location.in_dallas_county && (
        <p className="notice" role="status">
          This location is outside Dallas County. FoodScape only covers Dallas County, so places
          across the county line won't appear.
        </p>
      )}
      {location.low_access && (
        <p className="notice" role="status">
          <strong>This area has low food access.</strong> USDA data shows many residents here live
          more than a mile from a supermarket. Food pantries and farmers markets near you are listed
          below too.
        </p>
      )}
      {search.places.length === 0 && (
        <div className="notice" role="status">
          <p>
            Nothing found within {search.radiusMiles} {search.radiusMiles === 1 ? 'mile' : 'miles'}
            {filtersOn && ' with these filters'}.
          </p>
          {nextRadius && (
            <button
              type="button"
              className="link-button"
              onClick={() => search.setRadiusMiles(nextRadius)}
            >
              Search within {nextRadius} miles
            </button>
          )}
        </div>
      )}
    </>
  )
}

type ResultsListProps = {
  origin: SearchPoint
  places: NearbyPlace[]
  selectedPlaceId: number | null
  onSelect: (id: number) => void
}

function ResultsList({ origin, places, selectedPlaceId, onSelect }: ResultsListProps) {
  return (
    <ol className="results" aria-label="Nearby places, closest first">
      {places.map((place) => (
        <li key={place.id}>
          <button
            type="button"
            className={place.id === selectedPlaceId ? 'result selected' : 'result'}
            onClick={() => onSelect(place.id)}
          >
            <span className="result-title">
              <span
                className="swatch dot"
                style={{ background: PLACE_COLORS[place.type] }}
                aria-hidden="true"
              />
              {place.name}
              <span className="result-distance">{formatMiles(place.distance_m)}</span>
            </span>
            <span className="result-detail">
              {TYPE_LABELS[place.type]}
              {place.accepts_snap && ' · Accepts SNAP'}
            </span>
            {place.address && <span className="result-detail">{place.address}</span>}
            {place.hours && <span className="result-detail">Hours: {place.hours}</span>}
          </button>
          {/* A link, not inside the button above: interactive elements can't be nested */}
          <DirectionsLink origin={origin} place={place} />
        </li>
      ))}
    </ol>
  )
}

export function DirectionsLink({ origin, place }: { origin: SearchPoint; place: NearbyPlace }) {
  return (
    <a
      className="directions-link"
      href={directionsUrl(origin, place)}
      // new tab; noopener stops the new page from controlling this one, noreferrer hides our URL
      target="_blank"
      rel="noopener noreferrer"
    >
      Transit directions (opens Google Maps)
    </a>
  )
}
