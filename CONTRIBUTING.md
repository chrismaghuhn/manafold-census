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
