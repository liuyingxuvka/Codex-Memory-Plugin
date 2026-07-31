"""Thin loader for the canonical Chaos Brain behavior commitment ledger."""

from __future__ import annotations

import json
from pathlib import Path

from flowguard import BehaviorCommitmentLedger, load_behavior_commitment_ledger, write_behavior_commitment_ledger


LEDGER_PATH = Path(__file__).with_name("ledger.json")


def build_ledger() -> BehaviorCommitmentLedger:
    """Load the sole current JSON authority without executing a duplicate inventory."""
    try:
        ledger = load_behavior_commitment_ledger(LEDGER_PATH)
        needs_source_upgrade = any(
            str(surface.surface_kind) == "openspec"
            for surface in ledger.source_surfaces
        ) or not ledger.expected_source_surface_ids
        if not needs_source_upgrade:
            return ledger
        payload = ledger.to_dict()
        payload["expected_source_surface_ids"] = [
            str(surface.get("surface_id") or "")
            for surface in payload.get("source_surfaces") or []
            if str(surface.get("surface_id") or "")
        ]
        for surface in payload.get("source_surfaces") or []:
            if isinstance(surface, dict) and surface.get("surface_kind") == "openspec":
                surface["surface_kind"] = "doc"
        migrated = BehaviorCommitmentLedger(**payload)
        write_behavior_commitment_ledger(LEDGER_PATH, migrated)
        return migrated
    except ValueError as exc:
        # One-time author-side direct migration for the FlowGuard package's
        # current source-surface fields.  This is not a product-runtime
        # compatibility reader: the official writer replaces the source file
        # and every later consumer reads only the current canonical shape.
        raw = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        payload = dict(raw.get("ledger") or {})
        payload.setdefault("subject_lane", "normative_target")
        payload.setdefault("expected_source_surface_ids", [])
        payload.setdefault("source_inventory_revision", "")
        payload.setdefault("source_inventory_fingerprint", "")
        payload.setdefault("source_inventory_evidence_ids", [])
        payload.setdefault("require_complete_source_inventory", False)
        for surface in payload.get("source_surfaces") or []:
            if not isinstance(surface, dict):
                continue
            surface.setdefault("source_system_id", "")
            surface.setdefault("native_artifact_id", "")
            surface.setdefault("content_fingerprint", "")
            surface.setdefault("inventory_revision", "")
            surface.setdefault("discovery_evidence_ids", [])
            surface.setdefault("source_authority_role", "normative")
            surface.setdefault("declared_semantics_fingerprint", "")
            surface.setdefault("coverage_disposition", "modeled")
            surface.setdefault("delegated_owner_inventory_id", "")
            surface.setdefault("delegation_relation_type", "")
            surface.setdefault("native_evidence_ids", [])
        migrated = BehaviorCommitmentLedger(**payload)
        write_behavior_commitment_ledger(LEDGER_PATH, migrated)
        return migrated
