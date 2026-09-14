# M3 Corpus Pattern Review Packet

Date: 2026-09-13

This packet records proposal evidence for the first possible corpus-scale exact-pattern rule. It is not the maintainer decision record and does not establish corpus authority.

## Proposed record

```text
proposal_record_id  = m3.corpus.pattern-proposal.draw-two-cards.v1
proposal_record_sha = f963d6ae37a6895458da2ed40b606d3d5f52f2f9daea97d6033c417fbbf478cb
pattern_id          = m3.corpus.exact-clause.draw-two-cards
pattern_version     = 1
producer_id         = m3.registry-exact-pattern
producer_version    = 1
m2_contract_version = census.semantic-requirement.v1
rule_digest         = d4ef898620fb9d2e794390a545d08b9c9cb90a238af83fc7fd6e76900d0023a9
registry_digest     = 1f7f2189aaa9e2fa12b9e76f9da57ff7c57a4cd53a553b3de60287a31cd8cbaa
current_eligibility = NOT_ELIGIBLE
```

The canonical proposal record is stored at `config/analysis/m3-corpus-pattern-proposal.v1.json`. Its SHA-256 is the review binding recorded by the effective proposal registry at `config/analysis/m3-corpus-pattern-registry.v1.json`.

## Proposed semantic claim

The proposal uses `EXACT_FRAGMENT("Draw two cards.")` in parent `oracle_text`, with no normalization, and the complete typed `draw_cards` output:

```text
drawer.role         = source
drawer.multiplicity = one
drawer.ordinal      = null
quantity.mode       = exact
quantity.value      = 2
```

This packet does not claim that the fragment is semantically safe for global reuse. The same exact fragment can occur inside a larger conditional, triggered, modal, replacement, cost-dependent, or otherwise context-sensitive Oracle text. A substring match alone does not establish that the draw is unconditional, immediate, independently applicable, or free of additional semantic constraints.

The proposal's false-negative scope is also explicit: alternate wording, face text, punctuation variants, and context-dependent formulations are outside the proposed match. A non-match is not evidence that no equivalent requirement exists.

## Authority status

```text
MAINTAINER_DECISION = PENDING
ELIGIBILITY         = NOT_ELIGIBLE
CORPUS_AUTHORITY    = NOT_ESTABLISHED
```

The proposal registry is intentionally not a corpus-authoritative registry. The proposal record precedes its SHA-256 binding, which precedes the registry digest; this packet records those downstream digests and therefore does not participate in the digest chain. UNBLOCK_04 must supply an explicit maintainer decision before any eligibility change or corpus campaign.
