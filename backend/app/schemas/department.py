from pydantic import BaseModel, ConfigDict


class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    state: str = "Maharashtra"


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str | None
    state: str
