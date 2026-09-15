# Manafold Census 0.1 Release Conformance Evidence

Date: 2026-09-15

This report records the M5-12 release-conformance run for the frozen Census
0.1 vertical slice. It validates explicit frozen inputs, creates two fresh
candidate trees, rereads them through the existing M5 validators, compares
authoritative and derived bytes, and records path-free canonical JSON
evidence. Generated candidate trees remain ignored under `dist/`.

## Execution identity

```text
M5_12_IMPLEMENTATION_HEAD = d8605c7f634ce1c5694721d5c637b4f16e61ae60
M5_12_PARENT              = ca581776a6bbaa8096774ea978078e31cbeb5d55
BRANCH                    = feat/m5-census-0-1
PR_AUTHORIZED             = NO
MERGE_AUTHORIZED          = NO
```

The command was executed with all authoritative paths supplied explicitly:

```text
INPUT_LOCK       = locks/census-0.1-input-lock.v1.json
SOURCE_LOCK      = source-locks/scryfall-oracle-v1.json
STRUCTURAL_M1    = dist/structural/scryfall-oracle-v1-run-a
ANALYSIS_M3      = dist/analysis/m3-census-0-1-real-run-a
AUTHORITY_M4     = reviewed/m4/census-0.1
PUBLISHED_M4     = dist/capability/m4-census-0-1-real-run-a
OUTPUT_ROOT      = dist/release-conformance/2026-09-15-real
JSON_EVIDENCE    = docs/reports/2026-09-15-m5-census-0-1-release-conformance.json
```

No M3 or M4 builder was called. No source acquisition, network operation,
semantic coverage expansion, new M4 record, or artifact discovery was used.

## Frozen input identities

```text
SOURCE_LOCK_DIGEST              = 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
SOURCE_LOCK_FILE_SHA256         = 4916fe8c9eba177642efcdfeaa542e6a5d88bc06836cd7d8cd4e274168eaf0e7
M1_STRUCTURAL_MANIFEST_SHA256   = bdc74ec944798a8c1dd7627dae55a795c6fb72d3bbe067d2f2e50412c7155f2b
M1_STRUCTURAL_AGGREGATE_DIGEST  = eb215ca6c904c26baa2d8f0a63928e8c9acab5bb9ea9493eacebcdab2fbb86bb
M3_ANALYSIS_MANIFEST_SHA256     = f69cd3890de54278c231bb6bd8fb0125a31903c2b01d85c81ad1e5d732f9276f
M3_RECORD_IDENTITY_SET_DIGEST   = acf03f0d67c8d8cbb3067ed5ffb12b33f3f27a7329c327435ef4445d74678ba9
M3_RECORD_INDEX_DIGEST           = 0c5522d64dc6cb50984ca535d8aa5a07d936b0fe6efc8f056d6061fc29af28a6
M3_TRACE_INDEX_DIGEST            = 591d5157e1b1067fa9c6926907c2dda03b89716ce23b051eeb892b49138d5c89
M4_REQUIREMENT_SET_DIGEST        = 04b2d279cec33b44ecbaa5b4531142a8c25d879b36079f87349e3314528a10dc
M4_AUTHORITY_PACKAGE_DIGEST      = 5adc71ae9c589497e06a06ebf6123a7932648ddb78ff4c6c622d688b1ce25a0a
M4_MANIFEST_SHA256               = 575634d352d95f5db9f5d96e7fb66ad4cc21560d49354ec90460adcf5e0019b4
```

The locked population is:

```text
ORACLE_IDENTITIES          = 38740
STRUCTURAL_RECORDS         = 38740
ANALYSIS_RECORDS           = 38740
REQUIREMENTS_PRODUCED      = 5
NO_REQUIREMENTS_APPLICABLE = 0
UNRESOLVED_ANALYSIS        = 38735
PERSISTED_REQUIREMENTS     = 5
```

## Candidate reproduction

The conformance seam built `bundle-a` and `bundle-b` from the same frozen
inputs, then built `derived-a` and `derived-b` from those bundles. Every
candidate was independently reread through the frozen M5-02, M5-05, M5-06,
and Query Layer validation paths before parity checks.

| candidate | bundle files | derived files | census release id | bundle tree digest | derived tree digest | report-index SHA | index-manifest SHA |
| --- | ---: | ---: | --- | --- | --- | --- | --- |
| candidate-a | 98 | 108 | `censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f` | `72b79cc04e2ced7d4d9c59d9f44bbf8d83e78e7e0a4315cb99fbd211f8d5fbdc` | `a8b78000bc3cf82b59e919a9be6a681f51164751507fd0ba0961a86cc5fd0e5c` | `fb914e4e005eed3f01180bf933660d90727151ea1f45efa6af4ceb6f8ce3079f` | `4576c3a7fa6fecc0dc0d29a6633d6379f88c94ec89f024b5d4fb38d38db907cb` |
| candidate-b | 98 | 108 | `censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f` | `72b79cc04e2ced7d4d9c59d9f44bbf8d83e78e7e0a4315cb99fbd211f8d5fbdc` | `a8b78000bc3cf82b59e919a9be6a681f51164751507fd0ba0961a86cc5fd0e5c` | `fb914e4e005eed3f01180bf933660d90727151ea1f45efa6af4ceb6f8ce3079f` | `4576c3a7fa6fecc0dc0d29a6633d6379f88c94ec89f024b5d4fb38d38db907cb` |

```text
CENSUS_AUTHORITATIVE_BYTES_PARITY = PASS  (98 exact files)
REPORT_INDEX_BYTES_PARITY          = PASS  (10 exact reports/indexes)
RELEASE_CANDIDATE_REPRODUCTION    = PASS  (full 108-file trees)
RELEASE_CANDIDATE_AUDITABILITY    = PASS  (canonical path-free JSON evidence)
```

The JSON evidence is written only after all checks pass, contains no absolute
filesystem path, and does not hash itself.

## Previous frozen M5 gates

```text
M5-00  PASS / frozen head 786d28b3c53eef22df937221ee00bf317a58d4cb
M5-01  PASS / frozen head 2b7c6045816d38bac2f5d77fa62d8c2f8eab087f
M5-02  PASS / frozen head 8519a25635457e14ddf821cc6173fd9a14c6aefe
M5-03  PASS / frozen head 0b008f987dfaa819a3f8418d837a07c919a079eb
M5-04  PASS / frozen head 78aab6a6d0390c6b3befd695509411404be9ff74
M5-05  PASS / frozen head 74ed22c6c5e18608014a11a3c80753f7769a4f98
M5-06  PASS / frozen head 080a0e9218a9fafc1608b9eb1eab3deecdac668e
M5-07  PASS / frozen head d6bab7c0a1f800a18307cb3b94e90ab8c4907171
M5-08  PASS / frozen head 3052330508ee32d196b9826235cca5b62398b6eb
M5-09  PASS / frozen head 1eac15d9a6db5bc1c1f4077b39c1b1f3c3d71511
M5-10  PASS / frozen head a623e46d8b3a46d41503a1143d46c6f87a184dd5
M5-11  PASS / frozen head 03fcedbaab5e4896534f1aac9f9fc0aefe28e768
```

M5-11 hosted evidence includes Windows Run `35009681901` with the standalone
package smoke, external bundle, compatibility rejection, and functional
two-build parity. `WINDOWS_EXE_BYTE_PARITY_OBSERVED = PASS` remains an
experimental, non-hard gate.

```text
NO_NETWORK_REQUIREMENT                    = PASS
EXTERNAL_LOCAL_BUNDLE                     = PASS
PHYSICAL_NETWORK_ISOLATION_OF_CI_RUNNER   = NOT_RUN
WINDOWS_EXE_BYTE_PARITY_GATE              = EXPERIMENTAL (non-hard)
```

## M5-12 result

```text
ALL_REQUIRED_HARD_GATES       = PASS
AUTHORITATIVE_BYTES_PARITY    = PASS
REPORT_INDEX_BYTES_PARITY     = PASS
RELEASE_CANDIDATE_REPRODUCIBLE = PASS
RELEASE_CANDIDATE_AUDITABLE    = PASS
M5_12_IMPLEMENTATION          = PASS
M5_12_STATUS                  = NOT_FROZEN
M6_AUTHORIZED                 = NO
PR_AUTHORIZED                 = NO
MERGE_AUTHORIZED              = NO
```
