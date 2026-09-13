from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)
    consent_accepted: bool = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    display_name: str
    bio: str
    created_at: datetime
    is_verified: bool = True
    profile_visibility: str = "private"
    ai_consent: bool = False


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshOut(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=12, max_length=128)


class ProblemCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    current_state: str = Field(default="", max_length=2000)
    scope: str = Field(default="", max_length=2000)


class ProblemOut(ProblemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    author_id: int
    created_at: datetime


class ProblemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    current_state: str | None = Field(default=None, max_length=2000)
    scope: str | None = Field(default=None, max_length=2000)


class ProblemVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    problem_id: int
    version: int
    title: str
    description: str
    current_state: str
    scope: str
    author_id: int
    created_at: datetime


class ProblemQualify(BaseModel):
    status: str = Field(pattern="^(qualified|rejected|deferred)$")


class GoalCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    problem_id: int | None = None
    parent_goal_id: int | None = None
    priority: str = Field(default="medium", max_length=20)
    success_criteria: str = Field(default="", max_length=2000)
    required_resources: str = Field(default="", max_length=2000)
    expected_outcome: str = Field(default="", max_length=2000)


class GoalOut(GoalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    owner_id: int
    created_at: datetime
    sub_goals: list["GoalOut"] = []


GoalOut.model_rebuild()


GOAL_RELATION_TYPES = (
    "concretizes", "depends_on", "supports",
    "conflicts_with", "contributes_to", "blocks", "supersedes",
)
_RELATION_PATTERN = "^(" + "|".join(GOAL_RELATION_TYPES) + ")$"


class GoalRelationCreate(BaseModel):
    target_goal_id: int
    relation_type: str = Field(pattern=_RELATION_PATTERN)
    rationale: str = Field(min_length=3, max_length=2000)


class GoalRelationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source_goal_id: int
    target_goal_id: int
    relation_type: str
    rationale: str
    author_id: int
    created_at: datetime


class GoalImpact(BaseModel):
    """What stops or is affected if this goal fails — the operational
    value of the graph (critique, section 33/51)."""
    goal_id: int
    direct_dependents: int
    transitive_dependents: int
    supporters: int
    conflicts: int
    sub_goals: int
    projects: int
    decisions: int


class GoalTransition(BaseModel):
    action: str = Field(min_length=3, max_length=30, pattern="^[a-z-]+$")


class DecisionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    proposal: str = Field(min_length=1, max_length=5000)
    goal_id: int | None = None
    alternatives: str = Field(default="", max_length=3000)
    rationale: str = Field(default="", max_length=3000)
    decision_method: str = Field(
        default="majority",
        pattern="^(majority|supermajority|unanimity|consent)$",
    )
    quorum: int = Field(default=1, ge=1)
    deadline: datetime | None = None
    valid_until: datetime | None = None
    review_at: datetime | None = None


class ProposalVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    decision_id: int
    version: int
    content: str
    author_id: int
    created_at: datetime


class DecisionEventCreate(BaseModel):
    event_type: str = Field(
        min_length=3,
        max_length=30,
        pattern="^(proposal|argument|objection|question|alternative|revision|revised|clarification|evidence|comment|accepted|rejected)$",
    )
    content: str = Field(min_length=1, max_length=5000)


class DecisionEventOut(DecisionEventCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    decision_id: int
    author_id: int
    created_at: datetime


class DecisionOut(DecisionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    author_id: int
    outcome: str = ""
    created_at: datetime


class ProjectCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    goal_id: int | None = None


class ProjectOut(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    owner_id: int
    created_at: datetime
    knowledge_count: int = 0


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    assignee_id: int | None = None
    commitment_id: int | None = None
    competence_requirements: list[str] | None = None


class TaskOut(TaskCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    status: str
    assignee_name: str | None = None
    created_at: datetime


class TaskAssign(BaseModel):
    assignee_id: int | None = None


class TeamCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(default="", max_length=5000)


class TeamOut(TeamCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_id: int
    created_at: datetime


class MemberCreate(BaseModel):
    user_id: int
    role: str = Field(default="member", min_length=2, max_length=30)


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    role: str
    created_at: datetime


class ProjectMemberOut(MemberOut):
    project_id: int


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    content: str = Field(min_length=1, max_length=10000)
    project_id: int | None = None


class KnowledgeOut(KnowledgeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_id: int
    created_at: datetime
    project_name: str | None = None


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int
    entity_type: str
    entity_id: int
    action: str
    detail: str
    created_at: datetime


class GoalParticipationCreate(BaseModel):
    user_id: int | None = None
    role: str = Field(default="contributor", pattern="^(contributor|coordinator|expert|facilitator|observer)$")


class GoalParticipationRoleUpdate(BaseModel):
    role: str = Field(pattern="^(contributor|coordinator|expert|facilitator|observer)$")


class CommitmentCreate(BaseModel):
    description: str = Field(min_length=3, max_length=2000)
    expected_result: str = Field(default="", max_length=2000)
    deadline: datetime | None = None


class CommitmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(in_progress|fulfilled|failed|withdrawn)$")


CRITERION_TYPES = ("binary", "quantitative", "qualitative", "composite")


class GoalCriterionCreate(BaseModel):
    name: str = Field(min_length=3, max_length=200)
    description: str = Field(default="", max_length=2000)
    criterion_type: str = Field(default="quantitative", pattern="^(binary|quantitative|qualitative|composite)$")
    baseline: str = Field(default="", max_length=200)
    target_value: str = Field(default="", max_length=200)
    unit: str = Field(default="", max_length=50)
    weight: int = Field(default=1, ge=1, le=10)


class GoalCriterionOut(GoalCriterionCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    created_at: datetime


class GoalMeasurementCreate(BaseModel):
    value: str = Field(min_length=1, max_length=200)
    source: str = Field(default="", max_length=200)


class GoalMeasurementOut(GoalMeasurementCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    criterion_id: int
    measured_at: datetime
    recorded_by: int


class ResultCreate(BaseModel):
    description: str = Field(min_length=3, max_length=5000)
    expected_state: str = Field(default="", max_length=2000)
    actual_state: str = Field(default="", max_length=2000)
    task_id: int | None = None


class ResultOut(ResultCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    status: str
    reported_by: int
    created_at: datetime
    verified_at: datetime | None = None
    evidence_count: int = 0


class EvidenceCreate(BaseModel):
    evidence_type: str = Field(
        default="document",
        pattern="^(document|data|measurement|observation|linked_record|external_source|system_metric|collective_assessment)$",
    )
    content: str = Field(min_length=1, max_length=5000)
    source: str = Field(default="", max_length=500)


class EvidenceOut(EvidenceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    result_id: int
    created_by: int
    created_at: datetime


class ResultVerify(BaseModel):
    status: str = Field(pattern="^(verified|partially_verified|rejected)$")
    rationale: str = Field(min_length=3, max_length=2000)


class ChallengeCreate(BaseModel):
    target_type: str = Field(pattern="^(goal|decision|result)$")
    target_id: int
    claim: str = Field(min_length=3, max_length=2000)
    argument: str = Field(min_length=3, max_length=5000)
    evidence: str = Field(default="", max_length=5000)
    alternative: str = Field(default="", max_length=5000)


class ChallengeOut(ChallengeCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    author_id: int
    status: str
    resolution: str
    created_at: datetime
    resolved_at: datetime | None = None


class ChallengeResolve(BaseModel):
    status: str = Field(pattern="^(acknowledged|addressed|accepted|rejected|deferred|withdrawn)$")
    resolution: str = Field(min_length=3, max_length=5000)


class ProjectGoalCreate(BaseModel):
    goal_id: int
    relation_type: str = Field(default="serves", pattern="^(serves|supports|contributes_to)$")


class ProjectGoalOut(ProjectGoalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    created_by: int
    created_at: datetime


class KnowledgeRelationCreate(BaseModel):
    target_type: str = Field(pattern="^(problem|goal|decision|result)$")
    target_id: int
    relation_type: str = Field(default="supports", pattern="^(supports|explains|evidences|relates|contradicts)$")


class KnowledgeRelationOut(KnowledgeRelationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    knowledge_id: int
    created_by: int
    created_at: datetime


class SearchResults(BaseModel):
    problems: list[ProblemOut] = []
    goals: list[GoalOut] = []
    projects: list[ProjectOut] = []
    knowledge: list[KnowledgeOut] = []
    decisions: list[DecisionOut] = []


class NextActionOut(BaseModel):
    label: str
    section: str
    reason: str


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)
    bio: str = Field(default="", max_length=2000)


class AIRecommendation(BaseModel):
    suggestion: str
    source: str = ""
    confidence: float = 0.0
    status: str = "proposal"


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    entity_type: str
    entity_id: int
    message: str
    is_read: bool
    created_at: datetime


class ProjectStatusUpdate(BaseModel):
    status: str = Field(min_length=3, max_length=30)


class CompetenceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    level: int = Field(default=1, ge=1, le=5)
    description: str = Field(default="", max_length=2000)
    is_visible: bool = False


class CompetenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    name: str
    level: int
    description: str
    is_visible: bool = False
    created_at: datetime


class VoteCreate(BaseModel):
    variant: str = Field(min_length=2, max_length=30)
    comment: str = Field(default="", max_length=2000)


class VoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    decision_id: int
    user_id: int
    variant: str
    comment: str
    created_at: datetime


class VoteSummary(BaseModel):
    """Aggregated vote counts; the full identifiable list is only
    exposed after the decision is finalized."""
    accept: int
    reject: int
    total: int
    quorum: int
    quorum_met: bool
    own_vote: VoteOut | None = None
    votes: list[VoteOut] | None = None


class AISuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    id: int
    user_id: int
    endpoint: str
    suggestion: str
    status: str
    reason: str
    model_name: str = ""
    input_snapshot: str = ""
    confidence: float | None = None
    proposal_type: str = "recommendation"
    target_type: str = ""
    target_id: int | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class AISuggestionResolve(BaseModel):
    status: str = Field(min_length=3, max_length=20)
    reason: str = Field(default="", max_length=2000)


class ExplainNode(BaseModel):
    """One step of the justification chain (Track F: explain-this)."""
    kind: str  # problem / goal / decision / commitment / task / result
    id: int
    title: str
    status: str
    detail: str = ""


class GoalExplain(BaseModel):
    """Why does this goal exist: the full trace from the problem through
    decisions, commitments, tasks and results (critique, sections 77/89)."""
    goal_id: int
    chain: list[ExplainNode]
    counts: dict[str, int]


class DelegationCreate(BaseModel):
    recipient_id: int
    capability: str = Field(pattern="^(coordinate|transition|verify_result)$")
    reason: str = Field(min_length=3, max_length=2000)
    valid_until: datetime


class DelegationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    goal_id: int
    issuer_id: int
    recipient_id: int
    capability: str
    reason: str
    valid_from: datetime
    valid_until: datetime
    revoked_at: datetime | None = None
    revoked_by: int | None = None
    created_at: datetime
