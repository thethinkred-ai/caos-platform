# ADR-0004: Participation in goals replaces membership in containers

## Status

Accepted (Track C3–C4 of `docs/plan-caos-0.2.md`)

## Decision

A person's primary relation to collective activity is `GoalParticipation` (user ↔ goal, contextual role: contributor, coordinator, expert, facilitator, observer) plus `Commitment` (a voluntarily accepted obligation of concrete work towards the goal). `ProjectMember` is frozen and `Team`/`TeamMember` are deprecated as organizational forms: projects become tools that serve goals (linked many-to-many via `ProjectGoal`), not containers of people. Tasks attach to goals through commitments, which enforces invariant INV-2 (no orphan activity).

## Rationale

The concept says "you don't join an organization — you join the achievement of a specific goal", yet the current model stores exactly organizational membership (owner → members in teams and projects), which reproduces the hierarchy CAOS replaces. Contextual roles acknowledge that one person is a researcher in one goal and a reviewer in another — a global `role` column cannot express this. Commitments matter because assignment ("Ivan, do X") rebuilds hierarchy from the back door, while an accepted obligation with a source (self / decision / delegation) keeps responsibility voluntary and traceable. Existing project memberships are migrated to participations via `projects.goal_id`; the old tables stay frozen rather than dropped to preserve history (INV-8).
