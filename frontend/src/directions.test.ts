import { describe, expect, it } from 'vitest'
import { directionsUrl } from './directions'

const CITY_HALL = { lat: 32.7763, lng: -96.7969 }

// Read the link back the way Google will, instead of comparing raw encoded strings
function params(url: string) {
  return new URL(url).searchParams
}

describe('directionsUrl', () => {
  it('opens Google Maps transit directions from the origin', () => {
    const url = directionsUrl(CITY_HALL, {
      lat: 32.7781,
      lng: -96.79,
      address: '1010 S Pearl Expy, Dallas 75201',
    })

    expect(url.startsWith('https://www.google.com/maps/dir/?')).toBe(true)
    expect(params(url).get('api')).toBe('1')
    expect(params(url).get('travelmode')).toBe('transit')
    expect(params(url).get('origin')).toBe('32.7763,-96.7969')
  })

  it('uses the street address as the destination when there is one', () => {
    const url = directionsUrl(CITY_HALL, {
      lat: 32.7781,
      lng: -96.79,
      address: '1010 S Pearl Expy, Dallas 75201',
    })

    expect(params(url).get('destination')).toBe('1010 S Pearl Expy, Dallas 75201')
  })

  it('falls back to coordinates when there is no address', () => {
    const url = directionsUrl(CITY_HALL, { lat: 32.7781, lng: -96.79, address: null })

    expect(params(url).get('destination')).toBe('32.7781,-96.79')
  })

  it('encodes characters that would otherwise break the link', () => {
    const url = directionsUrl(CITY_HALL, { lat: 0, lng: 0, address: "Joe's #5 & Co, Dallas" })

    expect(params(url).get('destination')).toBe("Joe's #5 & Co, Dallas")
  })
})
