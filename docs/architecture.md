# CAOS MVP architecture

## Production topology

- `caos.thinkred.ru` points to the static frontend hosting on TimeWeb.
- `api-caos.thinkred.ru` points to the VPS and terminates TLS at Nginx.
- Nginx proxies `/api` to the FastAPI container and never exposes PostgreSQL or Redis publicly.
- PostgreSQL is the source of truth. Redis is reserved for rate limiting and background work.

## MVP boundary

The first release implements identity, problems, goals, decisions, teams, projects, tasks, project results and an audit trail. Goal Alignment records proposal history and explicit confirmation. Search and four bounded AI recommendations are optional extensions; core workflows must work when an LLM provider is unavailable.

PostgreSQL is the source of truth. Neo4j or Memgraph may be evaluated as a disposable read-model spike for graph search, but correctness and writes remain in PostgreSQL.

## Foundation artifacts

The implementation is governed by `Vision.md`, `PRD.md`, `Ontology.md`, `Roadmap.md`, `CodingStandards.md`, `AcceptanceCriteria.md` and ADRs. Every module has a passport and every database change is an ordered migration.

## Deployment

1. Build the frontend with `npm run build` using `VITE_API_URL=https://api-caos.thinkred.ru/api/v1`.
2. Upload `frontend/dist` to the `caos.thinkred.ru` document root on TimeWeb.
3. Deploy the repository to the VPS, apply ordered migrations, and run `docker compose up -d --build backend db redis`.
4. Configure Nginx and certificates for `api-caos.thinkred.ru`.
5. Run the smoke checks in `docs/deployment.md`.
