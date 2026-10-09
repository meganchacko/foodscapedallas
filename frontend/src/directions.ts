// Builds a Google Maps link that opens public transit directions. Google publishes this URL
// format ("Maps URLs") for exactly this: no API key, nothing to install.
// https://developers.google.com/maps/documentation/urls/get-started#directions-action

const GOOGLE_MAPS_DIRECTIONS = 'https://www.google.com/maps/dir/'

type Point = { lat: number; lng: number }
type Destination = Point & { address: string | null }

export function directionsUrl(origin: Point, destination: Destination): string {
  const params = new URLSearchParams({
    api: '1',
    origin: `${origin.lat},${origin.lng}`,
    // The street address alone, which Google resolves to one spot and routes right away.
    // (Tested: adding the store name made Google ask "Did you mean...?" when several listings
    // shared the name.) Without an address, use the exact coordinates.
    destination: destination.address ?? `${destination.lat},${destination.lng}`,
    // Opens on the bus/train tab (DART in Dallas); the user can still switch to walk or drive
    travelmode: 'transit',
  })
  return `${GOOGLE_MAPS_DIRECTIONS}?${params}`
}
