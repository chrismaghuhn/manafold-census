# M3 Task 11 Unblock Review Packet

```text
REFERENCE_HEAD = d75d0188480b18f5c72ba7f5b002740d05c8496b
TASK_11 = BLOCKED_SEMANTIC_CONFIGURATION
GLOBAL_EXTRACTION_STARTED = NO
TASK_11_RETRY_ALLOWED = NO
```

## Decision summary

```text
CURRENT_BLOCKER = no authorized corpus-scale producer configuration
RECOMMENDED_ARCHITECTURE = registry-driven exact-pattern producer
PROPOSED_MINIMUM_SEMANTIC_SCOPE = one reviewed exact fragment rule
CORPUS_REGISTRY_NAMESPACE = config/analysis/m3-corpus-pattern-registry.v1.json
REVIEW_AUTHORITY_REQUIRED = YES
NEW_SCHEMA_REQUIRED = NO for the first configuration
PRODUCTION_CODE_REQUIRED = YES
TASK_10_REVALIDATION_REQUIRED = YES
TASK_11_RETRY_ALLOWED = NO
```

The existing `m3.synthetic.no-match` adapter is bounded synthetic infrastructure,
not corpus semantic coverage. The exact pattern producer is currently test-only,
and the existing pattern registry uses fixture review identities. Neither is
silently promoted to corpus authority.

The corpus registry will live under `config/analysis/`, while
`fixtures/analysis/*` remains synthetic/test material. Review identity is
acyclic: maintainer decision record -> decision-record SHA ->
`PatternEligibilityV1.review_record_sha256` -> effective registry digest ->
downstream campaign configuration. The decision record never contains the
resulting effective registry digest.

The proposed `draw_cards` output is complete and explicit:

```text
drawer.role         = source
drawer.multiplicity = one
drawer.ordinal      = null
quantity.mode       = exact
quantity.value      = 2
```

The rule remains `NOT_ELIGIBLE` until explicit maintainer review and always
emits Requirements with `review_status = PROPOSED`.

The proposed first configuration enables only one new, corpus-reviewed exact
fragment rule for `"Draw two cards."`. It emits typed `PROPOSED` Requirements;
all nonmatching cards remain `UNRESOLVED_ANALYSIS`. No negative authority,
terminal review, model call, network path, dynamic execution, or engine logic is
included.

## Required follow-up sequence

```text
UNBLOCK_02 = generic registry-driven exact-pattern producer
UNBLOCK_03 = corpus pattern proposal and review packet
UNBLOCK_04 = explicit maintainer approval and frozen effective registry
UNBLOCK_05 = reproducible campaign configuration binding
TASK_11_RETRY = separately authorized Run A / Run B corpus evidence
```

The first production-code slice requires a full Task-10 conformance rerun before
Task 11 can be retried. A successful future closure run will prove artifact
closure and reproducibility, not card semantic certification.

## Current safety status

```text
LIVE_NETWORK_REQUIRED = NO
MODEL_API_REQUIRED = NO
DYNAMIC_EXECUTION_REQUIRED = NO
SYNTHETIC_FIXTURE_AS_AUTHORITY = NO
UNREVIEWED_PATTERN_ACTIVATION = NO
TASK_11_RETRY = NOT_AUTHORIZED
```
