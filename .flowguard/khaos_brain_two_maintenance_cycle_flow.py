"""FlowGuard model for the two-owner Khaos Brain maintenance cycles.

The existing Sleep, Dream, organization-maintenance, and contribution models
remain the native owners of their internal work.  This child model owns only
the new composition boundary:

* one local owner runs Sleep and then Dream in the same task;
* one organization owner serializes snapshot, maintenance, and contribution;
* a current organization snapshot is read-only foreign input for retrieval;
* foreground retrieval never replays lifecycle history: local-only queries read
  no foreign calibration, while organization results consume one current compact
  calibration projection and fail closed when it is stale;
* viewing, selecting, using, and evaluating a foreign card are distinct events;
* the two tasks have independent failure domains and share only one bounded
  mutation lease;
* an immutable child receipt must remain an exact subset of the richer outer
  cycle payload; outer-only Dream, lease, and orchestration evidence is not
  required retroactively from the child;
* organization migration backup/restore uses the same rollback identity while
  addressing Windows paths beyond the legacy 260-character boundary;
* foreground feedback appends history only; it cannot create a candidate or
  mutate model, mesh, projection, or active-index authority before Sleep;
* each organization generation applies one deterministic non-overlapping packet
  set and publishes the complete pre/post materialized path inventory, including
  deletions, before restoring a clean base mirror;
* organization maintenance is not adopted until the independently installed
  remote checker proves the same schema-2 source and complete LogicGuard packet
  contract, including one UTF-8/LF-normalized text-digest policy across Windows
  and Linux checkouts, the repository keeps PR and status-check protection but
  requires zero human approvals for the automatic maintenance lane, and the
  reviewed PR reaches organization main without an administrator bypass;
* foreign use never causes local adoption/model/Skill installation or a
  task-time network fetch.

Every transition is ``Input x State -> Set(Output x State)``.  The known-bad
sequences deliberately exercise the boundaries that previously caused timeout,
duplicate scheduler, stale snapshot, and auto-adoption risks.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Iterable

from flowguard import (
    FunctionContract,
    FunctionResult,
    Invariant,
    InvariantResult,
    LoopCheckConfig,
    Workflow,
    check_loops,
    check_trace_contracts,
    run_exact_sequence,
)
from flowguard.explorer import Explorer


MODEL_ID = "khaos_brain_two_maintenance_cycle_flow"


@dataclass(frozen=True)
class CycleInput:
    kind: str


@dataclass(frozen=True)
class CycleOutput:
    action: str
    owner: str
    input_obj: CycleInput


@dataclass(frozen=True)
class CycleState:
    local_owner_count: int = 0
    organization_owner_count: int = 0
    local_phase: str = "idle"
    organization_phase: str = "idle"
    local_model_published: bool = False
    dream_simulated: bool = False
    dream_opportunity_count: int = 0
    dream_recorded_opportunity_count: int = 0
    dream_inventory_digest_bound: bool = False
    dream_unbounded_opportunity_artifact: bool = False
    local_native_timeout_seconds: int = 0
    local_owner_timeout_seconds: int = 0
    local_timeout_budget_invalid: bool = False
    dream_not_run: bool = False
    local_blocked: bool = False
    snapshot_current: bool = False
    snapshot_manifest_valid: bool = False
    snapshot_generation: str = ""
    snapshot_schema_version: int = 0
    local_results_available: bool = False
    organization_status_visible: bool = False
    retired_snapshot_reader_used: bool = False
    organization_status_hidden: bool = False
    organization_maintenance_done: bool = False
    organization_contribution_done: bool = False
    organization_packet_selection_nonoverlap: bool = False
    organization_change_inventory_complete: bool = False
    organization_mirror_restored_clean: bool = False
    organization_source_schema_version: int = 0
    organization_remote_gate_schema_version: int = 0
    organization_remote_gate_bundle_paths_current: bool = False
    organization_remote_gate_portable_text_digest: bool = False
    organization_remote_gate_automatic_review_policy: bool = False
    organization_pr_merged: bool = False
    stale_organization_remote_gate: bool = False
    organization_human_approval_required: bool = False
    organization_admin_merge_bypass: bool = False
    foreign_card_viewed: bool = False
    foreign_card_selected: bool = False
    foreign_card_used: bool = False
    foreign_use_observations: int = 0
    foreign_outcomes: int = 0
    global_writer_owner: str = ""
    delegated_writer_owner: str = ""
    view_counted_as_use: bool = False
    local_block_suppressed_organization: bool = False
    dual_writer_attempt: bool = False
    invalid_delegated_writer: bool = False
    stale_receipt_reused: bool = False
    partial_promoted_to_completed: bool = False
    child_receipt_required_outer_fields: bool = False
    organization_backup_path_truncated: bool = False
    overlapping_organization_packets_selected: bool = False
    organization_deleted_paths_omitted: bool = False
    task_network_fetch: bool = False
    foreground_lifecycle_replay: bool = False
    foreground_observation_count: int = 0
    foreground_direct_candidate_write: bool = False
    raw_candidate_upgraded_by_sleep: bool = False
    raw_candidate_repair_omitted: bool = False
    local_adoption_or_skill_install: bool = False
    dream_published_authority: bool = False
    stale_snapshot_activated: bool = False
    illegal_dream_order: bool = False
    illegal_organization_order: bool = False
    duplicate_owner_attempt: bool = False
    local_done: bool = False
    organization_done: bool = False


class TwoMaintenanceCycleBlock:
    """Input x State -> Set(Output x State) for cycle composition."""

    name = "TwoMaintenanceCycleBlock"
    reads = tuple(CycleState.__dataclass_fields__)
    writes = reads
    accepted_input_type = CycleInput
    input_description = "one local or organization cycle event"
    output_description = "one cycle action and its resulting state"
    idempotency = "A repeated terminal event is a no-op; duplicate owner start is rejected by invariants."

    def apply(self, input_obj: CycleInput, state: CycleState) -> Iterable[FunctionResult]:
        kind = input_obj.kind
        new = state
        action = "ignored"
        owner = "boundary"
        reason = "The event is outside the current cycle phase and leaves state unchanged."

        if kind == "local_start":
            owner = "local"
            if state.local_owner_count == 0:
                new = replace(
                    state,
                    local_owner_count=1,
                    local_phase="sleep_running",
                    local_done=False,
                    local_native_timeout_seconds=2400,
                    local_owner_timeout_seconds=2700,
                )
                action = "local_owner_started"
                reason = "The single local owner acquired the local maintenance lane."
            else:
                action = "local_owner_start_noop"
                reason = "A repeated owner start is idempotent and does not create a second owner."
        elif kind == "duplicate_owner_start":
            owner = "boundary"
            new = replace(state, duplicate_owner_attempt=True)
            action = "duplicate_owner_violation"
            reason = "Known-bad duplicate scheduler owner path."
        elif kind == "local_sleep_publish":
            owner = "local"
            if state.local_phase == "sleep_running":
                new = replace(
                    state,
                    local_phase="sleep_completed",
                    local_model_published=True,
                )
                action = "sleep_published_current_model"
                reason = "Sleep is the only normal-runtime canonical LogicGuard publisher."
        elif kind == "local_sleep_upgrade_raw_candidate":
            owner = "local"
            if state.local_phase == "sleep_running":
                new = replace(state, raw_candidate_upgraded_by_sleep=True)
                action = "raw_candidate_bound_to_sleep_publication"
                reason = "Sleep froze the exact residual as upgrade work before publishing current authority."
        elif kind == "local_sleep_reads_raw_candidate_before_upgrade":
            owner = "local"
            new = replace(state, raw_candidate_repair_omitted=True)
            action = "raw_candidate_repair_inventory_violation"
            reason = "Known-bad Sleep catalog read reached an unbound candidate before freezing its upgrade work."
        elif kind == "local_sleep_blocked":
            owner = "local"
            if state.local_phase == "sleep_running":
                new = replace(
                    state,
                    local_phase="sleep_blocked",
                    dream_not_run=True,
                    local_blocked=True,
                )
                action = "sleep_progress_saved"
                reason = "A blocked Sleep keeps only Dream not_run; the organization task stays independent."
        elif kind == "local_block_suppresses_organization":
            owner = "boundary"
            new = replace(state, local_block_suppressed_organization=True)
            action = "cross_task_suppression_violation"
            reason = "Known-bad local failure changing the independent organization task."
        elif kind == "local_dream_simulate":
            owner = "local"
            if state.local_phase == "sleep_completed":
                new = replace(
                    state,
                    local_phase="dream_completed",
                    dream_simulated=True,
                    dream_opportunity_count=3019,
                    dream_recorded_opportunity_count=64,
                    dream_inventory_digest_bound=True,
                )
                action = "dream_simulated_read_only"
                reason = "Dream is the second read-only phase and persists only a digest-bound bounded opportunity projection."
            else:
                new = replace(state, illegal_dream_order=True)
                action = "dream_order_violation"
                reason = "Known-bad separate Dream scheduling path."
        elif kind == "dream_is_separate_scheduler":
            owner = "local"
            new = replace(state, illegal_dream_order=True)
            action = "dream_order_violation"
            reason = "Known-bad separate Dream scheduling path."
        elif kind == "local_dream_publish_model":
            owner = "local"
            new = replace(state, dream_published_authority=True)
            action = "dream_published_authority"
            reason = "Known-bad Dream mutation path."
        elif kind == "local_dream_persist_unbounded_opportunities":
            owner = "local"
            new = replace(
                state,
                dream_unbounded_opportunity_artifact=True,
                dream_opportunity_count=3019,
                dream_recorded_opportunity_count=3019,
            )
            action = "dream_unbounded_opportunity_artifact"
            reason = "Known-bad Dream writes the complete opportunity ocean instead of a bounded projection."
        elif kind == "local_timeout_budget_below_observed_cycle":
            owner = "local"
            new = replace(
                state,
                local_timeout_budget_invalid=True,
                local_native_timeout_seconds=900,
                local_owner_timeout_seconds=1200,
            )
            action = "local_timeout_budget_invalid"
            reason = "Known-bad local owner retains the former budget that expired after a successful Sleep child but before Dream closure."
        elif kind == "local_finish":
            owner = "local"
            if state.local_phase == "dream_completed":
                new = replace(state, local_phase="done", local_done=True)
                action = "local_cycle_finished"
                reason = "Sleep and Dream completed under one owner receipt."
        elif kind == "organization_start":
            owner = "organization"
            if state.organization_owner_count == 0:
                new = replace(
                    state,
                    organization_owner_count=1,
                    organization_phase="syncing",
                    organization_done=False,
                )
                action = "organization_owner_started"
                reason = "The single organization owner acquired the organization lane."
            else:
                action = "organization_owner_start_noop"
                reason = "A repeated owner start is idempotent and does not create a second owner."
        elif kind == "organization_snapshot_activate":
            owner = "organization"
            if state.organization_phase == "syncing":
                new = replace(
                    state,
                    organization_phase="snapshot_current",
                    snapshot_current=True,
                    snapshot_manifest_valid=True,
                    snapshot_generation="generation-1",
                    snapshot_schema_version=3,
                    organization_status_visible=True,
                )
                action = "foreign_snapshot_activated"
                reason = "A complete content-addressed snapshot became current atomically."
        elif kind == "organization_snapshot_invalid":
            owner = "organization"
            new = replace(
                state,
                snapshot_current=False,
                snapshot_manifest_valid=False,
                stale_snapshot_activated=True,
            )
            action = "snapshot_activation_blocked"
            reason = "Malformed or stale snapshots fail closed and preserve the prior pointer."
        elif kind == "organization_snapshot_v2_unavailable":
            owner = "retrieval"
            new = replace(
                state,
                snapshot_current=False,
                snapshot_manifest_valid=False,
                snapshot_schema_version=2,
                local_results_available=True,
                organization_status_visible=True,
            )
            action = "retired_snapshot_rejected_visibly"
            reason = "The current runtime rejects schema v2, keeps local results, and exposes the reason."
        elif kind == "retired_snapshot_runtime_read":
            owner = "retrieval"
            new = replace(state, retired_snapshot_reader_used=True)
            action = "retired_snapshot_reader_violation"
            reason = "Known-bad normal-runtime compatibility reader accepted schema v2."
        elif kind == "local_results_hide_organization_failure":
            owner = "retrieval"
            new = replace(
                state,
                local_results_available=True,
                organization_status_visible=False,
                organization_status_hidden=True,
            )
            action = "organization_status_hidden_violation"
            reason = "Known-bad bare-list response hid organization failure behind valid local rows."
        elif kind == "organization_maintenance":
            owner = "organization"
            if state.snapshot_current and state.snapshot_manifest_valid:
                new = replace(
                    state,
                    organization_phase="maintenance_done",
                    organization_maintenance_done=True,
                    organization_packet_selection_nonoverlap=True,
                    organization_change_inventory_complete=True,
                    organization_mirror_restored_clean=True,
                    organization_source_schema_version=2,
                )
                action = "organization_maintenance_finished"
                reason = "The owner applied one non-overlapping packet set and committed the complete pre/post path inventory before restoring a clean base mirror."
        elif kind == "organization_overlapping_packets_selected":
            owner = "organization"
            new = replace(state, overlapping_organization_packets_selected=True)
            action = "organization_packet_overlap_violation"
            reason = "Known-bad batch selected individually valid packets whose materialized paths overlap."
        elif kind == "organization_deletion_inventory_omitted":
            owner = "organization"
            new = replace(state, organization_deleted_paths_omitted=True)
            action = "organization_deletion_inventory_violation"
            reason = "Known-bad publication inventory omitted paths deleted by the rebuilt source generation."
        elif kind == "organization_remote_gate_validate":
            owner = "organization-remote"
            if state.organization_maintenance_done:
                new = replace(
                    state,
                    organization_remote_gate_schema_version=2,
                    organization_remote_gate_bundle_paths_current=True,
                    organization_remote_gate_portable_text_digest=True,
                    organization_remote_gate_automatic_review_policy=True,
                )
                action = "organization_remote_gate_passed"
                reason = "The independently installed checker validated the current schema-2 catalog and complete LogicGuard packet."
        elif kind == "organization_remote_gate_schema1":
            owner = "organization-remote"
            new = replace(state, stale_organization_remote_gate=True, organization_remote_gate_schema_version=1)
            action = "organization_remote_gate_schema_violation"
            reason = "Known-bad remote checker still requires retired source schema 1."
        elif kind == "organization_remote_gate_rejects_logicguard_bundle":
            owner = "organization-remote"
            new = replace(state, stale_organization_remote_gate=True)
            action = "organization_remote_gate_path_violation"
            reason = "Known-bad remote checker rejects the bundle, catalog, and manifest paths produced by current maintenance."
        elif kind == "organization_remote_gate_platform_digest_mismatch":
            owner = "organization-remote"
            new = replace(state, stale_organization_remote_gate=True)
            action = "organization_remote_gate_digest_violation"
            reason = "Known-bad catalog hashes checkout-specific CRLF bytes, so the same projections fail after GitHub's LF checkout."
        elif kind == "organization_remote_gate_requires_human_approval":
            owner = "organization-remote"
            new = replace(state, organization_human_approval_required=True)
            action = "organization_remote_gate_human_approval_violation"
            reason = "Known-bad branch policy requires a human approval that the fully automatic maintenance owner cannot produce."
        elif kind == "organization_pr_admin_merge_bypass":
            owner = "organization-remote"
            new = replace(state, organization_admin_merge_bypass=True, organization_pr_merged=True)
            action = "organization_admin_merge_bypass_violation"
            reason = "Known-bad administrator merge bypass entered organization main without satisfying the declared automatic gate."
        elif kind == "organization_pr_merge":
            owner = "organization-remote"
            if (
                state.organization_maintenance_done
                and state.organization_remote_gate_schema_version == 2
                and state.organization_remote_gate_bundle_paths_current
                and state.organization_remote_gate_portable_text_digest
                and state.organization_remote_gate_automatic_review_policy
            ):
                new = replace(state, organization_pr_merged=True)
                action = "organization_maintenance_merged"
                reason = "A current remote gate licensed the reviewed maintenance commit to enter organization main."
        elif kind == "organization_contribution":
            owner = "organization"
            if state.organization_maintenance_done:
                new = replace(
                    state,
                    organization_phase="contribution_done",
                    organization_contribution_done=True,
                )
                action = "organization_contribution_finished"
                reason = "Contribution follows maintenance in the same serialized organization task."
            else:
                new = replace(state, illegal_organization_order=True)
                action = "organization_order_violation"
                reason = "Known-bad contribution-before-maintenance path."
        elif kind == "contribution_before_maintenance":
            owner = "organization"
            new = replace(state, illegal_organization_order=True)
            action = "organization_order_violation"
            reason = "Known-bad contribution-before-maintenance path."
        elif kind == "organization_finish":
            owner = "organization"
            if state.organization_contribution_done:
                new = replace(state, organization_phase="done", organization_done=True)
                action = "organization_cycle_finished"
                reason = "The organization cycle closed after maintenance, contribution, and snapshot."
        elif kind in {"local_writer_acquire", "organization_writer_acquire"}:
            requested = "local" if kind.startswith("local") else "organization"
            owner = requested
            if not state.global_writer_owner:
                new = replace(state, global_writer_owner=requested, delegated_writer_owner=requested)
                action = f"{requested}_writer_acquired"
                reason = "The task acquired the sole global mutation lease and a scoped child delegation."
            elif state.global_writer_owner == requested:
                action = f"{requested}_writer_reused"
                reason = "The same task idempotently reused its current mutation lease."
            else:
                action = f"{requested}_writer_waiting"
                reason = "The other task retains its independent task state while waiting for the sole writer."
        elif kind in {"local_writer_release", "organization_writer_release"}:
            requested = "local" if kind.startswith("local") else "organization"
            owner = requested
            if state.global_writer_owner == requested:
                new = replace(state, global_writer_owner="", delegated_writer_owner="")
                action = f"{requested}_writer_released"
                reason = "The phase released the bounded global mutation lease."
        elif kind == "dual_writer":
            owner = "boundary"
            new = replace(state, dual_writer_attempt=True)
            action = "dual_writer_violation"
            reason = "Known-bad simultaneous global writer path."
        elif kind == "invalid_delegated_writer":
            owner = "boundary"
            new = replace(state, invalid_delegated_writer=True)
            action = "invalid_delegation_violation"
            reason = "Known-bad child mutation without the exact delegated token."
        elif kind == "stale_receipt_reuse":
            owner = "boundary"
            new = replace(state, stale_receipt_reused=True)
            action = "stale_receipt_reuse_violation"
            reason = "Known-bad run-id-only reuse after a frozen input changed."
        elif kind == "partial_promoted":
            owner = "boundary"
            new = replace(state, partial_promoted_to_completed=True)
            action = "partial_promotion_violation"
            reason = "Known-bad progress_saved/completed_with_blocks promotion to completed."
        elif kind == "child_receipt_requires_outer_fields":
            owner = "boundary"
            new = replace(state, child_receipt_required_outer_fields=True)
            action = "receipt_layering_violation"
            reason = "Known-bad validator requires the immutable child receipt to predict outer orchestration fields."
        elif kind == "organization_backup_path_truncated":
            owner = "organization"
            new = replace(state, organization_backup_path_truncated=True)
            action = "organization_backup_path_violation"
            reason = "Known-bad Windows backup path cannot preserve the complete rollback tree."
        elif kind == "foreign_card_view":
            owner = "retrieval"
            if state.snapshot_current and state.snapshot_manifest_valid:
                new = replace(state, foreign_card_viewed=True)
                action = "foreign_card_viewed_read_only"
                reason = "Opening details records only a viewed interaction."
        elif kind == "foreign_card_select":
            owner = "retrieval"
            if state.foreign_card_viewed:
                new = replace(state, foreign_card_selected=True)
                action = "foreign_card_selected_read_only"
                reason = "Selection is explicit but is still not use."
        elif kind == "foreign_card_use":
            owner = "retrieval"
            if state.foreign_card_selected:
                new = replace(
                    state,
                    foreign_card_used=True,
                    foreign_use_observations=state.foreign_use_observations + 1,
                )
                action = "foreign_card_used_read_only"
                reason = "Actual task consumption records a source-qualified use interaction."
        elif kind == "foreign_card_outcome":
            owner = "retrieval"
            if state.foreign_card_used:
                new = replace(state, foreign_outcomes=state.foreign_outcomes + 1)
                action = "foreign_card_outcome_recorded"
                reason = "Outcome is accepted only after exact use."
        elif kind == "view_counted_as_use":
            owner = "retrieval"
            new = replace(state, foreign_card_viewed=True, foreign_card_used=True, view_counted_as_use=True)
            action = "view_counted_as_use_violation"
            reason = "Known-bad detail-open side effect masquerading as actual use."
        elif kind == "task_network_fetch":
            owner = "retrieval"
            new = replace(state, task_network_fetch=True)
            action = "task_network_fetch"
            reason = "Known-bad task-time network fetch path."
        elif kind == "foreground_lifecycle_replay":
            owner = "retrieval"
            new = replace(state, foreground_lifecycle_replay=True)
            action = "foreground_lifecycle_replay_violation"
            reason = "Known-bad foreground replay of canonical lifecycle history."
        elif kind == "foreground_observation_append":
            owner = "retrieval"
            new = replace(
                state,
                foreground_observation_count=state.foreground_observation_count + 1,
            )
            action = "foreground_observation_recorded"
            reason = "Foreground feedback appends history and defers candidate/model publication to Sleep."
        elif kind == "foreground_direct_candidate_write":
            owner = "retrieval"
            new = replace(state, foreground_direct_candidate_write=True)
            action = "foreground_direct_candidate_write_violation"
            reason = "Known-bad foreground writer places an unmodeled card directly in candidate authority."
        elif kind == "foreign_auto_adopt":
            owner = "retrieval"
            new = replace(state, local_adoption_or_skill_install=True)
            action = "foreign_auto_adopt"
            reason = "Known-bad task-time adoption or Skill installation path."

        yield FunctionResult(
            output=CycleOutput(action=action, owner=owner, input_obj=input_obj),
            new_state=new,
            label=action,
            reason=reason,
        )


WORKFLOW = Workflow((TwoMaintenanceCycleBlock(),), name=MODEL_ID)
INITIAL_STATE = CycleState()


def _trace_outputs(trace: object) -> tuple[CycleOutput, ...]:
    return tuple(
        output
        for step in getattr(trace, "steps", ())
        if isinstance((output := getattr(step, "output", None)), CycleOutput)
    )


def local_cycle_order(state: CycleState, trace: object) -> InvariantResult:
    if state.illegal_dream_order:
        return InvariantResult.fail("Dream ran before a clean Sleep publication.")
    outputs = _trace_outputs(trace)
    actions = [item.action for item in outputs]
    if "dream_simulated_read_only" in actions and "sleep_published_current_model" not in actions:
        return InvariantResult.fail("Dream ran before a clean Sleep publication.")
    if "local_cycle_finished" in actions and "dream_simulated_read_only" not in actions:
        return InvariantResult.fail("The local owner finished without its Dream second phase.")
    return InvariantResult.pass_()


def organization_cycle_order(state: CycleState, trace: object) -> InvariantResult:
    if state.illegal_organization_order:
        return InvariantResult.fail("Contribution ran before organization maintenance.")
    outputs = _trace_outputs(trace)
    actions = [item.action for item in outputs]
    if "organization_maintenance_finished" in actions and "foreign_snapshot_activated" not in actions:
        return InvariantResult.fail("Organization maintenance ran without a current complete snapshot.")
    if "organization_contribution_finished" in actions and "organization_maintenance_finished" not in actions:
        return InvariantResult.fail("Contribution ran before organization maintenance.")
    if "organization_cycle_finished" in actions and "organization_contribution_finished" not in actions:
        return InvariantResult.fail("Organization cycle finished before contribution.")
    return InvariantResult.pass_()


def snapshot_atomicity(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.snapshot_current and not state.snapshot_manifest_valid:
        return InvariantResult.fail("A snapshot pointer became current without a valid manifest.")
    if state.stale_snapshot_activated:
        return InvariantResult.fail("A stale or malformed snapshot replaced the current pointer.")
    if state.snapshot_current and state.snapshot_schema_version != 3:
        return InvariantResult.fail("Normal runtime accepted a non-current organization snapshot schema.")
    if state.retired_snapshot_reader_used:
        return InvariantResult.fail("Normal runtime used a retired organization snapshot reader.")
    return InvariantResult.pass_()


def organization_failure_is_visible(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.organization_status_hidden:
        return InvariantResult.fail("Valid local rows hid the concurrent organization failure.")
    if (
        state.local_results_available
        and not state.snapshot_current
        and not state.organization_status_visible
    ):
        return InvariantResult.fail("Local results were returned without organization source status.")
    return InvariantResult.pass_()


def organization_batch_is_exact_and_restores_cleanly(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.overlapping_organization_packets_selected:
        return InvariantResult.fail("One organization generation selected overlapping merge/split packets.")
    if state.organization_deleted_paths_omitted:
        return InvariantResult.fail("The organization publication inventory omitted deleted materialized paths.")
    if state.organization_maintenance_done and not (
        state.organization_packet_selection_nonoverlap
        and state.organization_change_inventory_complete
        and state.organization_mirror_restored_clean
    ):
        return InvariantResult.fail("Organization maintenance completed without exact packet, path-inventory, and clean-restore evidence.")
    return InvariantResult.pass_()


def organization_remote_gate_matches_current_source(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.stale_organization_remote_gate:
        return InvariantResult.fail("The remote organization checker uses a retired schema or maintenance path contract.")
    if state.organization_human_approval_required:
        return InvariantResult.fail("The automatic organization lane is blocked by a human-approval requirement.")
    if state.organization_admin_merge_bypass:
        return InvariantResult.fail("Organization main changed through an administrator merge bypass.")
    if state.organization_pr_merged and not (
        state.organization_source_schema_version == 2
        and state.organization_remote_gate_schema_version == 2
        and state.organization_remote_gate_bundle_paths_current
        and state.organization_remote_gate_portable_text_digest
        and state.organization_remote_gate_automatic_review_policy
    ):
        return InvariantResult.fail("Organization maintenance merged without current schema, bundle, portable digest, and automatic review-policy evidence.")
    return InvariantResult.pass_()


def foreign_use_is_read_only(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.foreign_card_used and state.foreign_use_observations < 1:
        return InvariantResult.fail("Foreign card use did not produce organization_use feedback.")
    if state.view_counted_as_use:
        return InvariantResult.fail("Viewing a card was counted as actual task use.")
    if state.foreign_outcomes and not state.foreign_card_used:
        return InvariantResult.fail("An outcome was accepted without exact prior use.")
    if state.local_adoption_or_skill_install:
        return InvariantResult.fail("Foreign card use caused local adoption or Skill installation.")
    if state.task_network_fetch:
        return InvariantResult.fail("Task-time retrieval performed a network fetch.")
    if state.foreground_lifecycle_replay:
        return InvariantResult.fail("Foreground retrieval replayed lifecycle history instead of using the compact current projection.")
    return InvariantResult.pass_()


def foreground_intake_is_history_only(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.foreground_direct_candidate_write:
        return InvariantResult.fail(
            "Foreground intake wrote candidate authority before Sleep created the current LogicGuard projection."
        )
    return InvariantResult.pass_()


def raw_candidate_repair_precedes_authority_read(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.raw_candidate_repair_omitted:
        return InvariantResult.fail(
            "Sleep read a residual raw candidate as current authority before freezing its direct upgrade."
        )
    return InvariantResult.pass_()


def dream_inventory_is_bounded_and_budgeted(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.dream_unbounded_opportunity_artifact:
        return InvariantResult.fail(
            "Dream persisted the full opportunity ocean instead of a bounded diagnostic projection."
        )
    if state.local_timeout_budget_invalid:
        return InvariantResult.fail(
            "The local composite timeout cannot contain the observed atomic Sleep publication plus bounded Dream."
        )
    if state.dream_simulated and not (
        state.dream_inventory_digest_bound
        and 0 <= state.dream_recorded_opportunity_count <= 64
        and state.dream_recorded_opportunity_count <= state.dream_opportunity_count
        and state.local_native_timeout_seconds >= 2400
        and state.local_native_timeout_seconds < state.local_owner_timeout_seconds
    ):
        return InvariantResult.fail(
            "Dream completed without exact full-inventory identity, the 64-row artifact cap, or ordered timeout headroom."
        )
    return InvariantResult.pass_()


def sole_two_owner_boundary(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.local_owner_count > 1 or state.organization_owner_count > 1 or state.duplicate_owner_attempt:
        return InvariantResult.fail("A maintenance owner was duplicated instead of reusing the existing owner.")
    if state.dream_published_authority:
        return InvariantResult.fail("Dream mutated canonical model authority.")
    if state.local_block_suppressed_organization:
        return InvariantResult.fail("A local failure changed the independent organization task.")
    if state.dual_writer_attempt:
        return InvariantResult.fail("More than one task held the global mutation lease.")
    if state.invalid_delegated_writer:
        return InvariantResult.fail("A child wrote without an exact delegated lease token.")
    if state.stale_receipt_reused:
        return InvariantResult.fail("A cycle receipt was reused after its frozen inputs changed.")
    if state.partial_promoted_to_completed:
        return InvariantResult.fail("A partial cycle result was promoted to completed.")
    if state.child_receipt_required_outer_fields:
        return InvariantResult.fail(
            "The immutable child receipt was required to contain outer-only orchestration evidence."
        )
    if state.organization_backup_path_truncated:
        return InvariantResult.fail(
            "The organization upgrader could not preserve a complete rollback tree at a long Windows path."
        )
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("local_cycle_order", "Sleep publishes before Dream and the local receipt closes only after both phases.", local_cycle_order),
    Invariant("organization_cycle_order", "Snapshot, maintenance, contribution, and organization closure remain serialized.", organization_cycle_order),
    Invariant("snapshot_atomicity", "Only a valid content-addressed snapshot can become current; stale input fails closed.", snapshot_atomicity),
    Invariant("organization_failure_is_visible", "Local success and organization failure share one visible canonical envelope.", organization_failure_is_visible),
    Invariant("organization_batch_is_exact_and_restores_cleanly", "One generation applies only non-overlapping packets, stages pre/post paths including deletions, and restores a clean base mirror.", organization_batch_is_exact_and_restores_cleanly),
    Invariant("organization_remote_gate_matches_current_source", "The remote merge gate shares the current schema-2 catalog, LogicGuard packet, and portable UTF-8/LF text-digest contract before organization main changes.", organization_remote_gate_matches_current_source),
    Invariant("foreign_use_is_read_only", "Foreign card retrieval records use feedback without adoption, Skill installation, or task-time networking.", foreign_use_is_read_only),
    Invariant("foreground_intake_is_history_only", "Foreground feedback appends history only; Sleep alone publishes candidates and model authority.", foreground_intake_is_history_only),
    Invariant("raw_candidate_repair_precedes_authority_read", "Sleep freezes exact raw-candidate upgrade work before catalog loading and never adds a compatibility reader.", raw_candidate_repair_precedes_authority_read),
    Invariant("dream_inventory_is_bounded_and_budgeted", "Dream keeps full scan identity but persists at most 64 opportunities under a route-specific composite timeout tree.", dream_inventory_is_bounded_and_budgeted),
    Invariant("sole_two_owner_boundary", "Two scheduled owners share one writer, retain independent failures, and require current receipts.", sole_two_owner_boundary),
)


CONTRACTS = (
    FunctionContract(
        "TwoMaintenanceCycleBlock",
        accepted_input_type=CycleInput,
        output_type=CycleOutput,
        reads=TwoMaintenanceCycleBlock.reads,
        writes=TwoMaintenanceCycleBlock.writes,
        idempotency_rule="Stable cycle run ids and terminal receipts make repeated completion no-delta.",
        traceability_rule="Every local, organization, or retrieval action names its owner and phase.",
    ),
)


GOOD_LOCAL = (
    CycleInput("local_start"),
    CycleInput("local_sleep_publish"),
    CycleInput("local_dream_simulate"),
    CycleInput("local_finish"),
)
GOOD_ORGANIZATION = (
    CycleInput("organization_start"),
    CycleInput("organization_snapshot_v2_unavailable"),
    CycleInput("organization_snapshot_activate"),
    CycleInput("organization_maintenance"),
    CycleInput("organization_remote_gate_validate"),
    CycleInput("organization_pr_merge"),
    CycleInput("organization_contribution"),
    CycleInput("organization_finish"),
)
GOOD_FOREIGN_USE = GOOD_ORGANIZATION + (
    CycleInput("foreign_card_view"),
    CycleInput("foreign_card_select"),
    CycleInput("foreign_card_use"),
    CycleInput("foreign_card_outcome"),
)
BLOCKED_LOCAL = (CycleInput("local_start"), CycleInput("local_sleep_blocked"))
BLOCKED_LOCAL_THEN_ORGANIZATION = BLOCKED_LOCAL + GOOD_ORGANIZATION
GOOD_SHARED_WRITER = (
    CycleInput("local_start"),
    CycleInput("organization_start"),
    CycleInput("local_writer_acquire"),
    CycleInput("organization_writer_acquire"),
    CycleInput("local_writer_release"),
    CycleInput("organization_writer_acquire"),
    CycleInput("organization_writer_release"),
)
GOOD_FOREGROUND_INTAKE = (CycleInput("foreground_observation_append"),)
GOOD_RAW_CANDIDATE_UPGRADE = (
    CycleInput("local_start"),
    CycleInput("local_sleep_upgrade_raw_candidate"),
    CycleInput("local_sleep_publish"),
    CycleInput("local_dream_simulate"),
    CycleInput("local_finish"),
)

KNOWN_BADS = {
    "dream_is_separate_scheduler": GOOD_LOCAL[:1] + (CycleInput("dream_is_separate_scheduler"),),
    "foreign_use_auto_adopts": GOOD_ORGANIZATION + (CycleInput("foreign_auto_adopt"),),
    "foreign_use_fetches_network": GOOD_ORGANIZATION + (CycleInput("task_network_fetch"),),
    "stale_snapshot_replaces_pointer": (CycleInput("organization_start"), CycleInput("organization_snapshot_invalid")),
    "contribution_before_maintenance": (CycleInput("organization_start"), CycleInput("organization_snapshot_activate"), CycleInput("contribution_before_maintenance")),
    "dream_writes_model": GOOD_LOCAL[:2] + (CycleInput("local_dream_publish_model"),),
    "duplicate_local_owner": (CycleInput("local_start"), CycleInput("duplicate_owner_start")),
    "view_counted_as_use": GOOD_ORGANIZATION + (CycleInput("view_counted_as_use"),),
    "local_block_suppresses_organization": BLOCKED_LOCAL + (CycleInput("local_block_suppresses_organization"),),
    "dual_global_writer": (CycleInput("local_writer_acquire"), CycleInput("dual_writer")),
    "invalid_delegated_writer": (CycleInput("invalid_delegated_writer"),),
    "stale_receipt_reuse": (CycleInput("stale_receipt_reuse"),),
    "partial_promoted": (CycleInput("partial_promoted"),),
    "child_receipt_requires_outer_fields": (
        CycleInput("child_receipt_requires_outer_fields"),
    ),
    "organization_backup_path_truncated": (
        CycleInput("organization_start"),
        CycleInput("organization_backup_path_truncated"),
    ),
    "foreground_lifecycle_replay": GOOD_ORGANIZATION + (CycleInput("foreground_lifecycle_replay"),),
    "foreground_direct_candidate_write": (
        CycleInput("foreground_direct_candidate_write"),
    ),
    "raw_candidate_repair_omitted": (
        CycleInput("local_start"),
        CycleInput("local_sleep_reads_raw_candidate_before_upgrade"),
    ),
    "dream_unbounded_opportunity_artifact": GOOD_LOCAL[:2]
    + (CycleInput("local_dream_persist_unbounded_opportunities"),),
    "local_timeout_budget_below_observed_cycle": (
        CycleInput("local_start"),
        CycleInput("local_timeout_budget_below_observed_cycle"),
    ),
    "retired_snapshot_runtime_reader": (
        CycleInput("organization_snapshot_v2_unavailable"),
        CycleInput("retired_snapshot_runtime_read"),
    ),
    "local_results_hide_organization_failure": (
        CycleInput("organization_snapshot_v2_unavailable"),
        CycleInput("local_results_hide_organization_failure"),
    ),
    "organization_overlapping_packets_selected": (
        CycleInput("organization_start"),
        CycleInput("organization_snapshot_activate"),
        CycleInput("organization_overlapping_packets_selected"),
    ),
    "organization_deletion_inventory_omitted": (
        CycleInput("organization_start"),
        CycleInput("organization_snapshot_activate"),
        CycleInput("organization_deletion_inventory_omitted"),
    ),
    "organization_remote_gate_schema1": (
        CycleInput("organization_start"),
        CycleInput("organization_snapshot_activate"),
        CycleInput("organization_maintenance"),
        CycleInput("organization_remote_gate_schema1"),
    ),
    "organization_remote_gate_rejects_logicguard_bundle": (
        CycleInput("organization_start"),
        CycleInput("organization_snapshot_activate"),
        CycleInput("organization_maintenance"),
        CycleInput("organization_remote_gate_rejects_logicguard_bundle"),
    ),
    "organization_remote_gate_platform_digest_mismatch": (
        CycleInput("organization_start"),
        CycleInput("organization_snapshot_activate"),
        CycleInput("organization_maintenance"),
        CycleInput("organization_remote_gate_platform_digest_mismatch"),
    ),
    "organization_remote_gate_requires_human_approval": (
        CycleInput("organization_start"),
        CycleInput("organization_snapshot_activate"),
        CycleInput("organization_maintenance"),
        CycleInput("organization_remote_gate_validate"),
        CycleInput("organization_remote_gate_requires_human_approval"),
    ),
    "organization_pr_admin_merge_bypass": (
        CycleInput("organization_start"),
        CycleInput("organization_snapshot_activate"),
        CycleInput("organization_maintenance"),
        CycleInput("organization_pr_admin_merge_bypass"),
    ),
}


def _compact_report(report: object) -> dict[str, object]:
    payload = report.to_dict() if hasattr(report, "to_dict") else json.loads(report.to_json_text())
    return {
        "ok": payload.get("ok", getattr(report, "observed_status", "") == "ok"),
        "observed_status": getattr(report, "observed_status", payload.get("observed_status", "")),
        "summary": payload.get("summary"),
        "violation_count": len(payload.get("violations", []) or []),
        "reachability_failure_count": len(payload.get("reachability_failures", []) or []),
        "labels_seen": sorted({label for trace in payload.get("traces", []) for label in trace.get("labels", [])}),
    }


def _run(sequence: tuple[CycleInput, ...]) -> object:
    return run_exact_sequence(WORKFLOW, INITIAL_STATE, sequence, invariants=INVARIANTS)


def _final_state(report: object) -> CycleState:
    trace = report.traces[0]
    if trace.steps:
        return trace.steps[-1].new_state
    return trace.initial_state


def _loop_report() -> dict[str, object]:
    def transition(state: CycleState) -> Iterable[tuple[str, CycleState]]:
        if state.local_phase == "idle":
            run = WORKFLOW.execute(state, CycleInput("local_start"))
        elif state.local_phase == "sleep_running":
            run = WORKFLOW.execute(state, CycleInput("local_sleep_publish"))
        elif state.local_phase == "sleep_completed":
            run = WORKFLOW.execute(state, CycleInput("local_dream_simulate"))
        elif state.local_phase == "dream_completed":
            run = WORKFLOW.execute(state, CycleInput("local_finish"))
        else:
            return
        if getattr(run, "completed_paths", None):
            yield ("progress", run.completed_paths[0].state)

    report = check_loops(
        LoopCheckConfig(
            initial_states=(INITIAL_STATE,),
            transition_fn=transition,
            is_terminal=lambda state: state.local_done,
            is_success=lambda state: state.local_done,
            required_success=True,
            max_depth=8,
            max_states=32,
        )
    )
    return _compact_report(report)


def main() -> int:
    explorer = Explorer(
        workflow=WORKFLOW,
        initial_states=(INITIAL_STATE,),
        external_inputs=(
            CycleInput("local_start"),
            CycleInput("local_sleep_publish"),
            CycleInput("organization_start"),
            CycleInput("organization_snapshot_activate"),
            CycleInput("foreign_card_view"),
            CycleInput("foreign_card_select"),
            CycleInput("foreign_card_use"),
        ),
        invariants=INVARIANTS,
        max_sequence_length=4,
        required_labels=(
            "sleep_published_current_model",
            "foreign_snapshot_activated",
            "foreign_card_viewed_read_only",
            "foreign_card_selected_read_only",
        ),
    ).explore()
    accepted = _run(GOOD_LOCAL + GOOD_FOREIGN_USE + GOOD_FOREGROUND_INTAKE + GOOD_SHARED_WRITER)
    accepted_raw_upgrade = _run(GOOD_RAW_CANDIDATE_UPGRADE)
    blocked = _run(BLOCKED_LOCAL)
    blocked_then_organization = _run(BLOCKED_LOCAL_THEN_ORGANIZATION)
    bad_reports = {name: _compact_report(_run(sequence)) for name, sequence in KNOWN_BADS.items()}
    blocked_state = _final_state(blocked)
    blocked_then_organization_state = _final_state(blocked_then_organization)
    accepted_state = _final_state(accepted)
    contract = check_trace_contracts(accepted.traces[0], CONTRACTS) if accepted.traces else None
    contract_report = {
        "ok": bool(contract and contract.ok),
        "summary": getattr(contract, "summary", "no accepted trace"),
        "violation_count": len(getattr(contract, "violations", []) or []),
    }
    bad_rejected = all(report["ok"] is False for report in bad_reports.values())
    result = {
        "model": MODEL_ID,
        "flowguard_schema_version": "1.0",
        "question_results": {
            "accepted_two_owner_flow": accepted.observed_status == "ok",
            "view_does_not_count_as_use": blocked.observed_status == "ok" and not blocked_state.foreign_card_used,
            "local_block_does_not_disable_organization": (
                blocked_then_organization.observed_status == "ok"
                and blocked_then_organization_state.organization_done
            ),
            "single_global_writer_is_released": (
                accepted.observed_status == "ok" and not accepted_state.global_writer_owner
            ),
            "known_bad_variants_rejected": bad_rejected,
            "foreground_retrieval_avoids_lifecycle_replay": (
                bad_reports["foreground_lifecycle_replay"]["ok"] is False
            ),
            "foreground_observation_stays_history_only": (
                accepted_state.foreground_observation_count == 1
                and not accepted_state.foreground_direct_candidate_write
                and bad_reports["foreground_direct_candidate_write"]["ok"] is False
            ),
            "raw_candidate_repair_precedes_authority_read": (
                accepted_raw_upgrade.observed_status == "ok"
                and _final_state(accepted_raw_upgrade).raw_candidate_upgraded_by_sleep
                and bad_reports["raw_candidate_repair_omitted"]["ok"] is False
            ),
            "dream_inventory_is_bounded_and_budgeted": (
                accepted_state.dream_inventory_digest_bound
                and accepted_state.dream_recorded_opportunity_count <= 64
                and accepted_state.local_native_timeout_seconds == 2400
                and accepted_state.local_owner_timeout_seconds == 2700
                and bad_reports["dream_unbounded_opportunity_artifact"]["ok"] is False
                and bad_reports["local_timeout_budget_below_observed_cycle"]["ok"] is False
            ),
            "child_receipt_accepts_outer_superset": (
                bad_reports["child_receipt_requires_outer_fields"]["ok"] is False
            ),
            "organization_backup_preserves_long_paths": (
                bad_reports["organization_backup_path_truncated"]["ok"] is False
            ),
            "v2_snapshot_is_replaced_by_v3_without_runtime_fallback": (
                accepted_state.snapshot_current
                and accepted_state.snapshot_schema_version == 3
                and bad_reports["retired_snapshot_runtime_reader"]["ok"] is False
            ),
            "organization_failure_stays_visible_with_local_results": (
                bad_reports["local_results_hide_organization_failure"]["ok"] is False
            ),
            "organization_batch_apply_is_exact_and_restore_clean": (
                accepted_state.organization_packet_selection_nonoverlap
                and accepted_state.organization_change_inventory_complete
                and accepted_state.organization_mirror_restored_clean
                and bad_reports["organization_overlapping_packets_selected"]["ok"] is False
                and bad_reports["organization_deletion_inventory_omitted"]["ok"] is False
            ),
            "organization_remote_gate_is_cross_platform_current": (
                accepted_state.organization_remote_gate_schema_version == 2
                and accepted_state.organization_remote_gate_bundle_paths_current
                and accepted_state.organization_remote_gate_portable_text_digest
                and accepted_state.organization_remote_gate_automatic_review_policy
                and bad_reports["organization_remote_gate_schema1"]["ok"] is False
                and bad_reports["organization_remote_gate_rejects_logicguard_bundle"]["ok"] is False
                and bad_reports["organization_remote_gate_platform_digest_mismatch"]["ok"] is False
                and bad_reports["organization_remote_gate_requires_human_approval"]["ok"] is False
                and bad_reports["organization_pr_admin_merge_bypass"]["ok"] is False
            ),
            "contracts_hold": contract_report["ok"],
            "bounded_explorer_has_required_labels": set(
                ("sleep_published_current_model", "foreign_snapshot_activated", "foreign_card_viewed_read_only", "foreign_card_selected_read_only")
            ).issubset(set(_compact_report(explorer)["labels_seen"])),
            "local_progress_loop_has_success": _loop_report()["ok"],
        },
        "accepted": _compact_report(accepted),
        "accepted_raw_candidate_upgrade": _compact_report(accepted_raw_upgrade),
        "blocked": _compact_report(blocked),
        "blocked_then_organization": _compact_report(blocked_then_organization),
        "known_bad": bad_reports,
        "contract": contract_report,
        "explorer": _compact_report(explorer),
        "loop": _loop_report(),
        "claim_boundary": "This model proves only the two-owner composition and foreign-card authority boundaries; native child lifecycle, organization, installation, and Git receipts remain separate evidence.",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(result["question_results"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
