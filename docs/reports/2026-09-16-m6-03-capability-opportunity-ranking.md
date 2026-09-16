# M6-03 Capability-Opportunity Ranking Evidence

This evidence records two deterministic, offline prioritization builds.

Capability Opportunity != Capability.
Opportunity assessment != semantic review.
Ranking != authority.
Mechanical overlap != semantic equivalence.
Marginal Oracle coverage != semantic breadth.
M6-03 creates no Requirement, Capability, mapping, or M4 authority.

## Input identities

- SourceLock digest: 4767dccbb518b4009c235bb1ce531f509c0923ba0ebe190936c2dc2d14e2d4bd
- M1 manifest SHA-256: bdc74ec944798a8c1dd7627dae55a795c6fb72d3bbe067d2f2e50412c7155f2b
- M3 manifest SHA-256: f69cd3890de54278c231bb6bd8fb0125a31903c2b01d85c81ad1e5d732f9276f
- Parent M4 manifest SHA-256: 575634d352d95f5db9f5d96e7fb66ad4cc21560d49354ec90460adcf5e0019b4
- Parent Census release ID: censusrel_55ff3102f75a64a0a2e1277810e709847803d085c6623ceeec14b7fe8f969e9f
- M6-02 manifest SHA-256: 8c2d409d83f9e22be073e09f7a492a56ffa31fbc59d09f35dddd98159516f665
- M6-02 selected identity-set digest: 4a16da7aca9858c81341ecbc714bd46d60e643d33757f2e739d5ac4f69a54dc2
- M6-02 Opportunity count: 10732
- Assessment policy: m6-03.opportunity-assessment v1
- Ranking policy: m6-03.breadth-ranking v1

## Population and observed prioritization

- Input Opportunities: 10732
- Non-noise Opportunities: 10724
- Planning-noise Opportunities: 8
- Mechanical-overlap clusters: 7206
- Full ranked worklist: 10732
- Review packet (limit 25): 25
- Review-packet Oracle union coverage: 9938 / 38735
- Stopping reason: REVIEW_BUDGET_REACHED
- Marginal coverage sequence: [2725, 905, 789, 664, 398, 368, 351, 349, 316, 300, 274, 241, 227, 226, 225, 220, 207, 177, 166, 157, 141, 138, 137, 130, 107]
- Noise by class: [['ALL_EMPTY_OR_WHITESPACE', 6], ['ALL_NULL', 2], ['NONE', 10724]]

## Parity gates

- RUN_A_RUN_B_FILESET_PARITY: TRUE
- RUN_A_RUN_B_BYTE_PARITY: TRUE
- PATH_FREE_MANIFEST: TRUE
- OFFLINE_REGENERATION: TRUE

Capability Opportunity count is NOT Capability count.
No Requirement, Capability, mapping, or M4 authority is created.
