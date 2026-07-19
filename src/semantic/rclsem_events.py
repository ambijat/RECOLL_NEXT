#!/usr/bin/env python3
"""Small typed bridge from semantic components to the event ledger."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from rclsem_ledger import EventLedger


class EventSink(Protocol):
    def record(self, event_type: str, payload: Mapping[str, Any]) -> None:
        ...


@dataclass(frozen=True)
class LedgerEventSink:
    ledger: EventLedger
    actor: str
    session_id: str

    def record(self, event_type: str, payload: Mapping[str, Any]) -> None:
        self.ledger.append(
            event_type,
            actor=self.actor,
            session_id=self.session_id,
            payload=payload,
        )
