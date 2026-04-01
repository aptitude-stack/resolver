from __future__ import annotations

import asyncio
import time
from pathlib import Path

from textual.widgets import Input, Static

from aptitude.application.dto import (
    DiscoveryCandidateDto,
    ExecutionPlanDto,
    ExecutionStepDto,
    InstalledSkillDto,
    InstallResultDto,
    LockRootDto,
    LockfileDto,
    LockedSkillDto,
    PolicyEvaluationDto,
    ResolvedGraphDto,
    ResolvedSkillNodeDto,
    ResolveCoordinateDto,
    ResolveQueryResultDto,
    ResolveSkillSummaryDto,
    TraceEntryDto,
)
from aptitude.domain.errors import InvalidResolverConfigurationError
from aptitude.interfaces.tui.app import AptitudeInstallerApp


class FakeWorkflowService:
    def __init__(
        self,
        *,
        resolve_responses: list[ResolveQueryResultDto] | None = None,
        install_responses: list[InstallResultDto] | None = None,
        resolve_error: Exception | None = None,
        install_error: Exception | None = None,
    ) -> None:
        self.resolve_responses = list(resolve_responses or [])
        self.install_responses = list(install_responses or [])
        self.resolve_error = resolve_error
        self.install_error = install_error
        self.resolve_calls: list[dict[str, object]] = []
        self.install_calls: list[dict[str, object]] = []

    def resolve_query(self, **kwargs: object) -> ResolveQueryResultDto:
        self.resolve_calls.append(kwargs)
        if self.resolve_error is not None:
            raise self.resolve_error
        assert self.resolve_responses
        return self.resolve_responses.pop(0)

    def install_query(self, **kwargs: object) -> InstallResultDto:
        self.install_calls.append(kwargs)
        if self.install_error is not None:
            raise self.install_error
        assert self.install_responses
        return self.install_responses.pop(0)


def _resolved_result(
    *,
    slug: str = "python.lint",
    version: str = "1.2.3",
    selection_mode: str = "single_candidate",
) -> ResolveQueryResultDto:
    return ResolveQueryResultDto(
        requested_query="python lint",
        status="resolved",
        selection_mode=selection_mode,
        selected_coordinate=ResolveCoordinateDto(slug=slug, version=version),
        selected_skill=ResolveSkillSummaryDto(
            name="Python Lint" if slug == "python.lint" else "JavaScript Lint",
            description="Linting skill",
            tags=["lint"],
            runtime="python" if slug == "python.lint" else "javascript",
            rendered_summary="Lint files consistently.",
            lifecycle_status="published",
            trust_tier="internal",
        ),
        graph=ResolvedGraphDto(
            root=ResolveCoordinateDto(slug=slug, version=version),
            nodes=[
                ResolvedSkillNodeDto(
                    slug=slug,
                    version=version,
                    name="Python Lint" if slug == "python.lint" else "JavaScript Lint",
                    description="Linting skill",
                    tags=["lint"],
                    runtime="python" if slug == "python.lint" else "javascript",
                    rendered_summary="Lint files consistently.",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                )
            ],
            edges=[],
            install_order=[ResolveCoordinateDto(slug=slug, version=version)],
            conflicts=[],
        ),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="python lint",
                requested_version=None,
                selected_node_id=f"{slug}@{version}",
                selection_mode=selection_mode,
            ),
            nodes=[
                LockedSkillDto(
                    node_id=f"{slug}@{version}",
                    slug=slug,
                    version=version,
                    artifact_ref=f"/skills/{slug}/{version}/content",
                    name="Python Lint" if slug == "python.lint" else "JavaScript Lint",
                    description="Linting skill",
                    tags=["lint"],
                    headers={
                        "runtime": "python" if slug == "python.lint" else "javascript"
                    },
                    rendered_summary="Lint files consistently.",
                    lifecycle_status="published",
                    trust_tier="internal",
                    published_at="2026-03-18T00:00:00Z",
                    content_checksum={
                        "algorithm": "sha256",
                        "digest": f"digest-{slug}-{version}",
                        "size_bytes": 256,
                    },
                )
            ],
            edges=[],
            install_order=[f"{slug}@{version}"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id=f"{slug}@{version}",
                    skill=slug,
                    version=version,
                    artifact_ref=f"/skills/{slug}/{version}/content",
                    action="materialize_local_skill",
                )
            ]
        ),
        trace=[
            TraceEntryDto(
                stage="selection",
                action="finalize_selection",
                message="Selected a skill.",
                data={"selection_mode": selection_mode},
            )
        ],
        policy_evaluations=[
            PolicyEvaluationDto(
                rule="allowed_lifecycle_status",
                passed=True,
                message="Lifecycle is allowed.",
                coordinate=ResolveCoordinateDto(slug=slug, version=version),
            )
        ],
    )


def _selection_required_result() -> ResolveQueryResultDto:
    return ResolveQueryResultDto(
        requested_query="lint",
        status="selection_required",
        candidates=[
            DiscoveryCandidateDto(
                slug="python.lint",
                version="1.2.3",
                name="Python Lint",
                description="Lint Python files",
                tags=["python", "lint"],
                labels=["python", "lint"],
                matched_labels=["python", "lint"],
                match_reasons=["exact_name_match"],
                runtime="python",
                lifecycle_status="published",
                trust_tier="internal",
                token_estimate=120,
                content_size_bytes=256,
                published_at="2026-03-18T00:00:00Z",
                ranking_position=1,
                selection_details=[
                    "tokens=120",
                    "size=256B",
                    "published=2026-03-18T00:00:00Z",
                ],
                selection_reason="ranked above js.lint@2.1.0: closer exact name match",
            ),
            DiscoveryCandidateDto(
                slug="js.lint",
                version="2.1.0",
                name="JavaScript Lint",
                description="Lint JavaScript files",
                tags=["javascript", "lint"],
                labels=["javascript", "lint"],
                matched_labels=["lint"],
                match_reasons=["label_overlap"],
                runtime="javascript",
                lifecycle_status="published",
                trust_tier="internal",
                token_estimate=250,
                content_size_bytes=320,
                published_at="2026-03-17T00:00:00Z",
                ranking_position=2,
                selection_details=[
                    "tokens=250",
                    "size=320B",
                    "published=2026-03-17T00:00:00Z",
                ],
            ),
        ],
        trace=[
            TraceEntryDto(
                stage="selection",
                action="await_user_choice",
                message="Multiple candidates remain.",
                data={},
            )
        ],
    )


def _installed_result(
    materialized_root: str = str(Path("skill_demo")),
) -> InstallResultDto:
    return InstallResultDto(
        requested_query="python lint",
        status="installed",
        selection_mode="single_candidate",
        selected_coordinate=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
        graph=ResolvedGraphDto(
            root=ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            nodes=[],
            edges=[],
            install_order=[
                ResolveCoordinateDto(slug="dep.core", version="0.9.0"),
                ResolveCoordinateDto(slug="python.lint", version="1.2.3"),
            ],
            conflicts=[],
        ),
        lockfile=LockfileDto(
            version=1,
            generated_at="2026-03-18T00:00:00Z",
            root=LockRootDto(
                request="python lint",
                requested_version=None,
                selected_node_id="python.lint@1.2.3",
                selection_mode="single_candidate",
            ),
            nodes=[],
            edges=[],
            install_order=["dep.core@0.9.0", "python.lint@1.2.3"],
            governance=[],
        ),
        execution_plan=ExecutionPlanDto(
            steps=[
                ExecutionStepDto(
                    node_id="dep.core@0.9.0",
                    skill="dep.core",
                    version="0.9.0",
                    artifact_ref="/skills/dep.core/0.9.0/content",
                    action="materialize_local_skill",
                ),
                ExecutionStepDto(
                    node_id="python.lint@1.2.3",
                    skill="python.lint",
                    version="1.2.3",
                    artifact_ref="/skills/python.lint/1.2.3/content",
                    action="materialize_local_skill",
                ),
            ]
        ),
        installed_skills=[
            InstalledSkillDto(
                slug="dep.core",
                version="0.9.0",
                install_path=str(
                    Path(materialized_root) / "skills" / "dep.core" / "0.9.0"
                ),
            ),
            InstalledSkillDto(
                slug="python.lint",
                version="1.2.3",
                install_path=str(
                    Path(materialized_root) / "skills" / "python.lint" / "1.2.3"
                ),
            ),
        ],
        materialized_root=materialized_root,
        trace=[
            TraceEntryDto(
                stage="install",
                action="materialize_graph",
                message="Installed locally.",
                data={},
            )
        ],
    )


async def _wait_for(
    predicate,
    *,
    timeout: float = 2.0,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("Timed out waiting for UI state change.")


def _has_widget(app: AptitudeInstallerApp, selector: str) -> bool:
    """Return whether the current DOM contains the selector."""

    return sum(1 for _ in app.screen.query(selector)) > 0


def _rendered_text(widget: Static) -> str:
    """Return the currently rendered text for one static widget."""

    return str(widget.render())


def test_tui_review_flow_handles_candidate_selection() -> None:
    service = FakeWorkflowService(
        resolve_responses=[
            _selection_required_result(),
            _resolved_result(
                slug="js.lint", version="2.1.0", selection_mode="interactive_choice"
            ),
        ]
    )

    async def scenario() -> None:
        app = AptitudeInstallerApp(workflow_service=service)
        async with app.run_test(size=(110, 34)) as pilot:
            await _wait_for(lambda: _has_widget(app, "#query-input"))
            app.screen.query_one("#query-input", Input).value = "lint"
            await pilot.click("#review-plan-button")
            await _wait_for(lambda: _has_widget(app, "#candidate-1"))
            await pilot.click("#candidate-2")
            await _wait_for(lambda: _has_widget(app, "#install-button"))

            assert len(service.resolve_calls) == 2
            assert service.resolve_calls[1]["select_slug"] == "js.lint"
            summary = app.screen.query_one("#plan-summary", Static)
            assert "js.lint" in _rendered_text(summary)

    asyncio.run(scenario())


def test_tui_install_success_shows_result_screen() -> None:
    service = FakeWorkflowService(
        resolve_responses=[_resolved_result()],
        install_responses=[_installed_result()],
    )

    async def scenario() -> None:
        app = AptitudeInstallerApp(workflow_service=service)
        async with app.run_test(size=(110, 34)) as pilot:
            await _wait_for(lambda: _has_widget(app, "#query-input"))
            app.screen.query_one("#query-input", Input).value = "python lint"
            await pilot.click("#review-plan-button")
            await _wait_for(lambda: _has_widget(app, "#install-button"))
            await pilot.click("#install-button")
            await _wait_for(lambda: _has_widget(app, "#result-summary"))

            result_summary = app.screen.query_one("#result-summary", Static)
            assert "Successfully installed" in _rendered_text(result_summary)
            assert service.install_calls[0]["query"] == "python lint"

    asyncio.run(scenario())


def test_tui_resolve_error_shows_error_state() -> None:
    service = FakeWorkflowService(
        resolve_error=InvalidResolverConfigurationError(
            "environment",
            "unsupported interaction mode",
        )
    )

    async def scenario() -> None:
        app = AptitudeInstallerApp(workflow_service=service)
        async with app.run_test(size=(110, 34)) as pilot:
            await _wait_for(lambda: _has_widget(app, "#query-input"))
            app.screen.query_one("#query-input", Input).value = "python lint"
            await pilot.click("#review-plan-button")
            await _wait_for(lambda: _has_widget(app, "#error-summary"))

            error_summary = app.screen.query_one("#error-summary", Static)
            assert "InvalidResolverConfigurationError" in _rendered_text(error_summary)

    asyncio.run(scenario())


def test_tui_candidate_back_navigation_returns_to_query_form() -> None:
    service = FakeWorkflowService(resolve_responses=[_selection_required_result()])

    async def scenario() -> None:
        app = AptitudeInstallerApp(workflow_service=service)
        async with app.run_test(size=(110, 34)) as pilot:
            await _wait_for(lambda: _has_widget(app, "#query-input"))
            query_input = app.screen.query_one("#query-input", Input)
            query_input.value = "lint"
            await pilot.click("#review-plan-button")
            await _wait_for(lambda: _has_widget(app, "#candidate-back-button"))
            await pilot.click("#candidate-back-button")
            await _wait_for(lambda: _has_widget(app, "#review-plan-button"))

            restored_input = app.screen.query_one("#query-input", Input)
            assert restored_input.value == "lint"

    asyncio.run(scenario())


def test_tui_query_screen_mounts_in_small_terminal() -> None:
    async def scenario() -> None:
        app = AptitudeInstallerApp(workflow_service=FakeWorkflowService())
        async with app.run_test(size=(80, 24)):
            await _wait_for(lambda: _has_widget(app, "#query-input"))
            query_input = app.screen.query_one("#query-input", Input)
            status = app.screen.query_one("#query-status", Static)
            assert query_input.value == ""
            assert "Review" in _rendered_text(status)

    asyncio.run(scenario())
