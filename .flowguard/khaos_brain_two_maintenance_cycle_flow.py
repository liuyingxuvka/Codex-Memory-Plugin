"""FlowGuard model for the two-owner Khaos Brain maintenance cycles.

The existing Sleep, Dream, organization-maintenance, and contribution models
remain the native owners of their internal work.  This child model owns only
the new composition boundary:

* one local owner runs Sleep and then Dream in the same task;
* one organization owner serializes snapshot, maintenance, and contribution;
* a current organization snapshot is read-only foreign input for retrieval;
* opening a foreign card records use feedback, never local adoption/model/Skill
  installation and never a task-time network fetch.

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
    dream_not_run: bool = False
    organization_not_run: bool = False
    snapshot_current: bool = False
    snapshot_manifest_valid: bool = False
    snapshot_generation: str = ""
    organization_maintenance_done: bool = False
    organization_contribution_done: bool = False
    foreign_card_used: bool = False
    foreign_use_observations: int = 0
    task_network_fetch: bool = False
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
        elif kind == "local_sleep_blocked":
            owner = "local"
            if state.local_phase == "sleep_running":
                new = replace(
                    state,
                    local_phase="sleep_blocked",
                    dream_not_run=True,
                    organization_not_run=True,
                )
                action = "sleep_progress_saved"
                reason = "A blocked or timed-out Sleep keeps Dream and the organization cycle not_run."
        elif kind == "local_dream_simulate":
            owner = "local"
            if state.local_phase == "sleep_completed":
                new = replace(
                    state,
                    local_phase="dream_completed",
                    dream_simulated=True,
                )
                action = "dream_simulated_read_only"
                reason = "Dream is the second read-only phase of the same local owner."
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
        elif kind == "organization_maintenance":
            owner = "organization"
            if state.snapshot_current and state.snapshot_manifest_valid:
                new = replace(
                    state,
                    organization_phase="maintenance_done",
                    organization_maintenance_done=True,
                )
                action = "organization_maintenance_finished"
                reason = "Existing organization maintenance remains the decision owner."
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
        elif kind == "foreign_card_use":
            owner = "retrieval"
            if state.snapshot_current and state.snapshot_manifest_valid:
                new = replace(
                    state,
                    foreign_card_used=True,
                    foreign_use_observations=state.foreign_use_observations + 1,
                )
                action = "foreign_card_used_read_only"
                reason = "Retrieval uses the current local snapshot and records organization_use feedback."
        elif kind == "task_network_fetch":
            owner = "retrieval"
            new = replace(state, task_network_fetch=True)
            action = "task_network_fetch"
            reason = "Known-bad task-time network fetch path."
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
    return InvariantResult.pass_()


def foreign_use_is_read_only(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.foreign_card_used and state.foreign_use_observations < 1:
        return InvariantResult.fail("Foreign card use did not produce organization_use feedback.")
    if state.local_adoption_or_skill_install:
        return InvariantResult.fail("Foreign card use caused local adoption or Skill installation.")
    if state.task_network_fetch:
        return InvariantResult.fail("Task-time retrieval performed a network fetch.")
    return InvariantResult.pass_()


def sole_two_owner_boundary(state: CycleState, trace: object) -> InvariantResult:
    del trace
    if state.local_owner_count > 1 or state.organization_owner_count > 1 or state.duplicate_owner_attempt:
        return InvariantResult.fail("A maintenance owner was duplicated instead of reusing the existing owner.")
    if state.dream_published_authority:
        return InvariantResult.fail("Dream mutated canonical model authority.")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant("local_cycle_order", "Sleep publishes before Dream and the local receipt closes only after both phases.", local_cycle_order),
    Invariant("organization_cycle_order", "Snapshot, maintenance, contribution, and organization closure remain serialized.", organization_cycle_order),
    Invariant("snapshot_atomicity", "Only a valid content-addressed snapshot can become current; stale input fails closed.", snapshot_atomicity),
    Invariant("foreign_use_is_read_only", "Foreign card retrieval records use feedback without adoption, Skill installation, or task-time networking.", foreign_use_is_read_only),
    Invariant("sole_two_owner_boundary", "There are exactly two scheduled owners and Dream remains read-only.", sole_two_owner_boundary),
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
    CycleInput("organization_snapshot_activate"),
    CycleInput("organization_maintenance"),
    CycleInput("organization_contribution"),
    CycleInput("organization_finish"),
)
GOOD_FOREIGN_USE = GOOD_ORGANIZATION + (CycleInput("foreign_card_use"),)
BLOCKED_LOCAL = (CycleInput("local_start"), CycleInput("local_sleep_blocked"))

KNOWN_BADS = {
    "dream_is_separate_scheduler": GOOD_LOCAL[:1] + (CycleInput("dream_is_separate_scheduler"),),
    "foreign_use_auto_adopts": GOOD_ORGANIZATION + (CycleInput("foreign_auto_adopt"),),
    "foreign_use_fetches_network": GOOD_ORGANIZATION + (CycleInput("task_network_fetch"),),
    "stale_snapshot_replaces_pointer": (CycleInput("organization_start"), CycleInput("organization_snapshot_invalid")),
    "contribution_before_maintenance": (CycleInput("organization_start"), CycleInput("organization_snapshot_activate"), CycleInput("contribution_before_maintenance")),
    "dream_writes_model": GOOD_LOCAL[:2] + (CycleInput("local_dream_publish_model"),),
    "duplicate_local_owner": (CycleInput("local_start"), CycleInput("duplicate_owner_start")),
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
            CycleInput("foreign_card_use"),
        ),
        invariants=INVARIANTS,
        max_sequence_length=3,
        required_labels=(
            "sleep_published_current_model",
            "foreign_snapshot_activated",
            "foreign_card_used_read_only",
        ),
    ).explore()
    accepted = _run(GOOD_LOCAL + GOOD_ORGANIZATION + (CycleInput("foreign_card_use"),))
    blocked = _run(BLOCKED_LOCAL)
    bad_reports = {name: _compact_report(_run(sequence)) for name, sequence in KNOWN_BADS.items()}
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
            "blocked_sleep_leaves_downstream_not_run": blocked.observed_status == "ok",
            "known_bad_variants_rejected": bad_rejected,
            "contracts_hold": contract_report["ok"],
            "bounded_explorer_has_required_labels": set(
                ("sleep_published_current_model", "foreign_snapshot_activated", "foreign_card_used_read_only")
            ).issubset(set(_compact_report(explorer)["labels_seen"])),
            "local_progress_loop_has_success": _loop_report()["ok"],
        },
        "accepted": _compact_report(accepted),
        "blocked": _compact_report(blocked),
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
