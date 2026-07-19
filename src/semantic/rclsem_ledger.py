#!/usr/bin/env python3
"""Local append-only, SHA-256 hash-chained event ledger.

The ledger deliberately contains no distributed-consensus or cryptocurrency
features. It provides a small, dependency-free audit primitive for Recoll Next.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import errno
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, Iterator, Mapping, Optional, TextIO, Tuple


SCHEMA = "recoll.event.v1"
GENESIS_HASH = "0" * 64
EVENT_FIELDS = {
    "schema",
    "sequence",
    "timestamp",
    "event_type",
    "actor",
    "session_id",
    "payload",
    "previous_hash",
    "hash",
}
EVENT_TYPE_RE = re.compile(r"^[a-z][a-z0-9_-]*(?:\.[a-z0-9_-]+)+$")
IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/+-]{0,127}$")


class LedgerError(Exception):
    """Base error raised by the event ledger."""


class LedgerLockError(LedgerError):
    """Raised when the ledger's inter-process lock cannot be acquired."""


class LedgerVerificationError(LedgerError):
    """Raised at the first event that violates the ledger contract."""

    def __init__(self, line_number: int, reason: str):
        self.line_number = line_number
        self.reason = reason
        super().__init__(f"ledger verification failed at line {line_number}: {reason}")


@dataclass(frozen=True)
class VerificationReport:
    """Summary returned after a successful full-chain verification."""

    event_count: int
    head_hash: str


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as ex:
        raise LedgerError(f"value is not canonical JSON data: {ex}") from ex


def _event_hash(event_without_hash: Mapping[str, Any]) -> str:
    encoded = _canonical_json(event_without_hash).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def _validate_timestamp(value: Any) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise LedgerError("timestamp must be an ISO-8601 UTC string ending in 'Z'")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as ex:
        raise LedgerError("timestamp must be a valid ISO-8601 UTC value") from ex


def _normalized_payload(payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    if payload is None:
        return {}
    if not isinstance(payload, Mapping):
        raise LedgerError("payload must be a JSON object")
    # A JSON round trip freezes mapping subclasses and rejects unsupported values.
    return json.loads(_canonical_json(dict(payload)))


@contextmanager
def _exclusive_file_lock(path: Path, timeout_seconds: float) -> Iterator[None]:
    """Take an advisory cross-process lock using a sibling lock file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_stream = path.open("a+b")
    try:
        lock_stream.seek(0, os.SEEK_END)
        if lock_stream.tell() == 0:
            lock_stream.write(b"\0")
            lock_stream.flush()

        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                lock_stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock_stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as ex:
                if ex.errno not in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                    raise LedgerLockError(f"could not lock {path}: {ex}") from ex
                if time.monotonic() >= deadline:
                    raise LedgerLockError(
                        f"timed out waiting for ledger lock {path}"
                    ) from ex
                time.sleep(0.05)

        try:
            yield
        finally:
            lock_stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(lock_stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
    finally:
        lock_stream.close()


class EventLedger:
    """Append and verify events in one local JSONL hash chain."""

    def __init__(self, path: os.PathLike[str] | str, lock_timeout: float = 10.0):
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.lock_timeout = lock_timeout

    def append(
        self,
        event_type: str,
        *,
        actor: str,
        session_id: str,
        payload: Optional[Mapping[str, Any]] = None,
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate the existing chain, append one event, flush, and fsync."""

        self._validate_identity_fields(event_type, actor, session_id)
        normalized_payload = _normalized_payload(payload)
        event_timestamp = timestamp or _utc_now()
        _validate_timestamp(event_timestamp)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _exclusive_file_lock(self.lock_path, self.lock_timeout):
            report = self._verify_unlocked()
            event: Dict[str, Any] = {
                "schema": SCHEMA,
                "sequence": report.event_count + 1,
                "timestamp": event_timestamp,
                "event_type": event_type,
                "actor": actor,
                "session_id": session_id,
                "payload": normalized_payload,
                "previous_hash": report.head_hash,
            }
            event["hash"] = _event_hash(event)
            serialized = _canonical_json(event) + "\n"

            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(serialized)
                stream.flush()
                os.fsync(stream.fileno())
            return event

    def verify(self) -> VerificationReport:
        """Verify the complete ledger while preventing concurrent appends."""

        with _exclusive_file_lock(self.lock_path, self.lock_timeout):
            return self._verify_unlocked()

    def read_verified(self) -> Tuple[Dict[str, Any], ...]:
        """Return a stable snapshot only after verifying its complete chain."""

        with _exclusive_file_lock(self.lock_path, self.lock_timeout):
            self._verify_unlocked()
            if not self.path.exists():
                return ()
            with self.path.open("r", encoding="utf-8") as stream:
                return tuple(json.loads(line) for line in stream)

    @staticmethod
    def _validate_identity_fields(event_type: str, actor: str, session_id: str) -> None:
        if not isinstance(event_type, str) or not EVENT_TYPE_RE.fullmatch(event_type):
            raise LedgerError(
                "event_type must be a lower-case namespace such as 'search.semantic.started'"
            )
        for name, value in (("actor", actor), ("session_id", session_id)):
            if not isinstance(value, str) or not IDENTITY_RE.fullmatch(value):
                raise LedgerError(f"{name} contains unsupported characters or length")

    def _verify_unlocked(self) -> VerificationReport:
        if not self.path.exists():
            return VerificationReport(0, GENESIS_HASH)

        previous_hash = GENESIS_HASH
        event_count = 0
        try:
            stream: TextIO
            with self.path.open("r", encoding="utf-8") as stream:
                for line_number, line in enumerate(stream, start=1):
                    if not line.endswith("\n"):
                        raise LedgerVerificationError(
                            line_number, "event is not terminated by a newline"
                        )
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError as ex:
                        raise LedgerVerificationError(
                            line_number, f"invalid JSON: {ex.msg}"
                        ) from ex
                    self._verify_event(event, line_number, previous_hash)
                    previous_hash = event["hash"]
                    event_count += 1
        except UnicodeDecodeError as ex:
            raise LedgerVerificationError(event_count + 1, "invalid UTF-8") from ex

        return VerificationReport(event_count, previous_hash)

    @staticmethod
    def _verify_event(event: Any, line_number: int, previous_hash: str) -> None:
        if not isinstance(event, dict):
            raise LedgerVerificationError(line_number, "event must be a JSON object")
        if set(event) != EVENT_FIELDS:
            missing = sorted(EVENT_FIELDS - set(event))
            extra = sorted(set(event) - EVENT_FIELDS)
            raise LedgerVerificationError(
                line_number, f"field mismatch; missing={missing}, extra={extra}"
            )
        if event["schema"] != SCHEMA:
            raise LedgerVerificationError(line_number, "unsupported schema")
        if (
            not isinstance(event["sequence"], int)
            or isinstance(event["sequence"], bool)
            or event["sequence"] != line_number
        ):
            raise LedgerVerificationError(line_number, "sequence is not contiguous")
        if event["previous_hash"] != previous_hash:
            raise LedgerVerificationError(line_number, "previous hash does not match")
        try:
            EventLedger._validate_identity_fields(
                event["event_type"], event["actor"], event["session_id"]
            )
            _validate_timestamp(event["timestamp"])
        except LedgerError as ex:
            raise LedgerVerificationError(line_number, str(ex)) from ex
        if not isinstance(event["payload"], dict):
            raise LedgerVerificationError(line_number, "payload is not an object")
        supplied_hash = event["hash"]
        if not isinstance(supplied_hash, str):
            raise LedgerVerificationError(line_number, "hash is not a string")
        unsigned_event = {key: value for key, value in event.items() if key != "hash"}
        try:
            expected_hash = _event_hash(unsigned_event)
        except LedgerError as ex:
            raise LedgerVerificationError(line_number, str(ex)) from ex
        if not hmac.compare_digest(supplied_hash, expected_hash):
            raise LedgerVerificationError(line_number, "event hash does not match")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    verify_parser = subparsers.add_parser("verify", help="verify a complete ledger")
    verify_parser.add_argument("path")

    append_parser = subparsers.add_parser("append", help="append one JSON event")
    append_parser.add_argument("path")
    append_parser.add_argument("event_type")
    append_parser.add_argument("--actor", required=True)
    append_parser.add_argument("--session", required=True, dest="session_id")
    append_parser.add_argument("--payload", default="{}", help="JSON object")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    ledger = EventLedger(args.path)
    try:
        if args.command == "verify":
            report = ledger.verify()
            print(
                _canonical_json(
                    {"event_count": report.event_count, "head_hash": report.head_hash}
                )
            )
        else:
            payload = json.loads(args.payload)
            event = ledger.append(
                args.event_type,
                actor=args.actor,
                session_id=args.session_id,
                payload=payload,
            )
            print(_canonical_json(event))
    except (json.JSONDecodeError, LedgerError) as ex:
        print(str(ex), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
