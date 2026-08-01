"""FlowGuard ModelMesh for the LogicGuard-native Khaos Brain architecture."""

from __future__ import annotations

import json
from dataclasses import replace

from flowguard import (
    ChildModelEvidence,
    ChildReattachmentContract,
    HierarchyCoverageItem,
    HierarchyPartitionMap,
    MeshClosureJoin,
    MeshClosureModel,
    MeshClosureTerminal,
    MeshClosureTransition,
    ModelTargetSplitDerivation,
    review_hierarchical_mesh,
)


PARENT_ID = "khaos_brain_product_model_mesh"
LIFECYCLE = "kb_convergence_upgrade_model.LifecycleConvergenceBlock"
GOVERNANCE = "khaos_brain_governance_flow.GovernanceBlock"
AUTHORITY = "khaos_brain_logicguard_authority_cutover"
INTERFACE = "kb_canonical_interface_flow.CanonicalDataBlock"
VISUAL = "card_visual_merge_flow.ProductionVisualMergeBlock"
LOGICGUARD = "logicguard-p0-p2-runtime"
CYCLES = "khaos_brain_two_maintenance_cycle_flow.TwoMaintenanceCycleBlock"


def children() -> tuple[ChildModelEvidence, ...]:
    return (
        ChildModelEvidence(
            model_id=LIFECYCLE,
            evidence_id="focused:resumable-sleep-batch-and-pointer-publication:20260722",
            risk_boundary=(
                "bounded resumable Sleep batches, exact per-item settlement, scoped retrieval impact, "
                "prior-generation availability, remainder movement, and sole-owner pointer publication"
            ),
            inputs_accepted=(
                "observation",
                "frozen eligible item boundary",
                "immutable item result",
                "cooperative soft stop",
                "next Sleep resume",
                "exact retrieval impact",
                "Dream handoff acknowledgement",
                "exact residual raw-candidate upgrade input",
            ),
            outputs_emitted=(
                "lifecycle_delta_selected",
                "retrieval_eligibility_snapshot",
                "sleep_batch_progress_saved",
                "raw_candidate_upgrade_frozen",
                "exact_entry_deny_published",
                "exact_current_corruption_blocked",
                "sleep_watermark_committed",
                "active_index_generation_published",
            ),
            state_owned=(
                "entry_lifecycle_state",
                "retrieval_eligibility",
                "sleep_batch_plan",
                "sleep_batch_checkpoint",
                "sleep_batch_item_results",
                "sleep_raw_candidate_upgrade_inventory",
                "sleep_remainder_movement",
                "sleep_watermark",
                "active_index_pointer",
                "active_index_exact_deny_projection",
                "active_index_exact_corruption_marker",
            ),
            side_effects_owned=(
                "sleep_batch_checkpoint_commit",
                "sleep_raw_candidate_repair_receipt_commit",
                "lifecycle_event_commit",
                "exact_entry_deny_publication",
                "exact_current_corruption_marking",
                "active_index_pointer_publication",
                "retired_active_invalidated_residual_removal",
                "sleep_watermark_advance",
            ),
            functional_areas=("lifecycle_and_index",),
            contracts_in=("contract:authority.complete_generation",),
            contracts_out=("contract:lifecycle.selected_delta", "contract:lifecycle.current_index"),
            depends_on=(GOVERNANCE, AUTHORITY),
            evidence_tier="hazard_green",
            functions_owned=("LifecycleConvergenceBlock",),
            invariants_owned=(
                "eligible_status_only",
                "frozen_batch_accounting_exact",
                "raw_candidate_repair_precedes_catalog_read",
                "unfinished_batch_preserves_previous_generation",
                "watermark_after_complete_pointer_commit",
                "authorized_index_publisher",
                "global_failure_requires_exact_current_corruption",
                "retired_unscoped_invalidation_has_zero_runtime_authority",
            ),
            risk_classes=(
                "lifecycle_debt",
                "restart_entire_batch",
                "over_broad_retrieval_invalidation",
                "watermark_partial_commit",
                "native_timeout_after_partial_progress",
                "retired_global_marker_residual",
                "raw_candidate_repair_inventory_omission",
            ),
            validation_evidence=(
                "model_check:lifecycle-convergence-v3:focused",
                "model_miss:sleep-timeout-recovery:state-too-coarse-and-evidence-overclaimed",
                "known_bad:unauthorized-publisher-rejected",
            ),
        ),
        ChildModelEvidence(
            model_id=GOVERNANCE,
            evidence_id="abstract:khaos-governance:20260714-current",
            risk_boundary="Sleep/Dream decision ownership, handoff closure, and route governance",
            inputs_accepted=("lifecycle delta", "model gap summary", "Dream simulation evidence", "candidate review debt"),
            outputs_emitted=("sleep_model_change_decision", "dream_handoff_decision"),
            state_owned=("sleep_decision_state", "dream_handoff_review_state", "route_governance_state"),
            side_effects_owned=("sleep_action_selection", "dream_handoff_disposition"),
            functional_areas=("maintenance_governance",),
            contracts_in=("contract:authority.gap_summary", "contract:authority.dream_handoff"),
            contracts_out=("contract:governance.sleep_decision", "contract:governance.dream_disposition"),
            depends_on=(LIFECYCLE, AUTHORITY),
            evidence_tier="hazard_green",
            functions_owned=("GovernanceBlock",),
            invariants_owned=("dream_handoff_must_close", "candidate_backlog_must_close"),
            risk_classes=("duplicate_sleep_owner", "unreviewed_dream_handoff", "unsafe_promotion"),
            validation_evidence=("accepted:pass", "known_bad:12/12 rejected"),
        ),
        ChildModelEvidence(
            model_id=AUTHORITY,
            evidence_id="abstract:khaos-logicguard-authority-cutover:20260714-current",
            risk_boundary="exact model/mesh authority, projection binding, model-native retrieval, Dream read-only, and atomic cutover",
            inputs_accepted=("Sleep model change decision", "exact frozen raw-candidate upgrade", "versioned legacy card input", "retrieval query", "Dream experiment request"),
            outputs_emitted=(
                "model_generation_committed",
                "model_binding_validated",
                "raw_candidate_current_projection_published",
                "model_native_retrieval_result",
                "dream_simulation_handoff",
                "rollback_safe",
            ),
            state_owned=("model_revision_heads", "mesh_revision_heads", "projection_generation_stage", "raw_candidate_replacement_set", "authority_generation_pointer"),
            side_effects_owned=("model_mesh_cas_commit", "projection_staging", "migration_generation_cutover"),
            functional_areas=("logicguard_authority_cutover",),
            contracts_in=("contract:governance.sleep_decision", "contract:lifecycle.selected_delta"),
            contracts_out=(
                "contract:authority.complete_generation",
                "contract:authority.exact_binding",
                "contract:authority.model_retrieval",
                "contract:authority.dream_handoff",
            ),
            depends_on=(LOGICGUARD, LIFECYCLE, GOVERNANCE),
            evidence_tier="hazard_green",
            functions_owned=(
                "BindCardModelBlock",
                "ValidateCardBindingBlock",
                "PlanSleepModelChangeBlock",
                "FreezeRawCandidateUpgradeBlock",
                "CommitSleepModelChangeBlock",
                "ValidateDreamMeshBlock",
                "RetrieveModelNeighborhoodBlock",
                "PublishAuthorityGenerationBlock",
            ),
            invariants_owned=(
                "exact_current_authority",
                "model_first_publication",
                "raw_candidate_direct_to_current_only",
                "sole_owner_boundaries",
                "dream_exact_read_only",
                "retrieval_model_native",
                "privacy_scope_closed",
                "migration_atomic_or_blocked",
            ),
            risk_classes=("dual_authority", "partial_generation", "flat_fallback", "raw_candidate_compatibility_read", "privacy_scope_leak"),
            validation_evidence=(
                "correct:4/4 pass",
                "known_bad:14/14 rejected",
                "contracts:154 steps pass",
                "loop/progress/refinement:pass",
            ),
        ),
        ChildModelEvidence(
            model_id=INTERFACE,
            evidence_id="abstract:canonical-interface:20260714-current",
            risk_boundary="canonical machine identities and localized display projection",
            inputs_accepted=("exact model-native retrieval result", "canonical model graph payload"),
            outputs_emitted=("localized_model_projection",),
            state_owned=("canonical_display_projection_state",),
            side_effects_owned=("localized_view_model_projection",),
            functional_areas=("canonical_display_interface",),
            contracts_in=("contract:authority.model_retrieval",),
            contracts_out=("contract:interface.localized_model_view",),
            depends_on=(AUTHORITY,),
            evidence_tier="hazard_green",
            functions_owned=("CanonicalDataBlock", "MachineCliBlock", "UiDisplayBlock"),
            invariants_owned=("no_localized_route_in_canonical_state", "no_raw_unicode_at_cli_boundary"),
            risk_classes=("canonical_localization_mix",),
            validation_evidence=("accepted:pass", "known_bad:2/2 rejected"),
        ),
        ChildModelEvidence(
            model_id=VISUAL,
            evidence_id="abstract:card-visual:20260714-current",
            risk_boundary="desktop graph/detail rendering without data or route mutation",
            inputs_accepted=("localized model projection",),
            outputs_emitted=("desktop_graph_rendered",),
            state_owned=("desktop_model_view_render_state",),
            side_effects_owned=("desktop_graph_render",),
            functional_areas=("desktop_visual_projection",),
            contracts_in=("contract:interface.localized_model_view",),
            contracts_out=("contract:desktop.model_graph_visible",),
            depends_on=(INTERFACE,),
            evidence_tier="hazard_green",
            functions_owned=("ProductionVisualMergeBlock",),
            invariants_owned=("no_data_or_route_mutation", "production_entry_preserved"),
            risk_classes=("stale_or_mutating_desktop_projection",),
            validation_evidence=("explorer:pass", "known_bad:3/3 rejected", "loop/contracts:pass"),
        ),
        ChildModelEvidence(
            model_id=LOGICGUARD,
            evidence_id="logicguard:p0-p2:current-local-receipts:20260714",
            risk_boundary="immutable argument models, exact ModelMesh, structural evaluation, and sparse simulation",
            inputs_accepted=("canonical argument payload", "mesh definition", "materialization request", "simulation perturbation"),
            outputs_emitted=("exact_model_revision", "exact_mesh_revision", "structural_diagnostic", "simulation_delta"),
            state_owned=("logicguard_model_store_internal", "logicguard_mesh_store_internal", "logicguard_overlay_catalog_internal"),
            side_effects_owned=("logicguard_immutable_revision_commit", "logicguard_simulation_receipt"),
            functional_areas=("argument_model_runtime",),
            contracts_in=("contract:authority.logicguard_payload",),
            contracts_out=("contract:logicguard.exact_revision", "contract:logicguard.diagnostics", "contract:logicguard.simulation"),
            evidence_tier="conformance_green",
            functions_owned=("FileModelStore", "FileModelMeshStore", "materialize_mesh", "evaluate_materialized_mesh", "simulate_mesh"),
            invariants_owned=("immutable_revision", "revision_pinned_mesh", "typed_provenance", "sparse_simulation_no_mutation"),
            risk_classes=("argument_store_corruption", "mesh_head_drift", "ungrounded_cross_model_edge"),
            validation_evidence=("P0:177 pass", "P1:265 pass", "P2:35 pass", "scale receipt:pass"),
        ),
        ChildModelEvidence(
            model_id=CYCLES,
            evidence_id="executable:khaos-two-maintenance-cycles:current",
            risk_boundary=(
                "two independent scheduled task leases, one global mutation lease, delegated child writes, "
                "strict cycle terminal states, receipt-v3 identity, bounded Dream opportunity persistence, "
                "local timeout headroom, and viewed/selected/used/outcome separation"
            ),
            inputs_accepted=(
                "local_scheduled_trigger",
                "organization_scheduled_trigger",
                "current_organization_snapshot",
                "retired_organization_snapshot_pointer",
                "retrieval_interaction",
                "foreground_observation",
            ),
            outputs_emitted=(
                "local_cycle_receipt_v3",
                "organization_cycle_receipt_v3",
                "global_writer_serialized",
                "foreign_use_outcome_handoff",
                "canonical_search_source_status_envelope",
                "schema_v3_snapshot_activation",
                "organization_nonoverlap_packet_set",
                "organization_complete_change_inventory",
                "organization_clean_base_restore",
                "foreground_history_observation",
                "dream_bounded_opportunity_projection",
                "local_cycle_timeout_tree",
            ),
            state_owned=(
                "local_task_lease",
                "organization_task_lease",
                "global_writer_lease",
                "delegated_child_write_token",
                "cycle_receipt_identity",
                "retrieval_interaction_stage",
                "organization_snapshot_schema_state",
                "organization_source_status",
                "organization_packet_path_reservations",
                "organization_pre_post_materialized_paths",
                "organization_remote_gate_contract",
                "organization_repository_review_policy",
                "foreground_intake_mode",
                "dream_opportunity_inventory_digest",
                "dream_recorded_opportunity_count",
                "local_cycle_timeout_policy",
            ),
            side_effects_owned=(
                "global_writer_lease_delegation",
                "local_cycle_receipt_commit",
                "organization_cycle_receipt_commit",
                "retrieval_interaction_commit",
                "organization_deleted_path_commit",
                "organization_base_branch_restore",
                "organization_remote_content_check",
                "organization_gated_automatic_merge",
                "foreground_history_append",
                "dream_bounded_opportunity_artifact_commit",
            ),
            functional_areas=("maintenance_cycle_composition",),
            contracts_in=("contract:authority.model_retrieval", "contract:lifecycle.current_index"),
            contracts_out=(
                "contract:cycles.local_terminal_receipt",
                "contract:cycles.organization_terminal_receipt",
                "contract:cycles.foreign_outcome_handoff",
                "contract:cycles.foreground_observation_only",
                "contract:cycles.dream_bounded_opportunities",
                "contract:cycles.local_timeout_headroom",
                "contract:cycles.organization_remote_gate",
            ),
            depends_on=(LIFECYCLE, AUTHORITY),
            evidence_tier="hazard_green",
            functions_owned=("TwoMaintenanceCycleBlock",),
            invariants_owned=(
                "local_and_organization_failures_are_independent",
                "one_global_writer",
                "delegated_writer_required",
                "cycle_receipt_matches_frozen_inputs",
                "view_is_not_use",
                "dream_never_publishes_authority",
                "retired_snapshot_reader_is_forbidden",
                "local_results_do_not_hide_organization_failure",
                "organization_packet_set_is_nonoverlapping",
                "organization_change_inventory_includes_deletions",
                "organization_mirror_restores_cleanly",
                "organization_remote_gate_matches_current_source",
                "foreground_intake_is_history_only",
                "dream_inventory_is_bounded_and_budgeted",
            ),
            risk_classes=(
                "cross_task_cancellation",
                "dual_global_writer",
                "stale_cycle_receipt_reuse",
                "partial_result_promotion",
                "view_counted_as_use",
                "retired_snapshot_runtime_fallback",
                "hidden_organization_source_failure",
                "same_generation_packet_overlap",
                "omitted_materialized_deletion",
                "dirty_organization_base_restore",
                "stale_organization_remote_checker",
                "checkout_specific_organization_digest",
                "organization_human_approval_blocker",
                "organization_admin_merge_bypass",
                "foreground_direct_candidate_write",
                "dream_opportunity_ocean",
                "local_composite_timeout_underbudgeted",
            ),
            validation_evidence=(
                "accepted:independent-two-task-flow",
                "known_bad:cross-task-writer-receipt-and-interaction-variants-rejected",
            ),
        ),
    )


def coverage_items() -> tuple[HierarchyCoverageItem, ...]:
    values = (
        ("item:observation-candidate-lifecycle", "function", LIFECYCLE),
        ("item:retrieval-eligibility", "state", LIFECYCLE),
        ("item:frozen-resumable-sleep-batch", "state", LIFECYCLE),
        ("item:per-item-settlement-checkpoint", "state", LIFECYCLE),
        ("item:remainder-movement", "state", LIFECYCLE),
        ("item:sleep-watermark", "state", LIFECYCLE),
        ("item:active-index-pointer-publication", "side_effect", LIFECYCLE),
        ("item:exact-entry-deny", "side_effect", LIFECYCLE),
        ("item:exact-current-corruption", "side_effect", LIFECYCLE),
        ("item:retired-active-invalidated-residual", "invariant", LIFECYCLE),
        ("item:sleep-decision", "function", GOVERNANCE),
        ("item:dream-handoff-decision", "function", GOVERNANCE),
        ("item:route-governance", "state", GOVERNANCE),
        ("item:exact-model-mesh-binding", "function", AUTHORITY),
        ("item:model-first-generation", "side_effect", AUTHORITY),
        ("item:model-native-retrieval-contract", "function", AUTHORITY),
        ("item:dream-read-only-contract", "invariant", AUTHORITY),
        ("item:privacy-scope-boundary", "invariant", AUTHORITY),
        ("item:canonical-display-separation", "function", INTERFACE),
        ("item:desktop-model-graph-render", "side_effect", VISUAL),
        ("item:argument-model-semantics", "shared_kernel", LOGICGUARD),
        ("item:revision-pinned-model-mesh", "shared_kernel", LOGICGUARD),
        ("item:structural-evaluation-simulation", "shared_kernel", LOGICGUARD),
        ("item:two-independent-task-leases", "state", CYCLES),
        ("item:single-global-mutation-lease", "side_effect", CYCLES),
        ("item:delegated-child-write-token", "state", CYCLES),
        ("item:cycle-receipt-v3", "side_effect", CYCLES),
        ("item:retrieval-interaction-stages", "function", CYCLES),
        ("item:foreground-observation-only-intake", "function", CYCLES),
        ("item:dream-bounded-opportunity-projection", "state", CYCLES),
        ("item:local-cycle-timeout-headroom", "invariant", CYCLES),
        ("item:organization-remote-content-and-review-gate", "invariant", CYCLES),
    )
    return tuple(
        HierarchyCoverageItem(
            item_id,
            item_type=item_type,
            owner_model_id=owner,
            ownership="child",
            description="Single child owner in the LogicGuard-native Khaos Brain parent boundary.",
        )
        for item_id, item_type, owner in values
    )


def reattachments(models: tuple[ChildModelEvidence, ...]) -> tuple[ChildReattachmentContract, ...]:
    return tuple(
        ChildReattachmentContract(
            child_model_id=child.model_id,
            consumed_evidence_id=child.evidence_id,
            expected_inputs=child.inputs_accepted,
            expected_outputs=child.outputs_emitted,
            expected_state_owned=child.state_owned,
            expected_side_effects_owned=child.side_effects_owned,
            expected_contracts_out=child.contracts_out,
            rationale="The parent consumes this exact current child boundary without expanding its internal state graph.",
        )
        for child in models
    )


def closure_model(models: tuple[ChildModelEvidence, ...]) -> MeshClosureModel:
    all_outputs = tuple(output for child in models for output in child.outputs_emitted)
    return MeshClosureModel(
        parent_model_id=PARENT_ID,
        root_entries=(
            "observation_or_versioned_legacy_input",
            "local_scheduled_trigger",
            "organization_scheduled_trigger",
            "current_organization_snapshot",
            "retired_organization_snapshot_pointer",
            "retrieval_interaction",
            "foreground_observation",
            "residual_raw_candidate_upgrade_input",
        ),
        transitions=(
            MeshClosureTransition(
                "cycles_record_foreground_observation_only",
                consumes=("foreground_observation",),
                emits=("foreground_history_observation", "observation_or_versioned_legacy_input"),
                consumer_model_id=CYCLES,
                code_contract_id="contract:cycles.foreground_observation_only",
                rationale=(
                    "Foreground feedback appends one history observation and cannot create a candidate or "
                    "change model, mesh, projection, or index authority before the next Sleep."
                ),
            ),
            MeshClosureTransition(
                "cycles_upgrade_retired_snapshot_to_current_schema",
                consumes=(
                    "organization_scheduled_trigger",
                    "retired_organization_snapshot_pointer",
                ),
                emits=("schema_v3_snapshot_activation",),
                consumer_model_id=CYCLES,
                code_contract_id="contract:cycles.organization_terminal_receipt",
                rationale=(
                    "The organization maintenance owner directly replaces a retired v2 pointer with one "
                    "validated schema-v3 snapshot; normal retrieval never opens the retired schema."
                ),
            ),
            MeshClosureTransition(
                "cycles_render_visible_default_source_status",
                consumes=(
                    "retrieval_interaction",
                    "schema_v3_snapshot_activation",
                ),
                emits=("canonical_search_source_status_envelope",),
                consumer_model_id=CYCLES,
                code_contract_id="contract:cycles.foreign_outcome_handoff",
                rationale=(
                    "Default retrieval returns local results together with the explicit organization "
                    "source status, so one successful source cannot hide another source failure."
                ),
            ),
            MeshClosureTransition(
                "cycles_apply_exact_organization_maintenance_batch",
                consumes=(
                    "organization_scheduled_trigger",
                    "current_organization_snapshot",
                ),
                emits=(
                    "organization_nonoverlap_packet_set",
                    "organization_complete_change_inventory",
                    "organization_clean_base_restore",
                ),
                consumer_model_id=CYCLES,
                code_contract_id="contract:cycles.organization_terminal_receipt",
                rationale=(
                    "The maintenance owner selects only non-overlapping packets, stages the union of pre/post "
                    "materialized paths including deletions, and restores a clean base mirror before terminal success."
                ),
            ),
            MeshClosureTransition(
                "cycles_serialize_writes_and_commit_terminal_receipts",
                consumes=(
                    "local_scheduled_trigger",
                    "organization_scheduled_trigger",
                    "current_organization_snapshot",
                    "retrieval_interaction",
                ),
                emits=(
                    "local_cycle_receipt_v3",
                    "organization_cycle_receipt_v3",
                    "global_writer_serialized",
                    "foreign_use_outcome_handoff",
                    "dream_bounded_opportunity_projection",
                    "local_cycle_timeout_tree",
                ),
                consumer_model_id=CYCLES,
                code_contract_id="contract:cycles.foreign_outcome_handoff",
                rationale=(
                    "Independent scheduled roots may overlap read-only work, while a single delegated writer "
                    "serializes mutations, Dream persists only a digest-bound bounded opportunity projection, "
                    "the local route retains ordered timeout headroom, and each root commits its own exact terminal receipt."
                ),
            ),
            MeshClosureTransition(
                "lifecycle_selects_delta",
                consumes=(
                    "observation_or_versioned_legacy_input",
                    "foreign_use_outcome_handoff",
                    "residual_raw_candidate_upgrade_input",
                ),
                emits=(
                    "lifecycle_delta_selected",
                    "retrieval_eligibility_snapshot",
                    "sleep_batch_progress_saved",
                    "raw_candidate_upgrade_frozen",
                    "exact_entry_deny_published",
                    "exact_current_corruption_blocked",
                ),
                consumer_model_id=LIFECYCLE,
                code_contract_id="contract:lifecycle.selected_delta",
                rationale=(
                    "The unique lifecycle owner freezes/resumes a bounded batch, binds each schema-less unbound "
                    "candidate as exact upgrade work before catalog loading, checkpoints exact item results, and "
                    "projects only impact-scoped retrieval safety while the prior generation remains current."
                ),
            ),
            MeshClosureTransition(
                "governance_selects_sleep_action",
                consumes=("lifecycle_delta_selected",),
                emits=("sleep_model_change_decision",),
                consumer_model_id=GOVERNANCE,
                code_contract_id="contract:governance.sleep_decision",
                rationale="The existing governance model remains the Sleep decision owner.",
            ),
            MeshClosureTransition(
                "logicguard_builds_exact_revisions",
                consumes=("sleep_model_change_decision",),
                emits=("exact_model_revision", "exact_mesh_revision", "structural_diagnostic"),
                consumer_model_id=LOGICGUARD,
                code_contract_id="contract:logicguard.exact_revision",
                rationale="LogicGuard supplies exact canonical semantics and diagnostics.",
            ),
            MeshClosureTransition(
                "authority_commits_complete_generation",
                consumes=("exact_model_revision", "exact_mesh_revision", "structural_diagnostic", "retrieval_eligibility_snapshot", "raw_candidate_upgrade_frozen"),
                emits=("model_generation_committed", "model_binding_validated", "raw_candidate_current_projection_published", "rollback_safe"),
                consumer_model_id=AUTHORITY,
                code_contract_id="contract:authority.complete_generation",
                rationale="The child authority model validates and stages one complete generation or safe rollback.",
            ),
            MeshClosureTransition(
                "lifecycle_publishes_index_and_watermark",
                consumes=(
                    "model_generation_committed",
                    "model_binding_validated",
                    "sleep_batch_progress_saved",
                    "exact_entry_deny_published",
                    "exact_current_corruption_blocked",
                ),
                emits=("active_index_generation_published", "sleep_watermark_committed"),
                consumer_model_id=LIFECYCLE,
                code_contract_id="contract:lifecycle.current_index",
                rationale=(
                    "The existing lifecycle owner alone publishes the immutable active-index pointer last, clears "
                    "generation-bound safety projections, removes retired unscoped marker residuals, and then advances Sleep watermark."
                ),
            ),
            MeshClosureTransition(
                "authority_returns_model_native_retrieval",
                consumes=("active_index_generation_published", "model_binding_validated"),
                emits=("model_native_retrieval_result",),
                consumer_model_id=AUTHORITY,
                code_contract_id="contract:authority.model_retrieval",
                rationale="The existing search facade consumes exact authority through the child contract.",
            ),
            MeshClosureTransition(
                "interface_localizes_model_view",
                consumes=("model_native_retrieval_result",),
                emits=("localized_model_projection",),
                consumer_model_id=INTERFACE,
                code_contract_id="contract:interface.localized_model_view",
                rationale="Localization projects display labels without mutating canonical identities.",
            ),
            MeshClosureTransition(
                "desktop_renders_model_graph",
                consumes=("localized_model_projection",),
                emits=("desktop_graph_rendered",),
                consumer_model_id=VISUAL,
                code_contract_id="contract:desktop.model_graph_visible",
                rationale="The desktop owner renders the single recommended graph.",
            ),
            MeshClosureTransition(
                "logicguard_simulates_exact_mesh",
                consumes=("exact_mesh_revision",),
                emits=("simulation_delta",),
                consumer_model_id=LOGICGUARD,
                code_contract_id="contract:logicguard.simulation",
                rationale="Dream simulation is sparse and does not mutate canonical revisions.",
            ),
            MeshClosureTransition(
                "authority_packages_dream_handoff",
                consumes=("simulation_delta",),
                emits=("dream_simulation_handoff",),
                consumer_model_id=AUTHORITY,
                code_contract_id="contract:authority.dream_handoff",
                rationale="The child packages immutable experiment evidence only.",
            ),
            MeshClosureTransition(
                "governance_disposes_dream_handoff",
                consumes=("dream_simulation_handoff",),
                emits=("dream_handoff_decision",),
                consumer_model_id=GOVERNANCE,
                code_contract_id="contract:governance.dream_disposition",
                rationale="The existing governance/Sleep owner reviews, watches, or rejects the handoff.",
            ),
        ),
        joins=(
            MeshClosureJoin(
                "join:logicguard-native-khaos-whole-flow",
                required_inputs=all_outputs,
                emits=("logicguard_native_khaos_closed",),
                rationale="Every child output is reachable and consumed before the parent can claim whole-flow closure.",
            ),
        ),
        terminals=(
            MeshClosureTerminal(
                "terminal:normal-current-generation",
                consumes=("logicguard_native_khaos_closed",),
                terminal_kind="normal_exit",
                rationale="A complete model-native generation, retrieval/UI route, Dream handoff route, and rollback capability are closed.",
            ),
        ),
        required_outputs=all_outputs,
        require_normal_exit=True,
        rationale="Model-of-models closure; child state graphs remain separate.",
    )


def build_partition() -> HierarchyPartitionMap:
    models = children()
    items = coverage_items()
    return HierarchyPartitionMap(
        parent_model_id=PARENT_ID,
        coverage_items=items,
        child_models=models,
        target_split_derivation=ModelTargetSplitDerivation(
            source_model_id=PARENT_ID,
            source_model_path=".flowguard/khaos_brain_logicguard_model_mesh.py",
            target_child_model_ids=tuple(child.model_id for child in models),
            covered_partition_item_ids=tuple(item.item_id for item in items),
            state_owner_fields=tuple(field for child in models for field in child.state_owned),
            side_effect_owner_fields=tuple(effect for child in models for effect in child.side_effects_owned),
            rationale=(
                "Lifecycle/index, maintenance governance, LogicGuard authority cutover, canonical/display, "
                "desktop rendering, and argument runtime are distinct cohesive ownership regions."
            ),
            derived_from_flowguard_model=True,
        ),
        reattachment_contracts=reattachments(models),
        required_evidence_tier="abstract_green",
        allowed_shared_areas=(),
        closure_model=closure_model(models),
    )


def broken_partition() -> HierarchyPartitionMap:
    current = build_partition()
    models = list(current.child_models)
    governance = next(child for child in models if child.model_id == GOVERNANCE)
    models[models.index(governance)] = replace(
        governance,
        state_owned=(*governance.state_owned, "model_revision_heads"),
        evidence_current=False,
    )
    return replace(current, child_models=tuple(models))


def main() -> int:
    expected_count = len(build_partition().child_models)
    current = review_hierarchical_mesh(build_partition(), model_count=expected_count)
    broken = review_hierarchical_mesh(broken_partition(), model_count=expected_count)
    payload = {
        "artifact_type": "khaos_brain_logicguard_native_flowguard_model_mesh",
        "current": current.to_dict(),
        "known_bad": broken.to_dict(),
        "child_count": len(build_partition().child_models),
        "partition_item_count": len(build_partition().coverage_items),
        "ok": current.ok and not broken.ok,
        "claim_boundary": (
            "This mesh proves current abstract parent/child ownership, exact evidence-id reattachment, "
            "partition coverage, no duplicate state/side-effect ownership, and token-level whole-flow "
            "closure. It does not prove production code, runtime conformance, tests, UI observation, "
            "migration, SkillGuard, or release readiness."
        ),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
