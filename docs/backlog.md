# CAOS Backlog

## Completed (this slice)

- Decision/DecisionEvent models, schemas, API routes, migration, tests.
- Goal Alignment UI: create proposals, list decisions, event history.
- Decision event UI: accept/reject/revise/comment buttons + event timeline.
- KnowledgeItem model + API + UI (create/list knowledge entries).
- AuditEvent model (immutable change tracking, used by knowledge creation).
- Search endpoint (ILIKE across problems, goals, projects) + UI search panel.
- Next-action dashboard endpoint ("Чем помочь сегодня") + overview UI.
- AI recommendation stubs (4 operations: similar problems, people, knowledge, goal decomposition).
- Profile update endpoint (PATCH /auth/me) + profile editing UI.
- Notification model + API (list, mark-read, mark-all-read) + UI section.
- Goal decomposition: parent_goal_id + sub-goals API + parent selector in UI.
- Project status transitions: PATCH /projects/{id}/status (planned→active→completed→on_hold) + status buttons in UI.
- CI workflow (GitHub Actions: backend pytest + frontend vite build).
- Foundation documentation: Vision, PRD, Ontology, Roadmap, CodingStandards, ModulePassport, AcceptanceCriteria, ADR-0001.
- Wire AI adapter to real LLM provider: OpenAI-compatible adapter (llm.py), env-based config (AI_API_KEY, AI_BASE_URL, AI_MODEL), stub fallback when no key, GET /ai/status endpoint, AI status panel in overview UI.
- Task creation UI: form inside expanded project to add tasks with title + description.
- Extended search: knowledge items and decisions now included in search results (backend + frontend).
- Task completion UI: "✓ Завершить" button on each task in expanded project view.
- Knowledge-project linking: project selector in knowledge creation form, project_id shown on knowledge items.

## Next backlog

- PostgreSQL full-text search (replace ILIKE with tsvector + GIN index).
- Project results and Practice versions (link knowledge to completed projects).
- Notification generation on decision events and project status changes.
- Audit event listing endpoint + audit viewer UI section ("Журнал").
- Audit events on task completion, decision events, project status changes.
- CSS styles for decision events, status buttons, read/selected states, audit entries.
- Task assignment: PATCH /tasks/{id}/assign, assignee_name in TaskOut, UI with take/unassign buttons.
- Project results: knowledge_count on ProjectOut, task expansion on project cards with assignee display.
- Competence management: model, schema, API (create/list/delete), UI section with level selector.
- Knowledge filtering by project_id: GET /knowledge?project_id=N returns only linked items.
- Competence and resource management.
- Decision event UI: show event timeline inline (currently in a separate panel).
- Evaluate Neo4j/Memgraph read-model spike.
- Defer mobile, federation, rankings, forecasting and autonomous agents until after pilot evidence.
