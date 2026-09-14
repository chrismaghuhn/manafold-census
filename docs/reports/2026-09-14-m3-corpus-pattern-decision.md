# M3 Corpus Pattern Decision

Date: 2026-09-14

## Decision

```text
PROPOSAL_ID       = m3.corpus.pattern-proposal.draw-two-cards.v1
PROPOSAL_SHA256   = f963d6ae37a6895458da2ed40b606d3d5f52f2f9daea97d6033c417fbbf478cb
DECISION_RECORD   = m3.corpus.pattern-decision.draw-two-cards.v1
DECISION_SHA256   = 89b73bb76d2a54bd847a322519a12a43b0e9736361f307771598b2225e67fd07
PATTERN_RULE_DIGEST = d4ef898620fb9d2e794390a545d08b9c9cb90a238af83fc7fd6e76900d0023a9
POST_DECISION_REGISTRY_DIGEST = 097973ee6ae59b06d868eaac8e1947dc66e519fca78432b3f79a650e2d4e21c1

DECISION   = REJECT_FOR_REUSE
ELIGIBILITY = NOT_ELIGIBLE

CORPUS_AUTHORITY_ESTABLISHED = NO
TASK_11_RETRY_ALLOWED        = NO
```

The proposal validity is separate from reuse approval:

```text
proposal validity = PASS
reuse approval     = REJECTED
```

## Reason

The proposed `EXACT_FRAGMENT("Draw two cards.")` rule is not context-safe by construction. The same substring may occur inside conditional, triggered, modal, replacement, cost-dependent, or other context-sensitive Oracle text. The isolated `draw_cards` output template is therefore not sufficient semantic authority for corpus reuse.

The negative decision record binds the exact proposal record by ID and SHA-256. The effective registry binds the decision record by ID and SHA-256, while the decision record intentionally does not contain the resulting registry digest. The rule definition and its rule digest remain unchanged; only the review binding changed.

No `REVIEWED_FOR_REUSE` promotion is authorized. The generic registry-driven producer remains available as frozen machinery, but this corpus pattern is not eligible and must produce no candidates or findings.
