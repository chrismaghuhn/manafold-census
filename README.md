# manafold-census

`manafold-census` is an independent Python project for deterministic
Magic: The Gathering data-census and research foundations. Task 00 provides
only the source, dataset, study, and artifact identity contracts plus a tiny
synthetic fixture pipeline.

It is not a rules engine, a Manafold package, an authority generator, or a
semantic truth system. Imported, parsed, generated, candidate, and exported
data remain distinct from supported or authoritative data.

Task 01 adds one explicit real-data source path: the current Scryfall
`oracle_cards` bulk snapshot. It pins the compressed source bytes in an
ignored local cache, commits a small generic source lock, and creates a
source-record inventory with 16 deterministic Oracle-ID shards. Completeness
is source-bounded: 100% means every valid record in the exact pinned snapshot,
not every Magic card that has ever existed. The inventory is `SOURCE_FACT`
provenance only and does not parse Oracle text or infer capabilities.

Canonical JSON, domain-separated SHA-256 digests, explicit provenance, and
byte-level reproduction remain the foundation. Raw bulk data is disposable and
is never committed.

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

The explicit live-source commands are separate from the offline check path:

```text
just source-discover
just source-acquire
just corpus-build
just corpus-check
```

`source-acquire` is an intentional refresh operation. It streams one HTTPS
gzip JSONL download to a temporary file, verifies the complete bytes, and then
promotes it atomically into `.cache/sources/scryfall/`. Ordinary tests, CI, and
`just check` use synthetic data and do not require Scryfall availability.

The `reproduce` command builds the synthetic fixture twice in independent
temporary directories and requires identical semantic files and SHA-256
digests.
