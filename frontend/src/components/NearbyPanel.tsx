import { type FormEvent, useState } from 'react'
import { PLACE_COLORS, PLACE_TYPES, formatMiles } from '../mapStyle'
import { RADIUS_OPTIONS, type NearbySearch } from '../useNearbySearch'
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
          <ResultsList
            places={search.places}
            selectedPlaceId={search.selectedPlaceId}
            onSelect={search.setSelectedPlaceId}
          />
        </>
      )}
    </section>
  )
}

type ResultsListProps = {
  places: NearbyPlace[]
  selectedPlaceId: number | null
  onSelect: (id: number) => void
}

function ResultsList({ places, selectedPlaceId, onSelect }: ResultsListProps) {
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
        </li>
      ))}
    </ol>
  )
}
