# Acceptance Criteria

Every feature is accepted only when:

- the user-visible scenario is described;
- authorization and invalid input behavior are defined;
- database changes have a migration;
- API schemas are documented;
- backend tests cover the happy path and a permission failure;
- frontend build succeeds;
- the feature does not block the core path when optional providers are unavailable.
