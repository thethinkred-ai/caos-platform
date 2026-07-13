# CAOS Coding Standards

- Python uses typed functions, Pydantic schemas and SQLAlchemy models.
- TypeScript uses strict types and explicit API response types.
- Every database change is an ordered migration; `create_all` is test-only bootstrap.
- Every endpoint defines authorization, validation and response schema.
- Every feature includes unit or integration coverage and acceptance criteria.
- Architectural changes require an ADR.
- API contracts are documented through FastAPI OpenAPI.
- Secrets, tokens and passwords never enter logs, frontend bundles or git.
- Comments are added only when they explain a non-obvious invariant.
