from pydantic import BaseModel


class GeocodeResponse(BaseModel):
    lat: float
    lng: float
    display_name: str  # Nominatim's full address, so the user can confirm it found the right place
