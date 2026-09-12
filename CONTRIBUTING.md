# Contributing

Keep changes deterministic and narrowly scoped.

- Add tests for every contract or behavior change.
- Do not introduce hidden timestamps, randomness, host paths, or implicit
  serialization into semantic outputs.
- Do not infer support, authority, certification, or correctness from imported,
  parsed, generated, candidate, proposed, or exported data.
- Report checks explicitly as `PASS`, `FAIL`, `NOT_RUN`, or `BLOCKED`.
- Keep the Python reference implementation simple until real workloads justify
  algorithmic or performance changes.
- Keep Scryfall acquisition explicit and source-bounded. Never replace a
  missing live source with another dataset or an undocumented cache.
- Keep Task 01 inventory records at `SOURCE_FACT` scope; semantic card
  analysis belongs to a separately authorized task.

### M1 structural work

M1 remains source-fact-only. Preserve exact source strings, array order, face
positions, absence versus empty values, and Task 01 four-field identity parity.
Do not add Oracle-text interpretation, Requirements, Capabilities, rules
citations, or semantic classifications.

The offline verification path is:

```text
python -m manafold_census.cli structural-check --synthetic
```

Pinned structural builds use only the committed source lock and its exact
content-addressed cache. They never refresh, download, or substitute a source.
Generated structural records and raw cache bytes remain ignored.

M1 implementation is staged: authorize one numbered task, run its focused and
regression gates, commit, push, verify the remote head, report the exact SHA,
and stop. The next task, pull request, merge, and M2 work require separate
authorization.
