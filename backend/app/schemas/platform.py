from pydantic import BaseModel, ConfigDict, HttpUrl

from app.models.platform import PlatformStatus


class PlatformCreate(BaseModel):
    name: str
    slug: str
    base_url: HttpUrl | None = None
    api_version: str = "v1"
    status: PlatformStatus = PlatformStatus.ACTIVE
    description: str | None = None
    department_id: int


class PlatformRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    base_url: str | None
    api_version: str
    status: PlatformStatus
    description: str | None
    department_id: int
