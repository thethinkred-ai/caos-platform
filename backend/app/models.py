from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120))
    bio: Mapped[str] = mapped_column(Text, default="")
    stepik_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    consent_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ai_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_visibility: Mapped[str] = mapped_column(String(20), default="private")
    role: Mapped[str] = mapped_column(String(20), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    problems: Mapped[list["Problem"]] = relationship(back_populates="author")
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    teams: Mapped[list["TeamMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    project_memberships: Mapped[list["ProjectMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="author")
    auth_identities: Mapped[list["AuthIdentity"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthIdentity(Base):
    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_auth_identity"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_subject: Mapped[str] = mapped_column(String(255))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    verified_email: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="auth_identities")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    author: Mapped[User] = relationship(back_populates="problems")
    goals: Mapped[list["Goal"]] = relationship(back_populates="problem")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
    problem_id: Mapped[int | None] = mapped_column(ForeignKey("problems.id"), nullable=True)
    parent_goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    success_criteria: Mapped[str] = mapped_column(Text, default="")
    required_resources: Mapped[str] = mapped_column(Text, default="")
    expected_outcome: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    problem: Mapped[Problem | None] = relationship(back_populates="goals")
    parent: Mapped["Goal | None"] = relationship(remote_side="Goal.id", back_populates="sub_goals")
    sub_goals: Mapped[list["Goal"]] = relationship(back_populates="parent", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="goal")


class GoalRelation(Base):
    """Typed edge of the goal graph (ADR-0002).

    parent_goal_id on Goal remains sugar over a `concretizes` edge; the
    graph itself lives here.
    """

    __tablename__ = "goal_relations"
    __table_args__ = (UniqueConstraint("source_goal_id", "target_goal_id", "relation_type", name="uq_goal_relation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    target_goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(30))
    rationale: Mapped[str] = mapped_column(Text, default="")
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


GOAL_PARTICIPATION_ROLES = ("contributor", "coordinator", "expert", "facilitator", "observer")


class GoalParticipation(Base):
    """A person's contextual relation to a specific goal (ADR-0004).

    Roles are contextual: the same user can be an expert in one goal and
    an observer in another. Replaces project/team membership as the
    primary form of association with activity.
    """

    __tablename__ = "goal_participations"
    __table_args__ = (UniqueConstraint("goal_id", "user_id", name="uq_goal_participation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(30), default="contributor")
    status: Mapped[str] = mapped_column(String(20), default="active")
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    left_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Commitment(Base):
    """A voluntarily accepted obligation of concrete work towards a goal.

    Not an assignment: `source` records the basis (own initiative, a
    collective decision, or delegation).
    """

    __tablename__ = "commitments"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    description: Mapped[str] = mapped_column(Text)
    expected_result: Mapped[str] = mapped_column(Text, default="")
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="self")
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GoalCriterion(Base):
    """A checkable success criterion of a goal (Track C5): type,
    baseline and target make achievement measurable instead of a free
    text field."""

    __tablename__ = "goal_criteria"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    criterion_type: Mapped[str] = mapped_column(String(20), default="quantitative")
    baseline: Mapped[str] = mapped_column(Text, default="")
    target_value: Mapped[str] = mapped_column(Text, default="")
    unit: Mapped[str] = mapped_column(String(50), default="")
    weight: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GoalMeasurement(Base):
    """A measured value of a criterion over time: baseline -> ... -> actual."""

    __tablename__ = "goal_measurements"

    id: Mapped[int] = mapped_column(primary_key=True)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("goal_criteria.id"), index=True)
    value: Mapped[str] = mapped_column(Text)
    measured_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    source: Mapped[str] = mapped_column(String(200), default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))


class Result(Base):
    """A change in the state of affairs produced by activity — not the
    fact that a task was completed (INV-3)."""

    __tablename__ = "results"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    expected_state: Mapped[str] = mapped_column(Text, default="")
    actual_state: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(30), default="reported", index=True
    )  # reported / under_verification / verified / partially_verified / rejected / disputed
    reported_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Evidence(Base):
    """Objective support for a result: document, measurement, metric..."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(30), default="document")
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Verification(Base):
    """A result verification by a participant other than the reporter
    (INV-4): reported != verified."""

    __tablename__ = "verifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("results.id"), index=True)
    verifier_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30))  # verified / partially_verified / rejected
    rationale: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Challenge(Base):
    """A structured objection to a significant object — goal, decision or
    result (Track C6). An objection is an object: it cannot be lost, and
    rejecting it requires a recorded answer."""

    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(primary_key=True)
    target_type: Mapped[str] = mapped_column(String(20), index=True)  # goal / decision / result
    target_id: Mapped[int] = mapped_column(index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    claim: Mapped[str] = mapped_column(Text)
    argument: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text, default="")
    alternative: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(
        String(20), default="open", index=True
    )  # open / acknowledged / addressed / accepted / rejected / withdrawn / deferred
    resolution: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProposalVersion(Base):
    """Immutable versions of a decision proposal: what exactly was
    discussed and accepted at each point in time."""

    __tablename__ = "proposal_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), index=True)
    version: Mapped[int] = mapped_column(default=1)
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    proposal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="proposed", index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    alternatives: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(Text, default="")
    decision_method: Mapped[str] = mapped_column(String(50), default="majority")
    quorum: Mapped[int] = mapped_column(default=1)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    goal: Mapped[Goal | None] = relationship(back_populates="decisions")
    author: Mapped[User] = relationship(back_populates="decisions")
    events: Mapped[list["DecisionEvent"]] = relationship(back_populates="decision", cascade="all, delete-orphan", order_by="DecisionEvent.created_at")
    votes: Mapped[list["Vote"]] = relationship(back_populates="decision", cascade="all, delete-orphan")


class DecisionEvent(Base):
    __tablename__ = "decision_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"))
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(30))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    decision: Mapped[Decision] = relationship(back_populates="events")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="planned", index=True)
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("goals.id"), nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    owner: Mapped[User] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    members: Mapped[list["TeamMember"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(30), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    team: Mapped[Team] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="teams")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(30), default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="project_memberships")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (UniqueConstraint("project_id", "title", name="uq_task_project_title"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="todo", index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    commitment_id: Mapped[int | None] = mapped_column(ForeignKey("commitments.id"), nullable=True, index=True)
    competence_requirements: Mapped[JSON | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="tasks")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    content: Mapped[str] = mapped_column(Text)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(30))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int] = mapped_column(index=True)
    message: Mapped[str] = mapped_column(String(500))
    is_read: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Competence(Base):
    __tablename__ = "competences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    level: Mapped[int] = mapped_column(default=1)
    description: Mapped[str] = mapped_column(Text, default="")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (UniqueConstraint("decision_id", "user_id", name="uq_vote_decision_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    variant: Mapped[str] = mapped_column(String(30))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    decision: Mapped[Decision] = relationship(back_populates="votes")


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(String(100))
    suggestion: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
