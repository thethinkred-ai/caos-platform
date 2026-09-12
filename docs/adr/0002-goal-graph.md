# ADR-0002: Typed goal graph (GoalRelation) instead of a parent pointer

## Status

Accepted (Track C1 of `docs/plan-caos-0.2.md`)

## Decision

The goal graph is stored in a dedicated `goal_relations` table with typed edges: `concretizes, depends_on, supports, conflicts_with, contributes_to, blocks, supersedes` — each with an author and a rationale. The existing `goals.parent_goal_id` remains only as sugar over a `concretizes` edge and is not the foundation of the model. Edge creation validates against forbidden cycles.

## Rationale

The README promises "a graph of goals instead of a department hierarchy", but `parent_goal_id` makes the model a tree: a goal needed by two other goals cannot be expressed. Real collective action includes support, dependency and conflict — a tree cannot hold any of them. A relation table on PostgreSQL (with recursive CTEs for traversal) delivers the graph without introducing Neo4j, keeping ADR-0001 intact. Edge types are deliberately limited to seven; new types require their own ADR. Philosophical vocabulary ("dialectical", "sublation") stays in documentation — API and tables use engineering names only.
