import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kb_skill_contract_model_common import build_contract_model, run_current_model_checks

FLOWGUARD_MODEL_MARKER = "flowguard-executable-model"


def export_contract_model():
    return build_contract_model(
        "kb-organization-maintenance",
        "Upgrade and maintain current organization card bundles, publish one immutable local snapshot, and preserve each machine's direct-use weighting and executable-safety authority.",
    )


if __name__ == "__main__":
    raise SystemExit(run_current_model_checks(export_contract_model()))
