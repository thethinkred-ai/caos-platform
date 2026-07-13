# ADR-0001: Modular monolith and PostgreSQL source of truth

## Status

Accepted

## Decision

CAOS MVP uses a FastAPI modular monolith with PostgreSQL as the authoritative store. Redis is reserved for rate limiting and background work. A graph database may be evaluated as a disposable read-model spike, but it is not required for correctness.

## Rationale

This keeps transactions, deployment and debugging simple while preserving module boundaries. It avoids an early operational dependency on a graph database before graph-specific measurements justify it.
