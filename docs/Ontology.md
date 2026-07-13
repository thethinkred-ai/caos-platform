# CAOS Ontology

## Entities

- `User`: account, identity and participation history.
- `Problem`: situation or contradiction requiring change.
- `Goal`: measurable desired change linked to a problem.
- `Decision`: proposal, arguments, objections, revisions and accepted outcome.
- `Team`: group of participants around a goal or project.
- `Project`: time-bounded activity for a goal.
- `Task`: verifiable project result.
- `Action`: atomic step inside a task.
- `Resource`: time, money, place, equipment, material or contact.
- `Competence`: ability relevant to an action or task.
- `Knowledge`: result, document, explanation or conclusion.
- `Practice`: versioned reproducible method with steps and success criteria.
- `Event`: immutable fact used for audit and history.

## Core relations

```text
Problem -> Goal -> Decision -> Project -> Task -> Action -> Result
User -> TeamMember -> Team -> ProjectMember -> Project
Project -> ProjectResult -> Knowledge -> Practice
Goal -> GoalRelation -> Goal
Task -> TaskDependency -> Task
```

## Invariants

- Only authorized users can mutate an object.
- A task belongs to exactly one project.
- A project may have many members, but its owner controls membership.
- Decision history is append-only from the API perspective.
- Goal and task hierarchies must reject cycles.
- LLM suggestions are not persisted as accepted decisions without confirmation.
