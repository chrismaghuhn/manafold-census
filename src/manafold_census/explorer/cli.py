"""Offline Explorer command registration and dispatch."""

from __future__ import annotations

import argparse
import shlex

from rich.console import Console, Group

from ..capability.model import CapabilityRefV1
from ..query.api import CensusReader, open_bundle
from ..query.cards import QueryNotFoundV1, SemanticStateV1
from ..query.deck import analyze_deck_file
from ..query.details import CardNameResolutionV1
from .render import (
    render_capability_detail,
    render_capability_list,
    render_card_detail,
    render_card_search,
    render_deck_analysis,
    render_info,
    render_mapping_trace,
    render_not_found,
    render_requirement_trace,
    render_unresolved,
    render_view_context,
)


def _add_explorer_commands(parser: argparse.ArgumentParser) -> None:
    commands = parser.add_subparsers(
        dest="explorer_command",
        required=True,
    )
    commands.add_parser("info", help="show validated Census identities")

    card_parser = commands.add_parser("card", help="navigate card identities")
    card_commands = card_parser.add_subparsers(
        dest="card_command",
        required=True,
    )
    card_search = card_commands.add_parser(
        "search",
        help="run exact/casefolded card-name lookup",
    )
    card_search.add_argument("text", nargs="+")
    card_show = card_commands.add_parser("show", help="show one card detail")
    card_show.add_argument("identifier", nargs="+")

    requirement_parser = commands.add_parser(
        "requirement",
        help="show one Requirement trace",
    )
    requirement_commands = requirement_parser.add_subparsers(
        dest="requirement_command",
        required=True,
    )
    requirement_show = requirement_commands.add_parser("show")
    requirement_show.add_argument("requirement_id")

    capability_parser = commands.add_parser(
        "capability",
        help="navigate Capability definitions",
    )
    capability_commands = capability_parser.add_subparsers(
        dest="capability_command",
        required=True,
    )
    capability_commands.add_parser("list", help="list Capability definitions")
    capability_show = capability_commands.add_parser("show")
    capability_show.add_argument("capability_ref")

    trace_parser = commands.add_parser("trace", help="show provenance traces")
    trace_commands = trace_parser.add_subparsers(
        dest="trace_command",
        required=True,
    )
    trace_requirement = trace_commands.add_parser("requirement")
    trace_requirement.add_argument("requirement_id")
    trace_mapping = trace_commands.add_parser("mapping")
    trace_mapping.add_argument("link_id")

    commands.add_parser("unresolved", help="list unresolved Card states")

    deck_parser = commands.add_parser("deck", help="analyze one deck file")
    deck_commands = deck_parser.add_subparsers(
        dest="deck_command",
        required=True,
    )
    deck_analyze = deck_commands.add_parser("analyze")
    deck_analyze.add_argument("deck_file")

    commands.add_parser("shell", help="open the bounded offline shell")


def add_explorer_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser(
        "explorer",
        help="navigate one validated Census bundle offline",
    )
    parser.add_argument("--bundle", required=True)
    _add_explorer_commands(parser)


def _shell_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="explorer",
        add_help=False,
    )
    _add_explorer_commands(parser)
    return parser


def _parse_capability_ref(value: str) -> CapabilityRefV1:
    parts = value.split("/")
    if len(parts) != 3 or any(not part for part in parts):
        raise ValueError("Capability reference must be family_id/version/claim_digest")
    try:
        version = int(parts[1])
    except ValueError as error:
        raise ValueError("Capability version must be an integer") from error
    return CapabilityRefV1(parts[0], version, parts[2])


def _print(console: Console, value: object) -> None:
    console.print(value)


def _print_view(console: Console, reader: CensusReader, value: object) -> None:
    console.print(Group(render_view_context(reader.metadata()), value))


def _run_action(
    reader: CensusReader,
    args: argparse.Namespace,
    console: Console,
) -> None:
    command = args.explorer_command
    if command == "info":
        _print(console, render_info(reader.metadata()))
        return
    if command == "card":
        identifier = " ".join(args.identifier) if args.card_command == "show" else None
        if args.card_command == "search":
            _print_view(
                console,
                reader,
                render_card_search(reader.search_cards(" ".join(args.text))),
            )
            return
        if identifier is None:
            raise ValueError("card command is missing an identifier")
        card_result = reader.get_card(identifier)
        if isinstance(card_result, QueryNotFoundV1):
            name_result = reader.get_card_by_name(identifier)
        else:
            name_result = card_result
        if isinstance(name_result, QueryNotFoundV1):
            _print_view(console, reader, render_not_found(name_result))
        elif isinstance(name_result, CardNameResolutionV1):
            _print_view(console, reader, render_card_search(name_result))
        else:
            _print_view(console, reader, render_card_detail(name_result))
        return
    if command == "requirement":
        requirement_result = reader.trace_requirement(args.requirement_id)
        if isinstance(requirement_result, QueryNotFoundV1):
            _print_view(console, reader, render_not_found(requirement_result))
        else:
            _print_view(console, reader, render_requirement_trace(requirement_result))
        return
    if command == "capability":
        if args.capability_command == "list":
            _print_view(
                console, reader, render_capability_list(reader.list_capabilities())
            )
            return
        capability_result = reader.get_capability(
            _parse_capability_ref(args.capability_ref)
        )
        if isinstance(capability_result, QueryNotFoundV1):
            _print_view(console, reader, render_not_found(capability_result))
        else:
            _print_view(console, reader, render_capability_detail(capability_result))
        return
    if command == "trace":
        if args.trace_command == "requirement":
            requirement_result = reader.trace_requirement(args.requirement_id)
            if isinstance(requirement_result, QueryNotFoundV1):
                _print_view(console, reader, render_not_found(requirement_result))
            else:
                _print_view(
                    console, reader, render_requirement_trace(requirement_result)
                )
            return
        mapping_result = reader.trace_mapping(args.link_id)
        if isinstance(mapping_result, QueryNotFoundV1):
            _print_view(console, reader, render_not_found(mapping_result))
        else:
            _print_view(console, reader, render_mapping_trace(mapping_result))
        return
    if command == "unresolved":
        views = tuple(
            view
            for view in reader.list_card_semantic_views()
            if view.semantic_state is SemanticStateV1.UNRESOLVED_ANALYSIS
        )
        _print_view(console, reader, render_unresolved(views))
        return
    if command == "deck":
        if args.deck_command != "analyze":
            raise ValueError("unsupported deck command")
        _print_view(
            console,
            reader,
            render_deck_analysis(analyze_deck_file(args.deck_file, reader)),
        )
        return
    if command == "shell":
        _run_shell(reader, console)
        return
    raise ValueError("unsupported Explorer command")


def _run_shell(reader: CensusReader, console: Console) -> None:
    parser = _shell_parser()
    while True:
        try:
            line = input("explorer> ")
        except EOFError:
            return
        if line.strip().casefold() in {"exit", "quit"}:
            return
        if not line.strip():
            continue
        try:
            tokens = shlex.split(line)
            args = parser.parse_args(tokens)
            if args.explorer_command == "shell":
                raise ValueError("nested shell is not supported")
            _run_action(reader, args, console)
        except SystemExit:
            continue
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            _print(console, f"error={error}")


def dispatch_explorer_command(args: argparse.Namespace) -> int | None:
    if args.command != "explorer":
        return None
    reader = open_bundle(args.bundle)
    console = Console(markup=False, highlight=False)
    _run_action(reader, args, console)
    return 0


__all__ = ["add_explorer_parser", "dispatch_explorer_command"]
