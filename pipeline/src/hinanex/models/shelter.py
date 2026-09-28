from pydantic import BaseModel, ConfigDict, Field


class ShelterRecord(BaseModel):
    """HINANEX common schema for evacuation facilities.

    Coordinates are nullable so a source record can survive normalization even
    when the municipality publishes only an address. Missing coordinates are a
    data-quality/application-readiness finding, not a reason to discard the row.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    address: str | None = None
    administrative_area: str | None = None

    facility_type: str | None = None

    # None = source does not let HINANEX determine supported disasters safely.
    # []   = source explicitly shows no supported disaster among parsed columns.
    supported_disasters: list[str] | None = None

    accessibility: bool | None = None
    capacity: int | None = Field(default=None, ge=0)

    detail_url: str | None = None
    notes: str | None = None
