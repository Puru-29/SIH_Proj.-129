from pydantic import BaseModel, ConfigDict


class ServiceCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    is_active: bool = True
    department_id: int
    platform_id: int


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str | None
    is_active: bool
    department_id: int
    platform_id: int
