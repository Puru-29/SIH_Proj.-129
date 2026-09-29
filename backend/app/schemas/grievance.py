from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class GrievanceCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    category: str = Field(min_length=1, max_length=120)
    related_application: str | None = Field(
        default=None,
        max_length=80,
        validation_alias=AliasChoices("relatedApplication", "related_application"),
    )
    department: str | None = Field(default=None, max_length=160)
    description: str = Field(min_length=1, max_length=5000)
    priority: str = Field(default="Normal", min_length=1, max_length=24)

    @field_validator("category", "description", "priority")
    @classmethod
    def require_non_whitespace(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank.")
        return normalized

    @field_validator("related_application", "department")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
