"""Root-CLI registration and dispatch for M6-02 inventory commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .build import build_inventory
from .input import InventoryInputsV1, load_inventory_inputs
from .validate import validate_inventory_against_inputs


def _add_parent_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-lock", required=True)
    parser.add_argument("--structural-output", required=True)
    parser.add_argument("--analysis-output", required=True)
    parser.add_argument("--m4-output", required=True)
    parser.add_argument("--parent-census-release-id", required=True)
    parser.add_argument("--expected-selected-count", type=int, default=38_735)


def _add_input_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    help_text: str,
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text)
    _add_parent_arguments(parser)
    return parser


def add_m6_02_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register all explicit M6-02 maintainer commands."""

    build_parser = _add_input_command(
        subparsers,
        "m6-02-inventory-build",
        "build a non-authoritative M6-02 inventory",
    )
    build_parser.add_argument("--output", required=True)

    check_parser = _add_input_command(
        subparsers,
        "m6-02-inventory-check",
        "validate an explicit M6-02 inventory",
    )
    check_parser.add_argument("--output", required=True)

    report_parser = _add_input_command(
        subparsers,
        "m6-02-inventory-report",
        "print an explicit M6-02 inventory report",
    )
    report_parser.add_argument("--output", required=True)

    reproduce_parser = _add_input_command(
        subparsers,
        "m6-02-inventory-reproduce",
        "build two explicit M6-02 inventory candidates",
    )
    reproduce_parser.add_argument("--output-root", required=True)
    reproduce_parser.add_argument("--evidence-json", required=True)
    reproduce_parser.add_argument("--evidence-markdown", required=True)


def _inputs(args: argparse.Namespace) -> InventoryInputsV1:
    return InventoryInputsV1(
        source_lock_path=Path(args.source_lock),
        structural_output_directory=Path(args.structural_output),
        analysis_output_directory=Path(args.analysis_output),
        m4_output_directory=Path(args.m4_output),
        parent_census_release_id=args.parent_census_release_id,
        expected_selected_count=args.expected_selected_count,
    )


def dispatch_m6_02_command(args: argparse.Namespace) -> int | None:
    """Dispatch one M6-02 command, returning None for unrelated commands."""

    if args.command == "m6-02-inventory-build":
        result = build_inventory(_inputs(args), args.output)
        print(
            f"selected_unresolved_oracle_id_count={result.manifest.selected_identity_count}"
        )
        print(f"surface_count={result.manifest.total_surface_count}")
        print(f"candidate_group_count={result.manifest.candidate_group_count}")
        print(f"opportunity_count={result.manifest.opportunity_count}")
        print(f"output_tree_digest={result.output_tree_digest}")
        print("m6-02-inventory-build=PASS")
        return 0
    if args.command in {"m6-02-inventory-check", "m6-02-inventory-report"}:
        loaded = load_inventory_inputs(_inputs(args))
        validated = validate_inventory_against_inputs(args.output, loaded)
        if args.command == "m6-02-inventory-report":
            print(json.dumps(validated.report.to_wire(), ensure_ascii=False))
            print("m6-02-inventory-report=PASS")
        else:
            print(f"output_tree_digest={validated.output_tree_digest}")
            print("m6-02-inventory-check=PASS")
        return 0
    if args.command == "m6-02-inventory-reproduce":
        from .reproduction import reproduce_inventory

        reproduced = reproduce_inventory(
            _inputs(args),
            args.output_root,
            args.evidence_json,
            args.evidence_markdown,
        )
        print(
            f"selected_unresolved_oracle_id_count={reproduced.selected_identity_count}"
        )
        print(f"output_tree_digest={reproduced.output_tree_digest}")
        print("m6-02-inventory-reproduce=PASS")
        return 0
    return None


__all__ = ["add_m6_02_parsers", "dispatch_m6_02_command"]
