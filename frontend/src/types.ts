export type User = { id: number; email: string; display_name: string; bio: string };
export type Problem = { id: number; title: string; description: string; status: string; author_id: number };
export type Goal = { id: number; title: string; description: string; status: string; problem_id: number | null; parent_goal_id: number | null; owner_id: number };
export type Project = { id: number; title: string; description: string; status: string; goal_id: number | null; owner_id: number; knowledge_count: number };

export type Team = { id: number; name: string; description: string; owner_id: number };
export type Decision = { id: number; title: string; proposal: string; status: string; goal_id: number | null; author_id: number; decision_method: string; quorum: number; valid_until: string | null; review_at: string | null };
export type DecisionEvent = { id: number; decision_id: number; author_id: number; event_type: string; content: string; created_at: string };
export type KnowledgeItem = { id: number; title: string; content: string; project_id: number | null; author_id: number; project_name: string | null; created_at: string };
export type NextAction = { label: string; section: string; reason: string };
export type Notification = { id: number; user_id: number; entity_type: string; entity_id: number; message: string; is_read: boolean; created_at: string };
export type AuditEvent = { id: number; actor_id: number; entity_type: string; entity_id: number; action: string; detail: string; created_at: string };
export type Competence = { id: number; user_id: number; name: string; level: number; description: string; created_at: string };
export type Task = { id: number; title: string; description: string; status: string; project_id: number; assignee_id: number | null; assignee_name: string | null; commitment_id: number | null; created_at: string };
export type SearchResults = { problems: Problem[]; goals: Goal[]; projects: Project[]; knowledge: KnowledgeItem[]; decisions: Decision[] };

// --- v0.2 domain types ---

export const GOAL_RELATION_TYPES = ["concretizes", "depends_on", "supports", "conflicts_with", "contributes_to", "blocks", "supersedes"] as const;
export const GOAL_PARTICIPATION_ROLES = ["contributor", "coordinator", "expert", "facilitator", "observer"] as const;
export const CRITERION_TYPES = ["binary", "quantitative", "qualitative", "composite"] as const;
export const EVIDENCE_TYPES = ["document", "data", "measurement", "observation", "linked_record", "external_source", "system_metric", "collective_assessment"] as const;

export type GoalRelation = { id: number; source_goal_id: number; target_goal_id: number; relation_type: string; rationale: string; author_id: number; created_at: string };
export type GoalImpact = { goal_id: number; direct_dependents: number; transitive_dependents: number; supporters: number; conflicts: number; sub_goals: number; projects: number; decisions: number };
export type GoalParticipation = { id: number; goal_id: number; user_id: number; display_name: string; role: string; status: string; joined_at: string; left_at: string | null };
export type Commitment = { id: number; goal_id: number; user_id: number; display_name: string; description: string; expected_result: string; deadline: string | null; source: string; status: string; created_at: string };
export type GoalCriterion = { id: number; goal_id: number; name: string; description: string; criterion_type: string; baseline: string; target_value: string; unit: string; weight: number; created_at: string };
export type GoalMeasurement = { id: number; criterion_id: number; value: string; source: string; measured_at: string; recorded_by: number };
export type ResultItem = { id: number; goal_id: number; task_id: number | null; description: string; expected_state: string; actual_state: string; status: string; reported_by: number; created_at: string; verified_at: string | null; evidence_count: number };
export type Evidence = { id: number; result_id: number; evidence_type: string; content: string; source: string; created_by: number; created_at: string };
export type Challenge = { id: number; target_type: string; target_id: number; author_id: number; claim: string; argument: string; evidence: string; alternative: string; status: string; resolution: string; created_at: string; resolved_at: string | null };

export type Section = "overview" | "activity" | "problems" | "goals" | "projects" | "teams" | "decisions" | "knowledge" | "profile" | "notifications" | "audit" | "competences";

export type ExplainNode = { kind: string; id: number; title: string; status: string; detail: string };
export type GoalExplain = { goal_id: number; chain: ExplainNode[]; counts: Record<string, number> };

export type VoteOut = { id: number; decision_id: number; user_id: number; variant: string; comment: string; created_at: string };
export type VoteSummary = { accept: number; reject: number; total: number; quorum: number; quorum_met: boolean; own_vote: VoteOut | null; votes: VoteOut[] | null };
export type ProposalVersion = { id: number; decision_id: number; version: number; content: string; author_id: number; created_at: string };
