from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.data_mapping import DataMapping, DataMappingRule
from app.models.platform import ConnectedSystem


REQUIRED_CITIZEN_FIELDS = {"name", "date_of_birth", "identifier"}

DEFAULT_MAPPING_RULES: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "revenue": (
        ("full_name", "name", True),
        ("dob", "date_of_birth", True),
        ("income_certificate_no", "identifier", True),
        ("income_certificate_no", "certificate_number", False),
        ("annual_income", "annual_income", False),
    ),
    "education": (
        ("student_name", "name", True),
        ("date_of_birth", "date_of_birth", True),
        ("student_id", "identifier", True),
        ("institution", "institution", False),
    ),
    "welfare": (
        ("applicant_name", "name", True),
        ("eligibility_id", "identifier", True),
        ("scheme_name", "record_type", False),
        ("eligibility_status", "verification_status", False),
    ),
    "transport": (
        ("applicantName", "name", True),
        ("birthDate", "date_of_birth", True),
        ("licenseNumber", "identifier", True),
        ("licenseNumber", "license_number", False),
    ),
    "municipal": (
        ("owner_name", "name", True),
        ("property_id", "identifier", True),
        ("assessment_status", "verification_status", False),
    ),
    "employment": (
        ("applicant_name", "name", True),
        ("date_of_birth", "date_of_birth", True),
        ("employment_id", "identifier", True),
        ("employer_name", "employer", False),
        ("employment_status", "employment_status", False),
        ("occupation", "occupation", False),
    ),
}


class MappingConfigurationError(ValueError):
    pass


class MappingService:
    def get_or_create_active_mapping(
        self,
        db: Session,
        *,
        source_system: ConnectedSystem,
        target_system_id: int,
        connector_key: str,
    ) -> DataMapping:
        mapping = self._active_mapping(
            db,
            source_system_id=source_system.id,
            target_system_id=target_system_id,
        )
        if mapping is not None:
            return mapping

        rules = DEFAULT_MAPPING_RULES.get(connector_key)
        if rules is None:
            raise MappingConfigurationError(
                f"No database mapping configuration exists for source '{connector_key}'."
            )
        mapping = DataMapping(
            source_system_id=source_system.id,
            target_system_id=target_system_id,
            name=f"{connector_key}-to-govflow-cdm",
            source_schema_version="1",
            target_schema_version="1",
            source=source_system.name,
            target="GovFlow Common Data Model",
            status="active",
            version=1,
        )
        db.add(mapping)
        db.flush()
        db.add_all(
            DataMappingRule(
                mapping_id=mapping.id,
                source_field=source_field,
                target_field=target_field,
                is_required=is_required,
            )
            for source_field, target_field, is_required in rules
        )
        db.flush()
        return self._mapping_with_rules(db, mapping.id)

    def map_to_common_model(
        self,
        db: Session,
        *,
        raw: dict[str, Any],
        citizen_id: int,
        source_system: ConnectedSystem,
        target_system_id: int,
        requested_type: str,
        connector_key: str,
    ) -> dict[str, Any]:
        mapping = self.get_or_create_active_mapping(
            db,
            source_system=source_system,
            target_system_id=target_system_id,
            connector_key=connector_key,
        )
        mapped: dict[str, Any] = {}
        missing_required: set[str] = set()
        mapping_conflicts: dict[str, list[dict[str, Any]]] = {}
        for rule in mapping.rules:
            value = raw.get(rule.source_field)
            if value is None or value == "":
                if rule.is_required:
                    missing_required.add(rule.target_field)
                continue
            if rule.target_field in mapped:
                if mapped[rule.target_field] != value:
                    evidence = mapping_conflicts.setdefault(rule.target_field, [])
                    if not evidence:
                        first_rule = next(
                            item
                            for item in mapping.rules
                            if item.target_field == rule.target_field
                            and raw.get(item.source_field) == mapped[rule.target_field]
                        )
                        evidence.append(
                            {
                                "source_field": first_rule.source_field,
                                "value": mapped[rule.target_field],
                            }
                        )
                    evidence.append({"source_field": rule.source_field, "value": value})
                continue
            mapped[rule.target_field] = value

        missing_required.update(REQUIRED_CITIZEN_FIELDS - mapped.keys())
        mapped["citizen_id"] = str(citizen_id)
        mapped["record_type"] = mapped.get("record_type") or requested_type
        mapped["source_system"] = source_system.name
        mapped["source_department"] = (
            source_system.department.name if source_system.department else source_system.name
        )
        mapped["verification_status"] = "UNVERIFIED"
        mapped["details"] = {
            key: value
            for key, value in raw.items()
            if value is not None and key not in {"purpose", "citizen_id"}
        }
        mapped["mapping_conflicts"] = mapping_conflicts
        mapped["missing_required_fields"] = sorted(missing_required)
        mapped["mapping_id"] = mapping.id
        mapped["mapping_version"] = mapping.version
        return mapped

    def list_mappings(self, db: Session) -> list[DataMapping]:
        return (
            db.query(DataMapping)
            .options(
                joinedload(DataMapping.rules),
                joinedload(DataMapping.source_system),
                joinedload(DataMapping.target_system),
            )
            .order_by(DataMapping.source_system_id, DataMapping.name, DataMapping.version.desc())
            .all()
        )

    def _active_mapping(
        self,
        db: Session,
        *,
        source_system_id: int,
        target_system_id: int,
    ) -> DataMapping | None:
        return (
            db.query(DataMapping)
            .options(joinedload(DataMapping.rules))
            .filter(
                DataMapping.source_system_id == source_system_id,
                DataMapping.target_system_id == target_system_id,
                DataMapping.status == "active",
            )
            .order_by(DataMapping.version.desc())
            .first()
        )

    @staticmethod
    def _mapping_with_rules(db: Session, mapping_id: int) -> DataMapping:
        mapping = (
            db.query(DataMapping)
            .options(joinedload(DataMapping.rules))
            .filter(DataMapping.id == mapping_id)
            .first()
        )
        if mapping is None:
            raise MappingConfigurationError(
                f"Mapping configuration {mapping_id} could not be loaded."
            )
        return mapping
