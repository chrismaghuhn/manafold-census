# M3 Reference Conformance — Synthetic Evidence

```text
REFERENCE_HEAD = daedc9ee79a493f8ebe60684cf9d94d47c43e80d
REFERENCE_PARENT = 68076f6f4956523e7dd28102878eda0f23f78723
M3_DESIGN = docs/superpowers/specs/2026-09-13-global-requirement-candidate-extraction-design.md
M3_PLAN = docs/superpowers/plans/2026-09-13-global-requirement-candidate-extraction.md
SCOPE = SYNTHETIC_ONLY
GLOBAL_EXTRACTION_STARTED = NO
```

## Conformance matrix

```text
ONE_M1_RECORD_TO_ONE_CARD_ANALYSIS_RECORD       = PASS
ZERO_REQUIREMENTS_WITHOUT_AUTHORITY             = PASS
ZERO_REQUIREMENTS_WITH_VALID_AUTHORITY          = PASS
PATTERN_REQUIREMENT_REVIEW_PROPOSED_ONLY        = PASS
TERMINAL_PRODUCER_REVIEW_EXECUTION_FAILURE      = PASS
SAME_ID_SAME_RESOLUTION_MONOTONE_MERGE          = PASS
SAME_ID_DIFFERENT_RESOLUTION_DISPUTED           = PASS
DIFFERENT_IDS_RETAINED_WITHOUT_PRIORITY         = PASS
EXPLICIT_CONFLICT_RELATIONSHIP_ONLY             = PASS
REPORT_DOWNSTREAM_OF_ANALYSIS_MANIFEST          = PASS
PARTITION_COUNTS_1_2_8_16                       = PASS
PARTITION_CANONICAL_PACKAGE_BYTES              = PASS
PARTITION_PACKAGE_DIGEST_PARITY                = PASS
PARTITION_MERGE_PARITY                          = PASS
PARALLEL_BACKEND                                = NOT_IMPLEMENTED
MISSING_SOURCE_KEY_CLOSURE_FAILURE              = PASS
DUPLICATE_SOURCE_KEY_CLOSURE_FAILURE            = PASS
EXTRA_SOURCE_KEY_CLOSURE_FAILURE                = PASS
```

Partition parity compares canonical record/trace shard bytes, manifest bytes,
and the complete package directory digest after in-process partition/merge for
counts 1, 2, 8, and 16. No workers, threads, processes, or parallel backend
were started.

The extra-source closure case uses a new validly formed source identity and
fails with `missing=0 extra=1`; it is distinct from the duplicate-key case.

## Gates

```text
FOCUSED_CONFORMANCE_TESTS = PASS (10 passed)
FULL_PYTEST               = PASS (550 passed)
RUFF_FORMAT               = PASS
RUFF                      = PASS
MYPY                      = PASS
REPRODUCTION              = PASS
SYNTHETIC_CORPUS          = PASS
SYNTHETIC_STRUCTURAL      = PASS
M3_CHECK_SYNTHETIC        = PASS
LOCAL_WHEEL_BUILD         = PASS
LOCAL_FRESH_WHEEL_SMOKE   = PASS
```

The local fresh-wheel run executed the bounded `m3-build`, `m3-check`, and
`m3-report` commands from a newly installed non-editable wheel.

## Scope and runtime status

```text
M1_FILES_CHANGED = 0
M2_FILES_CHANGED = 0
M4_FILES_CHANGED = 0
GLOBAL_EXTRACTION_STARTED = NO
PR_AUTHORIZED = NO
MERGE_AUTHORIZED = NO

MAX_SINGLE_TEST_RUNTIME_SECONDS            = 600
MAX_SINGLE_GATE_SUBPROCESS_RUNTIME_SECONDS = 600
PER_TEST_TIMEOUT_ENFORCEMENT               = BLOCKED
LOCAL_COMMAND_TIMEOUT_ENFORCEMENT          = EXTERNAL_EXECUTION_ENVIRONMENT
HOSTED_PER_STEP_600S_ENFORCEMENT           = NOT_IMPLEMENTED
OVER_600S_NORMAL_TESTS                     = NONE_OBSERVED
OVER_600S_NORMAL_GATE_COMMANDS             = NONE_OBSERVED
TIMEOUT_DIAGNOSTIC_TESTED                  = NO
LONG_RUNNING_WORKLOADS_IN_NORMAL_PR_GATE  = NO
```
