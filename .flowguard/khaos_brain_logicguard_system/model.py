"""Observed parent boundary for the Khaos Brain LogicGuard maintenance system.

The detailed executable behavior remains in the existing Khaos-owned FlowGuard
models.  This parent declares which current child owns the two-scheduled-task
composition so FlowGuard's model-system authority can inventory and revision the
observed implementation without creating another scheduler or product owner.
"""

from __future__ import annotations


MODEL_ID = "khaos_brain_logicguard_system"
CHILD_MODEL_ID = "khaos_brain_two_maintenance_cycle_flow"
CHILD_MODEL_PATH = ".flowguard/khaos_brain_two_maintenance_cycle_flow.py"

PROTECTED_FAILURE_IDS = (
    "khaos-cycle:view-counted-as-use",
    "khaos-cycle:local-block-suppresses-organization",
    "khaos-cycle:dream-publishes-authority",
    "khaos-cycle:task-time-network-or-adoption",
    "khaos-cycle:duplicate-scheduled-owner",
    "khaos-cycle:stale-snapshot-activation",
    "khaos-cycle:dual-global-writer",
    "khaos-cycle:invalid-delegated-writer",
    "khaos-cycle:stale-receipt-reuse",
    "khaos-cycle:partial-result-promotion",
    "khaos-cycle:foreground-lifecycle-replay",
    "khaos-cycle:foreground-direct-candidate-write",
    "khaos-cycle:raw-candidate-repair-omitted-from-sleep",
    "khaos-cycle:dream-opportunity-ocean-persisted",
    "khaos-cycle:local-composite-timeout-underbudgeted",
    "khaos-cycle:child-receipt-requires-outer-fields",
    "khaos-cycle:organization-backup-path-limit",
    "khaos-cycle:retired-snapshot-runtime-reader",
    "khaos-cycle:organization-status-hidden-by-local-results",
    "khaos-cycle:overlapping-organization-packets-selected",
    "khaos-cycle:organization-deletion-inventory-omitted",
)

REQUIRED_QUESTION_IDS = (
    "accepted_two_owner_flow",
    "view_does_not_count_as_use",
    "local_block_does_not_disable_organization",
    "single_global_writer_is_released",
    "known_bad_variants_rejected",
    "contracts_hold",
    "bounded_explorer_has_required_labels",
    "local_progress_loop_has_success",
    "foreground_retrieval_avoids_lifecycle_replay",
    "foreground_observation_stays_history_only",
    "raw_candidate_repair_precedes_authority_read",
    "dream_inventory_is_bounded_and_budgeted",
    "child_receipt_accepts_outer_superset",
    "organization_backup_preserves_long_paths",
    "v2_snapshot_is_replaced_by_v3_without_runtime_fallback",
    "organization_failure_stays_visible_with_local_results",
    "organization_batch_apply_is_exact_and_restore_clean",
)

CLAIM_BOUNDARY = (
    "This parent owns only the observed two-task composition, exact foreign-use "
    "boundary, foreground no-replay retrieval boundary, receipt-layering boundary, "
    "Windows-safe rollback boundary, foreground observation-only intake, explicit Sleep raw-candidate upgrade intake, bounded Dream opportunity projection, route-specific local composite timeout headroom, v2-to-v3 snapshot cutover, visible source-status "
    "envelope, non-overlapping organization packet selection, complete deletion-aware "
    "publication inventory, clean mirror restoration, and failure-domain separation. Child lifecycle, organization "
    "mutation, test, installation, Git, and release receipts remain independent."
)


def observed_child_contract() -> dict[str, object]:
    """Return the finite current child declaration consumed by the native runner."""

    return {
        "model_id": MODEL_ID,
        "child_model_id": CHILD_MODEL_ID,
        "child_model_path": CHILD_MODEL_PATH,
        "protected_failure_ids": list(PROTECTED_FAILURE_IDS),
        "required_question_ids": list(REQUIRED_QUESTION_IDS),
        "claim_boundary": CLAIM_BOUNDARY,
    }
