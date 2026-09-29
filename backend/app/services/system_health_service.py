from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.integration_health_check import IntegrationHealthCheck
from app.models.platform import ConnectedSystem
from app.models.transaction import InteroperabilityTransaction
from app.services.interoperability_service import interoperability_service

logger = logging.getLogger(__name__)


def check_integration_health(
    db: Session, system: ConnectedSystem
) -> dict[str, Any]:
    engine = interoperability_service.engine
    connector = engine.connector_for_system(system)
    started = perf_counter()
    error_message: str | None = None
    status = "offline"
    connector_mode: str | None = None

    if connector is None:
        error_message = f"No connector is configured for {system.name}."
    else:
        try:
            result = connector.health_check()
            connector_mode = result.get("mode") if isinstance(result, dict) else None
            if not isinstance(result, dict) or result.get("status") != "healthy":
                error_message = (
                    result.get("message") or result.get("error")
                    if isinstance(result, dict)
                    else None
                ) or "Connector health_check() did not report healthy."
                status = "degraded"
            else:
                status = "healthy" if system.is_active else "offline"
                if not system.is_active:
                    error_message = "The connected system is administratively disabled."
        except Exception as exc:
            logger.exception("Health check failed for connected system %s.", system.id)
            error_message = str(exc) or exc.__class__.__name__

    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    check = IntegrationHealthCheck(
        system_id=system.id,
        status=status,
        response_time_ms=elapsed_ms,
        error_message=error_message,
    )
    db.add(check)
    db.flush()

    previous_success = (
        db.query(func.max(IntegrationHealthCheck.checked_at))
        .filter(
            IntegrationHealthCheck.system_id == system.id,
            IntegrationHealthCheck.status == "healthy",
        )
        .scalar()
    )
    previous_failure = (
        db.query(func.max(IntegrationHealthCheck.checked_at))
        .filter(
            IntegrationHealthCheck.system_id == system.id,
            IntegrationHealthCheck.status != "healthy",
        )
        .scalar()
    )
    # The new probe is included in the counts and may be the latest result.
    latest_failure = (
        db.query(IntegrationHealthCheck)
        .filter(
            IntegrationHealthCheck.system_id == system.id,
            IntegrationHealthCheck.status != "healthy",
        )
        .order_by(IntegrationHealthCheck.checked_at.desc(), IntegrationHealthCheck.id.desc())
        .first()
    )
    failure_count = (
        db.query(IntegrationHealthCheck)
        .filter(
            IntegrationHealthCheck.system_id == system.id,
            IntegrationHealthCheck.status != "healthy",
        )
        .count()
    )

    transaction_filter = or_(
        InteroperabilityTransaction.source_system_id == system.id,
        InteroperabilityTransaction.destination_system_id == system.id,
    )
    last_successful_transaction = (
        db.query(func.max(InteroperabilityTransaction.completed_at))
        .filter(
            transaction_filter,
            InteroperabilityTransaction.status == "COMPLETED",
        )
        .scalar()
    )
    latest_failed_transaction = (
        db.query(InteroperabilityTransaction)
        .filter(
            transaction_filter,
            InteroperabilityTransaction.status.in_(("FAILED", "CONFLICT")),
        )
        .order_by(
            InteroperabilityTransaction.completed_at.desc(),
            InteroperabilityTransaction.requested_at.desc(),
        )
        .first()
    )
    transaction_failure_count = (
        db.query(InteroperabilityTransaction)
        .filter(
            transaction_filter,
            InteroperabilityTransaction.status.in_(("FAILED", "CONFLICT")),
        )
        .count()
    )
    last_failed_transaction_at = (
        latest_failed_transaction.completed_at or latest_failed_transaction.requested_at
        if latest_failed_transaction
        else None
    )
    latest_failure_at = max(
        (
            value
            for value in (previous_failure, last_failed_transaction_at)
            if value
        ),
        default=None,
    )
    last_failure_message = None
    if latest_failure and (
        not last_failed_transaction_at
        or latest_failure.checked_at >= last_failed_transaction_at
    ):
        last_failure_message = latest_failure.error_message
    elif latest_failed_transaction:
        last_failure_message = latest_failed_transaction.error_message
    return {
        "id": system.id,
        "slug": system.slug,
        "name": system.name,
        "department": system.department.name if system.department else None,
        "system_name": system.name,
        "connector_mode": connector_mode,
        "connectorMode": connector_mode,
        "status": status,
        "response_time": elapsed_ms,
        "last_successful_request": _iso(
            max(
                (
                    value
                    for value in (previous_success, last_successful_transaction)
                    if value
                ),
                default=None,
            )
        ),
        "last_failure": _iso(latest_failure_at),
        "last_failure_message": last_failure_message,
        "failure_count": failure_count + transaction_failure_count,
        "lastSuccessfulRequestAt": _iso(
            max(
                (
                    value
                    for value in (previous_success, last_successful_transaction)
                    if value
                ),
                default=None,
            )
        ),
        "lastFailureAt": _iso(latest_failure_at),
        "failureCount": failure_count + transaction_failure_count,
        "healthStatus": status,
        "connectionStatus": "connected" if status == "healthy" else "disconnected",
        "responseTimeMs": elapsed_ms,
        "transactionResponseTimeMs": None,
    }


def check_system_health(db: Session, systems: list[ConnectedSystem]) -> dict[str, Any]:
    started = perf_counter()
    integrations = [check_integration_health(db, system) for system in systems]
    db.commit()
    failures = sum(
        integration["status"] != "healthy" for integration in integrations
    )
    latest_success = max(
        (
            integration["last_successful_request"]
            for integration in integrations
            if integration["last_successful_request"]
        ),
        default=None,
    )
    latest_failure = max(
        (
            integration["last_failure"]
            for integration in integrations
            if integration["last_failure"]
        ),
        default=None,
    )
    return {
        "system_name": "SIH Interoperability Platform",
        "status": "healthy" if integrations and failures == 0 else "degraded",
        "response_time": round((perf_counter() - started) * 1000, 2),
        "last_successful_request": latest_success,
        "last_failure": latest_failure,
        "failure_count": sum(
            integration["failure_count"] for integration in integrations
        ),
        "integrations": integrations,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
