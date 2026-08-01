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
    "khaos-cycle:child-receipt-requires-outer-fields",
    "khaos-cycle:organization-backup-path-limit",
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
    "child_receipt_accepts_outer_superset",
    "organization_backup_preserves_long_paths",
)

CLAIM_BOUNDARY = (
    "This parent owns only the observed two-task composition, exact foreign-use "
    "boundary, foreground no-replay retrieval boundary, receipt-layering boundary, "
    "Windows-safe rollback boundary, and failure-domain separation. Child lifecycle, organization "
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
