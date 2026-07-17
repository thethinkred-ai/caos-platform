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


class ProblemOut(ProblemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    author_id: int
    created_at: datetime


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


class DecisionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    proposal: str = Field(min_length=1, max_length=5000)
    goal_id: int | None = None
    alternatives: str = Field(default="", max_length=3000)
    rationale: str = Field(default="", max_length=3000)
    decision_method: str = Field(default="consensus", max_length=50)
    quorum: int = Field(default=1, ge=1)
    deadline: datetime | None = None


class DecisionEventCreate(BaseModel):
    event_type: str = Field(min_length=3, max_length=30)
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


class AISuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    endpoint: str
    suggestion: str
    status: str
    reason: str
    created_at: datetime


class AISuggestionResolve(BaseModel):
    status: str = Field(min_length=3, max_length=20)
    reason: str = Field(default="", max_length=2000)
