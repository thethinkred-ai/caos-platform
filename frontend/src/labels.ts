/** Central Russian vocabulary of the domain (i18n layer).
 * The API speaks English identifiers; the interface speaks Russian.
 * Context-specific words (e.g. "open" for a problem vs a challenge)
 * get their own dictionaries. */

const GOAL: Record<string, string> = {
  draft: "черновик", proposed: "предложена", under_review: "на рассмотрении",
  accepted: "принята", active: "активна", suspended: "приостановлена",
  achieved: "достигнута", verified: "проверена", closed: "закрыта",
  rejected: "отклонена", abandoned: "отменена", superseded: "заменена",
};

const COMMITMENT: Record<string, string> = {
  open: "взято", in_progress: "в работе", fulfilled: "выполнено",
  failed: "не выполнено", withdrawn: "снято",
};

const RESULT: Record<string, string> = {
  reported: "сообщён", under_verification: "на проверке", verified: "проверен",
  partially_verified: "частично проверен", rejected: "отклонён", disputed: "оспорен",
};

const PROBLEM: Record<string, string> = {
  open: "открыта", qualified: "квалифицирована", rejected: "отклонена", deferred: "отложена",
};

const DECISION: Record<string, string> = {
  proposed: "предложено", in_discussion: "обсуждение", voting: "голосование",
  accepted: "принято", rejected: "отклонено", revised: "пересмотрено",
};

const CHALLENGE: Record<string, string> = {
  open: "открыто", acknowledged: "принято к сведению", addressed: "учтено",
  accepted: "принято", rejected: "отклонено", withdrawn: "снято", deferred: "отложено",
};

const ACTIVITY: Record<string, string> = {
  planned: "запланирована", in_progress: "идёт", completed: "завершена", cancelled: "отменена",
};

const PARTICIPATION: Record<string, string> = {
  active: "участвует", left: "вышел(ла)",
};

const BY_CONTEXT: Record<string, Record<string, string>> = {
  goal: GOAL, commitment: COMMITMENT, result: RESULT, problem: PROBLEM,
  decision: DECISION, challenge: CHALLENGE, activity: ACTIVITY, participation: PARTICIPATION,
};

/** Fallback dictionary for statuses without context. */
const STATUS: Record<string, string> = { ...GOAL, ...RESULT, ...DECISION, ...ACTIVITY, ...CHALLENGE };

export function statusLabel(status: string, context?: string): string {
  if (context && BY_CONTEXT[context] && BY_CONTEXT[context][status]) return BY_CONTEXT[context][status];
  return STATUS[status] ?? status;
}

export const KIND_LABELS: Record<string, string> = {
  goal: "цель", problem: "проблема", decision: "решение", commitment: "обязательство",
  activity: "деятельность", result: "результат", challenge: "возражение",
  participation: "участие", task: "задача",
};
export function kindLabel(kind: string): string {
  return KIND_LABELS[kind] ?? kind;
}

export const ROLE_LABELS: Record<string, string> = {
  contributor: "участник", coordinator: "координатор", expert: "эксперт",
  facilitator: "фасилитатор", observer: "наблюдатель", owner: "владелец",
};
export function roleLabel(role: string): string {
  return ROLE_LABELS[role] ?? role;
}

export const RELATION_LABELS: Record<string, string> = {
  concretizes: "конкретизирует", depends_on: "зависит от", supports: "поддерживает",
  conflicts_with: "конфликтует с", contributes_to: "содействует", blocks: "блокирует",
  supersedes: "заменяет", serves: "служит",
};
export function relationLabel(type: string): string {
  return RELATION_LABELS[type] ?? type;
}

export const CAPABILITY_LABELS: Record<string, string> = {
  coordinate: "координация", transition: "переводы по циклу", verify_result: "верификация результатов",
};
export function capabilityLabel(capability: string): string {
  return CAPABILITY_LABELS[capability] ?? capability;
}

export const CRITERION_LABELS: Record<string, string> = {
  binary: "бинарный", quantitative: "количественный", qualitative: "качественный", composite: "составной",
};

export const METHOD_LABELS: Record<string, string> = {
  majority: "большинство", supermajority: "супербольшинство (2/3)",
  unanimity: "единогласие", consent: "консент (без возражений)",
};

export const VOTE_LABELS: Record<string, string> = { accept: "за", reject: "против" };

export const CONCLUSION_LABELS: Record<string, string> = {
  successful: "цель достигнута", partially_successful: "частично достигнута",
  unsuccessful: "не достигнута", decision_correct_implementation_failed: "решение верно, исполнение подвело",
  decision_flawed: "решение ошибочно", external_factors: "внешние факторы",
};

export const TARGET_LABELS: Record<string, string> = {
  goal: "цель", decision: "решение", result: "результат", problem: "проблема",
};
