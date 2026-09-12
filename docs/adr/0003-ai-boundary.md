# ADR-0003: AI proposes, humans decide

## Status

Accepted (Track G of `docs/plan-caos-0.2.md`; invariant INV-5)

## Decision

AI never mutates domain state (goals, decisions, commitments, results) directly. Its only write-path is creating an `AIProposal` (model, input snapshot, proposed change, rationale, confidence) in status `under_review`. A human accepts, rejects or modifies the proposal; only then does the domain change, attributed to the reviewing user. AI context is built through a privacy filter that passes the minimum data classes required for the task — never emails, bios, OAuth identities or other users' private content. External AI providers receive nothing by default; retrieval is permission-scoped.

## Rationale

"The graph of goals replaces the hierarchy of people" collapses if an AI becomes an unaccountable decision-maker: proposals would silently reshape collective goals with no author to challenge. The proposal-review path preserves accountability (every change has a human author), enables measurement (accepted/rejected rates per model and prompt), and keeps the door open for local-first models by isolating providers behind one interface. The privacy firewall exists because the goal graph plus participation data reveals more about a person than a plain profile — shipping it to an LLM provider is a data decision, not a technical accident.
