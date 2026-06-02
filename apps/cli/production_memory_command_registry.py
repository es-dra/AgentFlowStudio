from __future__ import annotations

import typer

from apps.cli.production_memory_acceptance_feedback_candidate_command import (
    production_memory_loop_draft_acceptance_feedback_candidate_command,
)
from apps.cli.production_memory_acceptance_feedback_candidate_overlay_command import (
    production_memory_loop_run_acceptance_feedback_candidate_reviewed_no_provider_command,
)
from apps.cli.production_memory_acceptance_feedback_candidate_promotion_command import (
    production_memory_loop_review_acceptance_feedback_candidate_command,
)
from apps.cli.production_memory_acceptance_feedback_command import (
    production_memory_loop_record_acceptance_feedback_command,
)
from apps.cli.production_memory_action_result_acceptance_feedback_command import (
    production_memory_loop_record_action_result_acceptance_feedback_command,
)
from apps.cli.production_memory_asset_consistency_review_command import (
    asset_consistency_review_command,
    production_memory_loop_review_asset_consistency_command,
)
from apps.cli.production_memory_asset_feedback_command import (
    production_memory_loop_record_asset_feedback_command,
)
from apps.cli.production_memory_asset_profile_command import (
    production_memory_loop_asset_profile_readiness_command,
    production_memory_loop_run_asset_test_package_command,
)
from apps.cli.production_memory_asset_profile_context_projection_command import (
    production_memory_loop_asset_profile_context_projection_command,
)
from apps.cli.production_memory_asset_profile_promotion_command import (
    asset_profile_update_review_command,
    production_memory_loop_review_asset_profile_update_candidate_command,
)
from apps.cli.production_memory_asset_profile_update_candidate_command import (
    production_memory_loop_draft_asset_profile_update_candidate_command,
)
from apps.cli.production_memory_loop_command import (
    production_memory_loop_draft_feedback_command,
    production_memory_loop_review_promotion_command,
    production_memory_loop_run_no_provider_command,
    production_memory_loop_run_reviewed_feedback_no_provider_command,
    production_memory_loop_validate_command,
)
from apps.cli.production_memory_next_context_command import production_memory_loop_next_context_handoff_command
from apps.cli.production_memory_next_operator_action_result_command import (
    production_memory_loop_record_next_operator_action_result_command,
)
from apps.cli.production_memory_next_operator_start_command import (
    production_memory_loop_next_operator_start_packet_command,
)
from apps.cli.production_memory_next_operator_start_event_command import (
    production_memory_loop_record_next_operator_start_command,
)
from apps.cli.production_memory_next_pass_promotion_command import (
    production_memory_loop_review_next_pass_promotion_command,
    production_memory_loop_run_next_pass_reviewed_feedback_no_provider_command,
)
from apps.cli.production_memory_next_pass_result_command import (
    production_memory_loop_draft_next_pass_result_no_provider_command,
)
from apps.cli.production_memory_next_pass_review_command import production_memory_loop_review_next_pass_command
from apps.cli.production_memory_next_task_command import production_memory_loop_next_task_packet_command
from apps.cli.production_memory_operator_command import production_memory_loop_run_operator_no_provider_command
from apps.cli.production_memory_operator_feedback_candidate_command import (
    production_memory_loop_draft_operator_feedback_candidate_command,
)
from apps.cli.production_memory_operator_feedback_candidate_overlay_command import (
    production_memory_loop_run_operator_feedback_candidate_reviewed_no_provider_command,
)
from apps.cli.production_memory_operator_feedback_candidate_promotion_command import (
    production_memory_loop_review_operator_feedback_candidate_command,
)
from apps.cli.production_memory_operator_feedback_command import (
    production_memory_loop_capture_operator_feedback_command,
)
from apps.cli.production_memory_operator_handoff_command import (
    production_memory_loop_operator_handoff_packet_command,
)
from apps.cli.production_memory_operator_manifest_check_command import (
    production_memory_loop_check_operator_manifest_command,
)
from apps.cli.production_memory_operator_run_package_check_command import (
    production_memory_loop_check_operator_run_package_command,
)
from apps.cli.production_memory_session_command import (
    production_memory_loop_company_kb_candidates_command,
    production_memory_loop_session_report_command,
)


def register_production_memory_commands(app: typer.Typer) -> None:
    """Register Production Memory CLI commands with a thin default help surface."""
    _visible(app, "memory-loop-validate", production_memory_loop_validate_command)
    _visible(app, "memory-loop-run-no-provider", production_memory_loop_run_no_provider_command)
    _visible(
        app,
        "asset-profile-readiness",
        production_memory_loop_asset_profile_readiness_command,
    )
    _visible(
        app,
        "asset-test-package-run",
        production_memory_loop_run_asset_test_package_command,
    )
    _visible(app, "asset-feedback-record", production_memory_loop_record_asset_feedback_command)
    _visible(
        app,
        "asset-profile-update-draft",
        production_memory_loop_draft_asset_profile_update_candidate_command,
    )
    _visible(
        app,
        "asset-profile-update-review",
        asset_profile_update_review_command,
    )
    _visible(
        app,
        "asset-context-project",
        production_memory_loop_asset_profile_context_projection_command,
    )
    _visible(
        app,
        "asset-consistency-review",
        asset_consistency_review_command,
    )

    _hidden(app, "production-memory-loop-validate", production_memory_loop_validate_command)
    _hidden(app, "production-memory-loop-run-no-provider", production_memory_loop_run_no_provider_command)
    _hidden(app, "production-memory-loop-run-operator-no-provider", production_memory_loop_run_operator_no_provider_command)
    _hidden(
        app,
        "production-memory-loop-asset-profile-readiness",
        production_memory_loop_asset_profile_readiness_command,
    )
    _hidden(
        app,
        "production-memory-loop-run-asset-test-package",
        production_memory_loop_run_asset_test_package_command,
    )
    _hidden(app, "production-memory-loop-record-asset-feedback", production_memory_loop_record_asset_feedback_command)
    _hidden(
        app,
        "production-memory-loop-draft-asset-profile-update-candidate",
        production_memory_loop_draft_asset_profile_update_candidate_command,
    )
    _hidden(
        app,
        "production-memory-loop-review-asset-profile-update-candidate",
        production_memory_loop_review_asset_profile_update_candidate_command,
    )
    _hidden(
        app,
        "production-memory-loop-asset-profile-context-projection",
        production_memory_loop_asset_profile_context_projection_command,
    )
    _hidden(
        app,
        "production-memory-loop-review-asset-consistency",
        production_memory_loop_review_asset_consistency_command,
    )
    _hidden(app, "production-memory-loop-draft-feedback", production_memory_loop_draft_feedback_command)
    _hidden(app, "production-memory-loop-review-promotion", production_memory_loop_review_promotion_command)
    _hidden(
        app,
        "production-memory-loop-run-reviewed-feedback-no-provider",
        production_memory_loop_run_reviewed_feedback_no_provider_command,
    )
    _hidden(
        app,
        "production-memory-loop-check-operator-manifest",
        production_memory_loop_check_operator_manifest_command,
    )
    _hidden(
        app,
        "production-memory-loop-check-operator-run-package",
        production_memory_loop_check_operator_run_package_command,
    )
    _hidden(app, "production-memory-loop-operator-handoff-packet", production_memory_loop_operator_handoff_packet_command)
    _hidden(app, "production-memory-loop-capture-operator-feedback", production_memory_loop_capture_operator_feedback_command)
    _hidden(
        app,
        "production-memory-loop-record-acceptance-feedback",
        production_memory_loop_record_acceptance_feedback_command,
    )
    _hidden(
        app,
        "production-memory-loop-record-action-result-acceptance-feedback",
        production_memory_loop_record_action_result_acceptance_feedback_command,
    )
    _hidden(
        app,
        "production-memory-loop-draft-acceptance-feedback-candidate",
        production_memory_loop_draft_acceptance_feedback_candidate_command,
    )
    _hidden(
        app,
        "production-memory-loop-review-acceptance-feedback-candidate",
        production_memory_loop_review_acceptance_feedback_candidate_command,
    )
    _hidden(
        app,
        "production-memory-loop-run-acceptance-feedback-candidate-reviewed-no-provider",
        production_memory_loop_run_acceptance_feedback_candidate_reviewed_no_provider_command,
    )
    _hidden(
        app,
        "production-memory-loop-draft-operator-feedback-candidate",
        production_memory_loop_draft_operator_feedback_candidate_command,
    )
    _hidden(
        app,
        "production-memory-loop-review-operator-feedback-candidate",
        production_memory_loop_review_operator_feedback_candidate_command,
    )
    _hidden(
        app,
        "production-memory-loop-run-operator-feedback-candidate-reviewed-no-provider",
        production_memory_loop_run_operator_feedback_candidate_reviewed_no_provider_command,
    )
    _hidden(app, "production-memory-loop-next-context-handoff", production_memory_loop_next_context_handoff_command)
    _hidden(app, "production-memory-loop-next-task-packet", production_memory_loop_next_task_packet_command)
    _hidden(
        app,
        "production-memory-loop-draft-next-pass-result-no-provider",
        production_memory_loop_draft_next_pass_result_no_provider_command,
    )
    _hidden(app, "production-memory-loop-review-next-pass", production_memory_loop_review_next_pass_command)
    _hidden(
        app,
        "production-memory-loop-review-next-pass-promotion",
        production_memory_loop_review_next_pass_promotion_command,
    )
    _hidden(
        app,
        "production-memory-loop-run-next-pass-reviewed-feedback-no-provider",
        production_memory_loop_run_next_pass_reviewed_feedback_no_provider_command,
    )
    _hidden(app, "production-memory-loop-session-report", production_memory_loop_session_report_command)
    _hidden(app, "production-memory-loop-company-kb-candidates", production_memory_loop_company_kb_candidates_command)
    _hidden(
        app,
        "production-memory-loop-next-operator-start-packet",
        production_memory_loop_next_operator_start_packet_command,
    )
    _hidden(
        app,
        "production-memory-loop-record-next-operator-start",
        production_memory_loop_record_next_operator_start_command,
    )
    _hidden(
        app,
        "production-memory-loop-record-next-operator-action-result",
        production_memory_loop_record_next_operator_action_result_command,
    )


def _visible(app: typer.Typer, name: str, command: object) -> None:
    app.command(name=name)(command)


def _hidden(app: typer.Typer, name: str, command: object) -> None:
    app.command(name=name, hidden=True)(command)
