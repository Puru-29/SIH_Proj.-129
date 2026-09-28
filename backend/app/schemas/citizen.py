from pydantic import BaseModel, ConfigDict


class CitizenRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    citizenId: str
    name: str
    dateOfBirth: str
    mobile: str | None = None
    email: str | None = None
