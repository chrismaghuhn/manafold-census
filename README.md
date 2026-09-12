# manafold-census

`manafold-census` is an independent Python project for deterministic
Magic: The Gathering data-census and research foundations. Task 00 provides
only the source, dataset, study, and artifact identity contracts plus a tiny
synthetic fixture pipeline.

It is not a rules engine, a Manafold package, an authority generator, or a
semantic truth system. Imported, parsed, generated, candidate, and exported
data remain distinct from supported or authoritative data. No real MTG data
or network acquisition is included.

The current project is deliberately immature: later acquisition, normalization,
census, analysis, and review systems are not implemented here. Canonical JSON,
domain-separated SHA-256 digests, explicit provenance, and byte-level
reproduction are the current foundation.

## Local golden path

Install the minimal development tools:

```text
python -m pip install -e ".[dev]"
```

Then run:

```text
just doctor
just test
just lint
just typecheck
just reproduce
just check
```

The `reproduce` command builds the synthetic fixture twice in independent
temporary directories and requires identical semantic files and SHA-256
digests.
