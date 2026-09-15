from __future__ import annotations

import builtins
import re
from dataclasses import replace
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from test_census_bundle import _build_bundle

from manafold_census.analysis.model import AnalysisOutcomeV1
from manafold_census.capability.model import CapabilityRefV1
from manafold_census.cli import main
from manafold_census.explorer.render import render_card_search, render_unresolved
from manafold_census.query.api import open_bundle
from manafold_census.query.cards import QueryNotFoundV1, SemanticStateV1
from manafold_census.query.details import (
    CardIdentityV1,
    CardNameResolutionStatusV1,
    CardNameResolutionV1,
)
from manafold_census.reports.build import build_census_derived

ORACLE_ID = "abcdefab-abcd-4abc-8abc-abcdefabcdef"


def _derived_bundle(tmp_path: Path) -> Path:
    _package, bundle = _build_bundle(tmp_path / "fixture")
    return build_census_derived(bundle.output_dir, tmp_path / "derived").output_dir


def _capability_text(ref: CapabilityRefV1) -> str:
    return f"{ref.capability_family_id}/{ref.capability_version}/{ref.claim_digest}"


def test_explorer_info_and_exact_card_search(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _derived_bundle(tmp_path)

    assert main(["explorer", "--bundle", str(root), "info"]) == 0
    output = capsys.readouterr().out
    assert "Census release" in output
    assert "…" not in output
    digest = open_bundle(root).metadata().census_manifest_sha256
    assert digest in re.sub(r"[\s|│]", "", output)

    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "card",
                "search",
                "Fixture",
                "Card",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "AMBIGUOUS" in output
    assert "matches=5" in output


def test_explorer_card_show_and_capability_list_are_offline(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _derived_bundle(tmp_path)

    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "card",
                "show",
                ORACLE_ID,
            ]
        )
        == 0
    )
    assert "semantic_state" in capsys.readouterr().out

    assert main(["explorer", "--bundle", str(root), "capability", "list"]) == 0
    assert "Draw cards" in capsys.readouterr().out

    assert main(["explorer", "--bundle", str(root), "unresolved"]) == 0
    assert "unresolved_cards=0" in capsys.readouterr().out


def test_explorer_unknown_and_ambiguous_card_show_are_explicit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _derived_bundle(tmp_path)

    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "card",
                "show",
                "Fixture",
                "Card",
            ]
        )
        == 0
    )
    assert "AMBIGUOUS" in capsys.readouterr().out

    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "card",
                "show",
                "not",
                "a",
                "card",
            ]
        )
        == 0
    )
    assert "UNKNOWN" in capsys.readouterr().out


def test_explorer_trace_capability_and_deck_commands_delegate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _derived_bundle(tmp_path / "bundle")
    reader = open_bundle(root)
    card = reader.get_card(ORACLE_ID)
    assert not isinstance(card, QueryNotFoundV1)
    requirement_id = card.requirement_details[0].requirement_id
    link_id = card.requirement_details[0].links[0].link_id
    capability_ref = card.capability_details[0].definition.capability_ref

    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "requirement",
                "show",
                requirement_id,
            ]
        )
        == 0
    )
    assert requirement_id in capsys.readouterr().out

    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "trace",
                "mapping",
                link_id,
            ]
        )
        == 0
    )
    assert link_id in capsys.readouterr().out

    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "capability",
                "show",
                _capability_text(capability_ref),
            ]
        )
        == 0
    )
    assert "Draw cards" in capsys.readouterr().out

    deck_path = tmp_path / "deck.txt"
    deck_path.write_bytes(b"[main]\n1 Fixture Card\n")
    assert (
        main(
            [
                "explorer",
                "--bundle",
                str(root),
                "deck",
                "analyze",
                str(deck_path),
            ]
        )
        == 0
    )
    assert "AMBIGUOUS" in capsys.readouterr().out


def test_explorer_shell_reuses_commands_and_exits(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _derived_bundle(tmp_path)
    commands = iter(("info", "card search Fixture Card", "exit"))
    monkeypatch.setattr(builtins, "input", lambda _prompt: next(commands))

    assert main(["explorer", "--bundle", str(root), "shell"]) == 0
    output = capsys.readouterr().out
    assert "Census release" in output
    assert "AMBIGUOUS" in output


def test_explorer_rejects_missing_bundle(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "missing"
    assert main(["explorer", "--bundle", str(missing), "info"]) == 1
    assert "explorer=FAIL" in capsys.readouterr().err


def test_query_navigation_seams_are_public_and_canonical(tmp_path: Path) -> None:
    reader = open_bundle(_derived_bundle(tmp_path))

    views = reader.list_card_semantic_views()
    capabilities = reader.list_capabilities()
    capability_ref = capabilities[0].definition.capability_ref
    requirements = reader.get_requirements_for_capability(capability_ref)
    missing = reader.get_requirements_for_capability(
        replace(capability_ref, claim_digest="f" * 64)
    )

    assert tuple(view.oracle_id for view in views) == tuple(
        sorted(view.oracle_id for view in views)
    )
    assert len(capabilities) == 1
    assert requirements == capabilities[0].linked_requirements
    assert isinstance(missing, QueryNotFoundV1)


def test_unresolved_renderer_displays_query_state_without_inference(
    tmp_path: Path,
) -> None:
    reader = open_bundle(_derived_bundle(tmp_path))
    view = reader.get_card_semantic_view(ORACLE_ID)
    assert not isinstance(view, QueryNotFoundV1)
    unresolved = replace(
        view,
        analysis_outcome=AnalysisOutcomeV1.UNRESOLVED_ANALYSIS,
        semantic_state=SemanticStateV1.UNRESOLVED_ANALYSIS,
    )
    output = StringIO()
    Console(file=output, markup=False, highlight=False).print(
        render_unresolved((unresolved,))
    )

    assert "UNRESOLVED_ANALYSIS" in output.getvalue()
    assert "unresolved_cards=1" in output.getvalue()


def test_rich_renderer_keeps_untrusted_brackets_as_text() -> None:
    identity = CardIdentityV1(
        "abcdefab-abcd-4abc-8abc-abcdefabcdef",
        "abcdefab-abcd-4abc-8abc-abcdefabcdeb",
        "b" * 64,
        "[red] card",
    )
    resolution = CardNameResolutionV1(
        "[red] card",
        "[red] card",
        CardNameResolutionStatusV1.RESOLVED,
        (identity,),
    )
    output = StringIO()
    Console(file=output, markup=False, highlight=False).print(
        render_card_search(resolution)
    )

    assert "[red] card" in output.getvalue()
