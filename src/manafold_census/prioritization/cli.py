"""Root-CLI registration and dispatch for M6-03 prioritization commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build import build_prioritization
from .input import PrioritizationInputsV1, load_prioritization_inputs
from .validate import validate_prioritization_against_inputs


def _add_parent_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--m6-02-output", required=True)
    parser.add_argument("--source-lock", required=True)
    parser.add_argument("--structural-output", required=True)
    parser.add_argument("--analysis-output", required=True)
    parser.add_argument("--m4-output", required=True)
    parser.add_argument("--parent-census-release-id", required=True)
    parser.add_argument("--expected-opportunity-count", type=int, default=10_732)


def _add_input_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text)
    _add_parent_arguments(parser)
    return parser


def add_m6_03_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register all explicit M6-03 maintainer commands."""

    build_parser = _add_input_command(
        subparsers,
        "m6-03-opportunity-build",
        "build a non-authoritative M6-03 prioritization",
    )
    build_parser.add_argument("--output", required=True)

    check_parser = _add_input_command(
        subparsers,
        "m6-03-opportunity-check",
        "validate an explicit M6-03 prioritization",
    )
    check_parser.add_argument("--output", required=True)

    report_parser = _add_input_command(
        subparsers,
        "m6-03-opportunity-report",
        "print an explicit M6-03 prioritization report",
    )
    report_parser.add_argument("--output", required=True)

    reproduce_parser = _add_input_command(
        subparsers,
        "m6-03-opportunity-reproduce",
        "build two explicit M6-03 prioritization candidates",
    )
    reproduce_parser.add_argument("--output-root", required=True)
    reproduce_parser.add_argument("--evidence-json", required=True)
    reproduce_parser.add_argument("--evidence-markdown", required=True)


def _inputs(args: argparse.Namespace) -> PrioritizationInputsV1:
    return PrioritizationInputsV1(
        m6_02_output_directory=Path(args.m6_02_output),
        source_lock_path=Path(args.source_lock),
        structural_output_directory=Path(args.structural_output),
        analysis_output_directory=Path(args.analysis_output),
        m4_output_directory=Path(args.m4_output),
        parent_census_release_id=args.parent_census_release_id,
        expected_opportunity_count=args.expected_opportunity_count,
    )


def dispatch_m6_03_command(args: argparse.Namespace) -> int | None:
    """Dispatch one M6-03 command, returning None for unrelated commands."""

    if args.command == "m6-03-opportunity-build":
        result = build_prioritization(_inputs(args), args.output)
        print(f"input_opportunity_count={result.manifest.input_opportunity_count}")
        print(
            f"non_noise_opportunity_count={result.manifest.non_noise_opportunity_count}"
        )
        print(
            f"planning_noise_opportunity_count="
            f"{result.manifest.planning_noise_opportunity_count}"
        )
        print(
            f"mechanical_overlap_cluster_count="
            f"{result.manifest.mechanical_overlap_cluster_count}"
        )
        print(f"review_packet_count={result.manifest.review_packet_count}")
        print(f"output_tree_digest={result.output_tree_digest}")
        print("m6-03-opportunity-build=PASS")
        return 0
    if args.command in {"m6-03-opportunity-check", "m6-03-opportunity-report"}:
        loaded = load_prioritization_inputs(_inputs(args))
        validated = validate_prioritization_against_inputs(args.output, loaded)
        if args.command == "m6-03-opportunity-report":
            print(json.dumps(validated.report.to_wire(), ensure_ascii=False))
            print("m6-03-opportunity-report=PASS")
        else:
            print(f"output_tree_digest={validated.output_tree_digest}")
            print("m6-03-opportunity-check=PASS")
        return 0
    if args.command == "m6-03-opportunity-reproduce":
        from .reproduction import reproduce_prioritization

        reproduced = reproduce_prioritization(
            _inputs(args),
            args.output_root,
            args.evidence_json,
            args.evidence_markdown,
        )
        print(f"input_opportunity_count={reproduced.input_opportunity_count}")
        print(f"output_tree_digest={reproduced.output_tree_digest}")
        print("m6-03-opportunity-reproduce=PASS")
        return 0
    return None


__all__ = ["add_m6_03_parsers", "dispatch_m6_03_command"]
