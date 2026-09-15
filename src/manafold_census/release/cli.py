"""M5-specific parser registration and command dispatch."""

from __future__ import annotations

import argparse

from .commands import (
    build_census_bundle_command,
    build_census_derived_command,
    build_real_m4_snapshot_command,
    check_census_authority_package_command,
    check_census_input_lock_command,
)


def add_m5_parsers(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    input_lock_parser = subparsers.add_parser(
        "m5-input-lock-check",
        help="validate a CensusInputLockV1 against explicit artifact paths",
    )
    input_lock_parser.add_argument("--lock", required=True)
    input_lock_parser.add_argument("--source-lock", required=True)
    input_lock_parser.add_argument("--structural-output", required=True)
    input_lock_parser.add_argument("--analysis-output", required=True)
    authority_parser = subparsers.add_parser(
        "m5-authority-check",
        help="validate the explicit Census 0.1 M4 authority package",
    )
    authority_parser.add_argument("--package", required=True)
    authority_parser.add_argument("--lock", required=True)
    authority_parser.add_argument("--source-lock", required=True)
    authority_parser.add_argument("--structural-output", required=True)
    authority_parser.add_argument("--analysis-output", required=True)
    m4_real_parser = subparsers.add_parser(
        "m5-m4-build",
        help="build the first real M4 snapshot from explicit M5 inputs",
    )
    m4_real_parser.add_argument("--input-lock", required=True)
    m4_real_parser.add_argument("--authority-package", required=True)
    m4_real_parser.add_argument("--source-lock", required=True)
    m4_real_parser.add_argument("--structural-output", required=True)
    m4_real_parser.add_argument("--analysis-output", required=True)
    m4_real_parser.add_argument("--output", required=True)
    bundle_parser = subparsers.add_parser(
        "m5-bundle-build",
        help="publish the self-contained Census 0.1 bundle",
    )
    bundle_parser.add_argument("--input-lock", required=True)
    bundle_parser.add_argument("--authority-package", required=True)
    bundle_parser.add_argument("--source-lock", required=True)
    bundle_parser.add_argument("--structural-output", required=True)
    bundle_parser.add_argument("--analysis-output", required=True)
    bundle_parser.add_argument("--m4-output", required=True)
    bundle_parser.add_argument("--output", required=True)
    derived_parser = subparsers.add_parser(
        "m5-derived-build",
        help="publish derived Census 0.1 reports and canonical indexes",
    )
    derived_parser.add_argument("--bundle", required=True)
    derived_parser.add_argument("--output", required=True)


def dispatch_m5_command(args: argparse.Namespace) -> int | None:
    if args.command == "m5-input-lock-check":
        return check_census_input_lock_command(
            args.lock,
            args.source_lock,
            args.structural_output,
            args.analysis_output,
        )
    if args.command == "m5-authority-check":
        return check_census_authority_package_command(
            args.package,
            args.lock,
            args.source_lock,
            args.structural_output,
            args.analysis_output,
        )
    if args.command == "m5-m4-build":
        return build_real_m4_snapshot_command(
            args.input_lock,
            args.authority_package,
            args.source_lock,
            args.structural_output,
            args.analysis_output,
            args.output,
        )
    if args.command == "m5-bundle-build":
        return build_census_bundle_command(
            args.input_lock,
            args.authority_package,
            args.source_lock,
            args.structural_output,
            args.analysis_output,
            args.m4_output,
            args.output,
        )
    if args.command == "m5-derived-build":
        return build_census_derived_command(args.bundle, args.output)
    return None


__all__ = ["add_m5_parsers", "dispatch_m5_command"]
