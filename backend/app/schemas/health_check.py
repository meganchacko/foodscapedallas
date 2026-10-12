"""Request and response shapes for POST /health-check.

The API uses plain field names (vegetables, physical_activity, ...). app/services/health_check.py
translates them into the dataset's column names and values, which is what the model expects.
"""

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

Frequency = Literal["no", "Sometimes", "Frequently", "Always"]
Transportation = Literal["Automobile", "Bike", "Motorbike", "Public_Transportation", "Walking"]


class HealthCheckRequest(BaseModel):
    sex: Literal["Female", "Male"]
    # The training data covers ages 14-61; the tool is for adults, and over 61 gets a note
    age: int = Field(ge=18, le=100)
    family_history_overweight: bool
    high_calorie_food_often: bool
    vegetables: int = Field(ge=1, le=3, description="1 never, 2 sometimes, 3 always")
    main_meals_per_day: int = Field(ge=1, le=4)
    snacking: Frequency
    smokes: bool
    water: int = Field(ge=1, le=3, description="1 under 1 L, 2 1-2 L, 3 over 2 L per day")
    tracks_calories: bool
    physical_activity: int = Field(
        ge=0, le=3, description="0 none, 1 1-2 days, 2 2-4 days, 3 4-5 days a week"
    )
    screen_time: int = Field(ge=0, le=2, description="0 0-2 h, 1 3-5 h, 2 over 5 h a day")
    alcohol: Frequency
    transportation: Transportation

    # Nothing is stored unless the user opts in
    save: bool = False
    # A random ID made by the browser, so saved results aren't linked to a person. Required to
    # save; ignored otherwise.
    anonymous_id: UUID | None = None

    @model_validator(mode="after")
    def anonymous_id_needed_to_save(self) -> Self:
        if self.save and self.anonymous_id is None:
            raise ValueError("anonymous_id is required when save is true")
        return self


class Factor(BaseModel):
    field: str  # the request field, e.g. "physical_activity"
    label: str  # plain language, e.g. "Physical activity"
    # How much this answer moved the estimate compared with an average respondent, on the
    # log-odds scale the model uses. Positive raises the estimate, negative lowers it.
    effect: float
    direction: Literal["raises", "lowers"]
    changeable: bool  # a habit (vs. age, sex, family history)
    # A changeable habit where moving toward the healthier answer would lower this estimate.
    # Only these are shown as suggestions (see services/health_check.py).
    actionable: bool


class ResourceSuggestion(BaseModel):
    place_type: Literal["grocery", "farmers_market"] | None
    message: str


class HealthCheckResponse(BaseModel):
    probability: float = Field(ge=0, le=1)
    model_version: str
    factors: list[Factor]  # largest effect first
    suggestion: ResourceSuggestion | None
    notes: list[str]  # caveats that apply to these answers
    saved: bool
