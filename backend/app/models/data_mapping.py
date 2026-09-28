from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.model_base import PublicUUIDMixin, TimestampMixin


class DataMapping(PublicUUIDMixin, TimestampMixin, Base):
    __tablename__ = "data_mappings"
    __table_args__ = (
        UniqueConstraint(
            "source_system_id", "target_system_id", "name", "version",
            name="uq_data_mapping_system_pair_version",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    integration_id: Mapped[int | None] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_system_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )
    target_system_id: Mapped[int] = mapped_column(
        ForeignKey("connected_systems.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    source_schema_version: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    target_schema_version: Mapped[str] = mapped_column(String(40), default="1", nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    target: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    source_system = relationship("ConnectedSystem", foreign_keys=[source_system_id])
    target_system = relationship("ConnectedSystem", foreign_keys=[target_system_id])
    rules = relationship(
        "DataMappingRule", back_populates="mapping", cascade="all, delete-orphan"
    )


class DataMappingRule(TimestampMixin, Base):
    __tablename__ = "data_mapping_rules"
    __table_args__ = (
        UniqueConstraint("mapping_id", "source_field", "target_field", name="uq_data_mapping_field_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mapping_id: Mapped[int] = mapped_column(
        ForeignKey("data_mappings.id", ondelete="CASCADE"), index=True
    )
    source_field: Mapped[str] = mapped_column(String(160), nullable=False)
    target_field: Mapped[str] = mapped_column(String(160), nullable=False)
    transformation: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_expression: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    mapping = relationship("DataMapping", back_populates="rules")
