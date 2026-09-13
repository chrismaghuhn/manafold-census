# M3 Corpus Exact-Field Pattern Review Packet

Date: 2026-09-14

## Replacement proposal

```text
NEW_PROPOSAL_RECORD_ID = m3.corpus.pattern-proposal.draw-two-cards-exact-field.v1
NEW_PROPOSAL_SHA256    = 04d659d2e21e3b2333efc4d5bd974f46119fe128e20ec5cebcb3aa894b00897f
NEW_PATTERN_ID         = m3.corpus.exact-field.draw-two-cards
NEW_PATTERN_RULE_DIGEST = b97740ed2d63e8b23e1a2e6fec5ed340d9b223078ca6d728e9feb279e2a7a32c
POST_PROPOSAL_REGISTRY_DIGEST = 8cf822b4b8459f5335d3fe393209765040ee8506aac0a2e229a5842d1eab50d9

MATCHER      = EXACT_FIELD_TEXT
ELIGIBILITY  = NOT_ELIGIBLE
MAINTAINER_DECISION = PENDING
CORPUS_AUTHORITY    = NOT_ESTABLISHED
```

The proposed claim is narrower than the rejected `EXACT_FRAGMENT("Draw two cards.")` rule: the complete parent `oracle_text` must equal exactly `Draw two cards.`. No prefix, suffix, additional sentence, condition, mode, trigger clause, replacement text, or cost-dependent text is permitted.

The rejected fragment rule remains in the effective registry with its original rule bytes, rule digest, `NOT_ELIGIBLE` state, and rejected Decision-Record binding. The new proposal is also `NOT_ELIGIBLE`; this packet records evidence only and does not approve reuse.

## Remaining limitations

The exact-field proposal does not match face-specific occurrences, alternate capitalization or punctuation, alternate wording, or semantically equivalent text. A non-match proves nothing about absence of a draw requirement. Any future approval would authorize candidate reuse only and would not certify a card's semantics.

```text
REPLACEMENT_PATTERN_APPROVED  = NO
REPLACEMENT_PATTERN_ELIGIBLE  = NO
CORPUS_AUTHORITY_ESTABLISHED  = NO
TASK_11_RETRY_ALLOWED         = NO
```
