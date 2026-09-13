"""Bounded synthetic M3 maintainer-command support."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from ..canonical import canonical_json_bytes
from ..resources import project_data_root
from ..semantic.model import DerivationMethodV1
from ..structural.build import build_structural_corpus
from ..structural.model import StructuralCardRecordV1
from ..structural.synthetic import _write_synthetic_input
from .build import build_reference_m3
from .manifest import AnalysisManifestV1
from .patterns import EffectivePatternRegistryV1
from .producer import CandidateProducerV1, ProducerDescriptorV1, ProducerResultV1
from .registry import ProducerRegistryV1
from .report import ValidatedAnalysisRunV1, build_reports
from .validate import validate_analysis_closure


def _write_m3_synthetic_input(root: Path) -> tuple[Path, Path]:
    source_path, lock_path = _write_synthetic_input(root)
    records = gzip.decompress(source_path.read_bytes()).splitlines()
    records.append(
        b'{"id":"66666666-6666-4666-8666-666666666667","layout":"normal",'
        b'"name":"Synthetic Extra","object":"card",'
        b'"oracle_id":"66666666-6666-4666-8666-666666666666"}'
    )
    source_path.write_bytes(gzip.compress(b"\n".join(records) + b"\n", mtime=0))
    measurement = source_path.stat()
    lock = json.loads(lock_path.read_bytes())
    lock["artifacts"][0].update(
        sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
        byte_length=measurement.st_size,
    )
    lock_path.write_bytes(canonical_json_bytes(lock))
    return source_path, lock_path


def m3_command(command: str, args: argparse.Namespace) -> int:
    output, structural, source_lock = map(
        Path, (args.output, args.structural_output, args.source_lock)
    )
    if not args.synthetic:
        raise ValueError(f"m3-{command} requires --synthetic")
    if command == "build":
        if any(path.exists() for path in (output, structural, source_lock)):
            raise ValueError("m3 synthetic output paths must be fresh")
        descriptor = ProducerDescriptorV1(
            *(
                "m3.synthetic.no-match",
                "1",
                DerivationMethodV1.DETERMINISTIC_RULE,
                StructuralCardRecordV1.SCHEMA,
                ("layout",),
                None,
                True,
                False,
            )
        )
        producer = cast(
            CandidateProducerV1,
            SimpleNamespace(
                descriptor=descriptor, produce=lambda *_: ProducerResultV1.no_match()
            ),
        )
        with tempfile.TemporaryDirectory(prefix="census-m3-input-") as temp:
            source, lock = _write_m3_synthetic_input(Path(temp))
            build_structural_corpus(source, lock, structural)
            source_lock.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(lock, source_lock)
        pattern_path = (
            project_data_root() / "fixtures/analysis/pattern-registry.v1.json"
        )
        pattern = EffectivePatternRegistryV1.from_wire(
            json.loads(pattern_path.read_bytes())
        )
        build_reference_m3(
            structural,
            ProducerRegistryV1.build([descriptor]),
            pattern,
            output,
            producer_implementations=(producer,),
            source_lock_path=source_lock,
        )
        print("m3-build=PASS")
        return 0
    validated = validate_analysis_closure(structural, output, source_lock)
    manifest = AnalysisManifestV1.from_wire(
        json.loads((output / "analysis-manifest.json").read_bytes())
    )
    result = SimpleNamespace(
        manifest=manifest, records=validated[0].values, traces=validated[1].values
    )
    if command == "check":
        print("m3-check=PASS")
        return 0
    index_path = output / "report-index.json"
    if (
        index_path.exists()
        and json.loads(index_path.read_bytes()).get("analysis_manifest_sha256")
        != manifest.digest()
    ):
        raise ValueError("report-index analysis manifest mismatch")
    build_reports(cast(ValidatedAnalysisRunV1, result), output)
    print("m3-report=PASS")
    return 0


__all__ = ["m3_command"]
