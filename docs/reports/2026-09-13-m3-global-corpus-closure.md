# M3 Global Corpus Closure Evidence

Date: 2026-09-13

This report records the offline two-run closure campaign. It is infrastructure and candidate-extraction evidence only; it is not a certification of card semantics or engine behavior.

## Frozen campaign inputs

```text
REPOSITORY_HEAD = a8d94958a762ce8e6ecfb54a25e739f460c1272f

SOURCE_LOCK_DIGEST             = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
M1_STRUCTURAL_MANIFEST_SHA256  = bdc74ec944798a8c1dd7627dae55a795c6fb72d3bbe067d2f2e50412c7155f2b
M1_STRUCTURAL_AGGREGATE_DIGEST = eb215ca6c904c26baa2d8f0a63928e8c9acab5bb9ea9493eacebcdab2fbb86bb

PATTERN_REGISTRY_PATH   = config/analysis/m3-corpus-pattern-registry.v1.json
PATTERN_REGISTRY_DIGEST = a27effa3d7f5497fca0d9d2e3e3abb562037278b17cf7b17b0f54523d58e5eb1
PRODUCER_REGISTRY_PATH  = config/analysis/m3-corpus-producer-registry.v1.json
PRODUCER_REGISTRY_DIGEST = fca4a0d9318669a372ee1dcded22c55e1fd1fdff7dd470ecd0bbfa9c07be498f
PRODUCER_ID              = m3.registry-exact-pattern
PRODUCER_VERSION         = 1
M3_BUILD_PROFILE         = census.m3-reference.v1
NEGATIVE_AUTHORITY       = NONE
ACTIVE_REVIEWED_PATTERN  = m3.corpus.exact-field.draw-two-cards@1
```

## Run status and closure

```text
RUN_A_OUTPUT_ROOT_ID          = manafold-task11-a8d9495/run-a
RUN_B_OUTPUT_ROOT_ID          = manafold-task11-a8d9495/run-b

RUN_A_RECORD_COUNT             = 38740
RUN_B_RECORD_COUNT             = 38740
RUN_A_TRACE_COUNT              = 38740
RUN_B_TRACE_COUNT              = 38740

RUN_A_MISSING_SOURCE_IDENTITIES = 0
RUN_A_EXTRA_SOURCE_IDENTITIES   = 0
RUN_A_DUPLICATE_IDENTITIES      = 0
RUN_B_MISSING_SOURCE_IDENTITIES = 0
RUN_B_EXTRA_SOURCE_IDENTITIES   = 0
RUN_B_DUPLICATE_IDENTITIES      = 0

M1_M3_IDENTITY_SET_EQUALITY = PASS
PERSISTED_REREAD            = PASS
CLOSURE_VALIDATION          = PASS
```

The campaign used the existing `build_reference_m3()` path with the frozen M1 structural index, frozen registries, and `RegistryDrivenExactPatternProducerV1`. No live source acquisition, cache refresh, model call, parallel backend, or additional producer was used.

## Semantic outcome scope

```text
REQUIREMENTS_PRODUCED      = 5
NO_REQUIREMENTS_APPLICABLE = 0
UNRESOLVED_ANALYSIS        = 38735

EXPECTED_EXACT_FIELD_MATCH_COUNT = 5
```

The five produced records are the five identities from the frozen exact-field M1 census. Each contains exactly one `effect/draw_cards` Requirement with `drawer=source/one/null`, `quantity=exact/2`, and `review.status=PROPOSED`. The remaining 38,735 cards remain explicitly `UNRESOLVED_ANALYSIS` because no negative authority is configured and no other semantic pattern is active.

This campaign does not claim broad Magic semantic coverage, card certification, full semantic understanding, or M4 capability coverage.

## Run-A authoritative digests

```text
ANALYSIS_MANIFEST_SHA256     = f69cd3890de54278c231bb6bd8fb0125a31903c2b01d85c81ad1e5d732f9276f
ANALYSIS_MANIFEST_DIGEST     = f69cd3890de54278c231bb6bd8fb0125a31903c2b01d85c81ad1e5d732f9276f
RECORD_IDENTITY_SET_DIGEST   = acf03f0d67c8d8cbb3067ed5ffb12b33f3f27a7329c327435ef4445d74678ba9
RECORD_INDEX_DIGEST           = 0c5522d64dc6cb50984ca535d8aa5a07d936b0fe6efc8f056d6061fc29af28a6
TRACE_INDEX_DIGEST            = 591d5157e1b1067fa9c6926907c2dda03b89716ce23b051eeb892b49138d5c89
PACKAGE_DIGEST                = 93a6353134d84a43408e31277f0be33535fb57c91fa3c6177576efd7d227c649
```

## Record-shard descriptors

The Run-A descriptors below are also the Run-B descriptors byte-for-byte.

| path | records | bytes | sha256 |
| --- | ---: | ---: | --- |
| records/0.jsonl | 2433 | 1099716 | a3c71d281592da8dd8420edba1cf4d01dfed844bded219d8cda21bc7dee50e03 |
| records/1.jsonl | 2425 | 1096100 | 3a4dea7a9528ef5a9e07ca0131ce3b645509003e5691c677ad6ccf3d9fd0d3c4 |
| records/2.jsonl | 2320 | 1050403 | 3e509a7cfc88fd61126f54976ec2df7a4a77c93fdd52ebd03061ad5aec333798 |
| records/3.jsonl | 2462 | 1112824 | 42268040e1afb78c114a585584b4be1f18956a8d6a676306d2526606e7ca3693 |
| records/4.jsonl | 2400 | 1084800 | ef8003e79719c522bd028cabcded8dd65d5fea21efdf7dead2017a7021df9041 |
| records/5.jsonl | 2395 | 1082540 | 8a11032259f7de96740deb859cd6242473f956a965954b69c43bcb53903fab94 |
| records/6.jsonl | 2425 | 1099626 | 7566b978e78c480b72cb307c62d05eabdc3a7a3987c4e93e166a2e89c3a58be7 |
| records/7.jsonl | 2454 | 1110971 | 185e36ef40f02025966b2799dabfcc6c6bc098ad8eb0dcc16b662a8eb34cb7b4 |
| records/8.jsonl | 2390 | 1080280 | a4312786fedba217414058332d0d6532ac3d35846fb60a816ae2d1e4ee4717af |
| records/9.jsonl | 2430 | 1098360 | 9d9a1db62aa02aa7da289a551a0dbf1ac4b570cf529894b55f4cbdc91cb7355a |
| records/a.jsonl | 2392 | 1081184 | 7b7c39f04fcc580433cefdab94dc4fc7590c1496582da3c1e875f7f0b0bae9 |
| records/b.jsonl | 2407 | 1087964 | 16bd03e50d517b1fa9d017bee2b451031ad17b25a486a76a802a5de9b27b94d2 |
| records/c.jsonl | 2451 | 1107852 | ddb92655494674673ff9a56c5aad54b726f5e94abb57c3e2c5b840f90ebc63df |
| records/d.jsonl | 2416 | 1092032 | bba177363c7230d4bb2938acbb1f92f7eb1fc775de34f6027db1a87bcf5e1651 |
| records/e.jsonl | 2529 | 1143108 | 9672c2ef801f0af551ed4b0809243946f3ac88736e5a6d68ec51f4aa20aed99e |
| records/f.jsonl | 2411 | 1091535 | 156a425de05baeffe8e4733138479551147b5a0d632ad33aaf1be46755c274ed |

## Trace-shard descriptors

| path | records | bytes | sha256 |
| --- | ---: | ---: | --- |
| trace/0.jsonl | 2433 | 1345449 | 39c514acc26148547ebf897659afa6c97d11a068aec77adf6504e53addd94ddf |
| trace/1.jsonl | 2425 | 1341025 | 597180a63d730aae19fc309785f754e776153897fe5fb280a1cf78935c8b1474 |
| trace/2.jsonl | 2320 | 1283131 | 6a0a1454e02cf6585e76e0334faa8f94e103b0a71648304c57ec21718cb98131 |
| trace/3.jsonl | 2462 | 1361486 | 8fbe622d1eebe68b225300312650f3daf13bda41b304433c681309f4226e54cc |
| trace/4.jsonl | 2400 | 1327200 | 4de6fd13222f2f2d36fb6b1d816a10812ca94ed4391030f3b12ba8256a741144 |
| trace/5.jsonl | 2395 | 1324435 | 0809f601e021d3e7aba8d15bdbdb319d88630ec2580f1f44bc5dae5594e383cb |
| trace/6.jsonl | 2425 | 1341367 | 1c234858431718c550bce493e981e38f14fd9d0a3d869a76e99fa577302cc6a5 |
| trace/7.jsonl | 2454 | 1357233 | 1b4f27c86e1550ccde03837c35c8228ee6301267a0da16da35049a676e64a497 |
| trace/8.jsonl | 2390 | 1321670 | 2fb6e35d97f54691ea086c01951778ca5e4e2b7228eb1e73100db8b1d4a3cb08 |
| trace/9.jsonl | 2430 | 1343790 | 1d5d6f212bd01a5c47ffb05b756fcc3b669df18b6ec9442b149e063141dde3ea |
| trace/a.jsonl | 2392 | 1322776 | 4aa48b04d161a94ac0a97ef3fb7e737ab533871a0808f74a94996eb81006d186 |
| trace/b.jsonl | 2407 | 1331071 | 20126e4e16dbfadeda8ccc6cc41d79f97a385125fbb2213a471e878a3cb5a89e |
| trace/c.jsonl | 2451 | 1355403 | 806d5e55d5b7a43eda25e424909f291e18bfe20a28fc73666d470a291b7b6f3a |
| trace/d.jsonl | 2416 | 1336048 | 58610116cc1ff1a8f6fee1e18ddf05fbd2a337b0aa57e9f42e923bd46a25beec |
| trace/e.jsonl | 2529 | 1398537 | 89c86a799af7d309a37823e6ec614dc33dcc51430de6ad03232d2b6d0c235522 |
| trace/f.jsonl | 2411 | 1333454 | ee27a6600e2d6cc5166547961746da1f1fa1c8e667372ef1bd06eb91975614c5 |

## Cross-run parity

```text
RUN_A_RECORD_BYTES == RUN_B_RECORD_BYTES       = PASS
RUN_A_TRACE_BYTES == RUN_B_TRACE_BYTES         = PASS
RUN_A_MANIFEST_BYTES == RUN_B_MANIFEST_BYTES   = PASS
RUN_A_RECORD_SHARD_DIGESTS == RUN_B            = PASS
RUN_A_TRACE_SHARD_DIGESTS == RUN_B             = PASS
RUN_A_IDENTITY_SET_DIGEST == RUN_B             = PASS
RUN_A_PACKAGE_DIGEST == RUN_B                  = PASS
RUN_A_OUTCOME_COUNTS == RUN_B                  = PASS
CROSS_RUN_BYTE_PARITY                         = PASS
GLOBAL_CORPUS_CLOSURE                         = PASS
```

## Regression and status

```text
LOCAL_PYTEST = PASS (578 passed)
LOCAL_RUFF_FORMAT = PASS
LOCAL_RUFF = PASS
LOCAL_MYPY = PASS
TASK_10_CONFORMANCE = PASS
LOCAL_REPRODUCTION_GATES = PASS
LOCAL_M3_SYNTHETIC_GATES = PASS
LOCAL_WHEEL_SMOKE = PASS

HOSTED_GLOBAL_CORPUS = NOT_RUN
HOSTED_NORMAL_CI = REQUIRED_ON_FINAL_REPORT_SHA

M1_MATCH_CENSUS_STARTED = YES
GLOBAL_M3_EXTRACTION_STARTED = YES
TASK_11_RUN_A = PASS
TASK_11_RUN_B = PASS
M4_STARTED = NO
```

Runtime-budget status remains truthful:

```text
MAX_SINGLE_TEST_RUNTIME_SECONDS = 600
MAX_SINGLE_GATE_SUBPROCESS_RUNTIME_SECONDS = 600
PER_TEST_TIMEOUT_ENFORCEMENT = BLOCKED
LOCAL_COMMAND_TIMEOUT_ENFORCEMENT = EXTERNAL_EXECUTION_ENVIRONMENT
HOSTED_PER_STEP_600S_ENFORCEMENT = NOT_IMPLEMENTED
TIMEOUT_DIAGNOSTIC_TESTED = NO
```

The final report intentionally does not contain the final report-only commit SHA, so the report does not hash itself.
