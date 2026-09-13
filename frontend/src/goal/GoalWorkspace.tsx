import { FormEvent, useCallback, useEffect, useState } from "react";
import { request } from "../api/client";
import {
  CRITERION_TYPES,
  EVIDENCE_TYPES,
  GOAL_RELATION_TYPES,
  type Activity,
  type Challenge,
  type Delegation,
  type Evaluation,
  type GoalExplain,
  type Commitment,
  type Evidence,
  type Goal,
  type GoalCriterion,
  type GoalImpact,
  type GoalMeasurement,
  type GoalParticipation,
  type GoalRelation,
  type ResultItem,
  type User,
} from "../types";

const LIFECYCLE_ACTIONS: Record<string, { label: string; from: string[] }[]> = {
  draft: [{ label: "Предложить", from: ["propose"] }],
  proposed: [
    { label: "На рассмотрение", from: ["review"] },
    { label: "Принять", from: ["accept"] },
    { label: "Отклонить", from: ["reject"] },
  ],
  under_review: [
    { label: "Принять", from: ["accept"] },
    { label: "Отклонить", from: ["reject"] },
  ],
  accepted: [
    { label: "Активировать", from: ["activate"] },
    { label: "Отменить", from: ["abandon"] },
  ],
  active: [
    { label: "Приостановить", from: ["suspend"] },
    { label: "Цель достигнута", from: ["report-achieved"] },
    { label: "Отменить", from: ["abandon"] },
  ],
  suspended: [
    { label: "Возобновить", from: ["resume"] },
    { label: "Отменить", from: ["abandon"] },
  ],
  achieved: [{ label: "Проверить", from: ["verify"] }],
  verified: [{ label: "Закрыть", from: ["close"] }],
};

const COMMITMENT_NEXT: Record<string, string[]> = {
  open: ["in_progress", "withdrawn"],
  in_progress: ["fulfilled", "failed", "withdrawn"],
};

const COMMITMENT_LABELS: Record<string, string> = {
  in_progress: "В работе",
  fulfilled: "Выполнено",
  failed: "Не выполнено",
  withdrawn: "Снято",
};

export function GoalWorkspace({ goalId, goals, user, onBack }: { goalId: number; goals: Goal[]; user: User; onBack: () => void }) {
  const [goal, setGoal] = useState<Goal | null>(goals.find((g) => g.id === goalId) ?? null);
  const [impact, setImpact] = useState<GoalImpact | null>(null);
  const [relations, setRelations] = useState<GoalRelation[]>([]);
  const [participations, setParticipations] = useState<GoalParticipation[]>([]);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [criteria, setCriteria] = useState<GoalCriterion[]>([]);
  const [measurements, setMeasurements] = useState<Record<number, GoalMeasurement[]>>({});
  const [measurementFor, setMeasurementFor] = useState<number | null>(null);
  const [measurementValue, setMeasurementValue] = useState("");
  const [measurementSource, setMeasurementSource] = useState("");
  const [results, setResults] = useState<ResultItem[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [delegations, setDelegations] = useState<Delegation[]>([]);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [activityType, setActivityType] = useState("task");
  const [activityTitle, setActivityTitle] = useState("");
  const [evaluations, setEvaluations] = useState<Record<number, Evaluation[]>>({});
  const [evalFor, setEvalFor] = useState<number | null>(null);
  const [evalConclusion, setEvalConclusion] = useState("partially_successful");
  const [evalInsight, setEvalInsight] = useState("");
  const [delegRecipient, setDelegRecipient] = useState("");
  const [delegCapability, setDelegCapability] = useState("coordinate");
  const [delegReason, setDelegReason] = useState("");
  const [delegUntil, setDelegUntil] = useState("");
  const [explain, setExplain] = useState<GoalExplain | null>(null);
  const [explainOpen, setExplainOpen] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const [relTarget, setRelTarget] = useState("");
  const [relType, setRelType] = useState<string>("depends_on");
  const [relRationale, setRelRationale] = useState("");
  const [commitmentText, setCommitmentText] = useState("");
  const [commitmentResult, setCommitmentResult] = useState("");
  const [criterionName, setCriterionName] = useState("");
  const [criterionTarget, setCriterionTarget] = useState("");
  const [resultText, setResultText] = useState("");
  const [resultActual, setResultActual] = useState("");
  const [evidenceFor, setEvidenceFor] = useState<number | null>(null);
  const [evidenceText, setEvidenceText] = useState("");
  const [challengeClaim, setChallengeClaim] = useState("");
  const [challengeArgument, setChallengeArgument] = useState("");

  const reload = useCallback(async () => {
    try {
      const [goalData, impactData, relationsData, partsData, commitsData, criteriaData, resultsData, challengesData, explainData, delegationsData, activitiesData] =
        await Promise.all([
          request<Goal[]>(`/goals`),
          request<GoalImpact>(`/goals/${goalId}/impact`),
          request<GoalRelation[]>(`/goals/${goalId}/relations`),
          request<GoalParticipation[]>(`/goals/${goalId}/participations`),
          request<Commitment[]>(`/goals/${goalId}/commitments`),
          request<GoalCriterion[]>(`/goals/${goalId}/criteria`),
          request<ResultItem[]>(`/goals/${goalId}/results`),
          request<Challenge[]>(`/challenges?target_type=goal&target_id=${goalId}`),
          request<GoalExplain>(`/goals/${goalId}/explain`),
          request<Delegation[]>(`/goals/${goalId}/delegations`),
          request<Activity[]>(`/goals/${goalId}/activities`),
        ]);
      setGoal(goalData.find((g) => g.id === goalId) ?? null);
      setImpact(impactData);
      setRelations(relationsData);
      setParticipations(partsData);
      setCommitments(commitsData);
      setCriteria(criteriaData);
      setResults(resultsData);
      setChallenges(challengesData);
      setExplain(explainData);
      setDelegations(delegationsData);
      setActivities(activitiesData);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки цели");
    }
  }, [goalId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  // Criterion dynamics: fetch measurement history once criteria are known.
  useEffect(() => {
    void (async () => {
      for (const criterion of criteria) {
        if (measurements[criterion.id] !== undefined) continue;
        try {
          const data = await request<GoalMeasurement[]>(`/criteria/${criterion.id}/measurements`);
          setMeasurements((prev) => ({ ...prev, [criterion.id]: data }));
        } catch {
          setMeasurements((prev) => ({ ...prev, [criterion.id]: [] }));
        }
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [criteria]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Действие не удалось");
    } finally {
      setBusy(false);
    }
  };

  const transition = (action: string) => act(() => request(`/goals/${goalId}/transition`, { method: "POST", body: JSON.stringify({ action }) }));
  const join = () => act(() => request(`/goals/${goalId}/participations`, { method: "POST", body: JSON.stringify({}) }));
  const leave = () => act(() => request(`/goals/${goalId}/participations/leave`, { method: "POST" }));

  const addRelation = (e: FormEvent) => {
    e.preventDefault();
    if (!relTarget || !relRationale.trim()) return;
    void act(async () => {
      await request(`/goals/${goalId}/relations`, {
        method: "POST",
        body: JSON.stringify({ target_goal_id: Number(relTarget), relation_type: relType, rationale: relRationale }),
      });
      setRelTarget("");
      setRelRationale("");
    });
  };

  const createCommitment = (e: FormEvent) => {
    e.preventDefault();
    if (!commitmentText.trim()) return;
    void act(async () => {
      await request(`/goals/${goalId}/commitments`, {
        method: "POST",
        body: JSON.stringify({ description: commitmentText, expected_result: commitmentResult }),
      });
      setCommitmentText("");
      setCommitmentResult("");
    });
  };

  const createCriterion = (e: FormEvent) => {
    e.preventDefault();
    if (!criterionName.trim()) return;
    void act(async () => {
      await request(`/goals/${goalId}/criteria`, {
        method: "POST",
        body: JSON.stringify({ name: criterionName, criterion_type: "quantitative", target_value: criterionTarget }),
      });
      setCriterionName("");
      setCriterionTarget("");
    });
  };

  const recordMeasurement = (criterionId: number) => {
    if (!measurementValue.trim()) return;
    void act(async () => {
      await request(`/criteria/${criterionId}/measurements`, {
        method: "POST",
        body: JSON.stringify({ value: measurementValue, source: measurementSource }),
      });
      setMeasurementValue("");
      setMeasurementSource("");
      setMeasurementFor(null);
      const data = await request<GoalMeasurement[]>(`/criteria/${criterionId}/measurements`);
      setMeasurements((prev) => ({ ...prev, [criterionId]: data }));
    });
  };

  const reportResult = (e: FormEvent) => {
    e.preventDefault();
    if (!resultText.trim()) return;
    void act(async () => {
      await request(`/goals/${goalId}/results`, {
        method: "POST",
        body: JSON.stringify({ description: resultText, actual_state: resultActual }),
      });
      setResultText("");
      setResultActual("");
    });
  };

  const attachEvidence = (resultId: number) => {
    if (!evidenceText.trim()) return;
    void act(async () => {
      await request(`/results/${resultId}/evidence`, {
        method: "POST",
        body: JSON.stringify({ evidence_type: "document", content: evidenceText }),
      });
      setEvidenceText("");
      setEvidenceFor(null);
    });
  };

  const verifyResult = (resultId: number, status: string) =>
    act(() => request(`/results/${resultId}/verify`, { method: "POST", body: JSON.stringify({ status, rationale: "Проверено в интерфейсе цели" }) }));

  const createDelegation = () => {
    if (!delegRecipient || !delegReason.trim() || !delegUntil) return;
    void act(async () => {
      await request(`/goals/${goalId}/delegations`, {
        method: "POST",
        body: JSON.stringify({
          recipient_id: Number(delegRecipient),
          capability: delegCapability,
          reason: delegReason,
          valid_until: new Date(delegUntil).toISOString(),
        }),
      });
      setDelegRecipient("");
      setDelegReason("");
      setDelegUntil("");
    });
  };

  const revokeDelegation = (id: number) =>
    act(() => request(`/delegations/${id}/revoke`, { method: "POST" }));

  const createActivity = (e: FormEvent) => {
    e.preventDefault();
    if (!activityTitle.trim()) return;
    void act(async () => {
      await request(`/goals/${goalId}/activities`, {
        method: "POST",
        body: JSON.stringify({ activity_type: activityType, title: activityTitle }),
      });
      setActivityTitle("");
    });
  };

  const advanceActivity = (id: number, next: string) =>
    act(() => request(`/activities/${id}/status`, { method: "POST", body: JSON.stringify({ status: next }) }));

  const loadEvaluations = async (resultId: number) => {
    if (evaluations[resultId] !== undefined) return;
    try {
      const data = await request<Evaluation[]>(`/results/${resultId}/evaluations`);
      setEvaluations((prev) => ({ ...prev, [resultId]: data }));
    } catch {
      setEvaluations((prev) => ({ ...prev, [resultId]: [] }));
    }
  };

  const createEvaluation = (resultId: number) => {
    void act(async () => {
      await request(`/results/${resultId}/evaluations`, {
        method: "POST",
        body: JSON.stringify({ conclusion: evalConclusion, insight: evalInsight }),
      });
      setEvalInsight("");
      setEvalFor(null);
      const data = await request<Evaluation[]>(`/results/${resultId}/evaluations`);
      setEvaluations((prev) => ({ ...prev, [resultId]: data }));
    });
  };

  const createChallenge = (e: FormEvent) => {
    e.preventDefault();
    if (!challengeClaim.trim() || !challengeArgument.trim()) return;
    void act(async () => {
      await request(`/challenges`, {
        method: "POST",
        body: JSON.stringify({ target_type: "goal", target_id: goalId, claim: challengeClaim, argument: challengeArgument }),
      });
      setChallengeClaim("");
      setChallengeArgument("");
    });
  };

  const myParticipation = participations.find((p) => p.user_id === user.id && p.status === "active");
  const isOwner = goal?.owner_id === user.id;
  const lifecycle = goal ? (LIFECYCLE_ACTIONS[goal.status] ?? []) : [];
  const goalTitle = (id: number) => goals.find((g) => g.id === id)?.title ?? `Цель #${id}`;

  if (!goal) {
    return (
      <section className="panel">
        <button onClick={onBack}>← К списку целей</button>
        {error && <p className="error">{error}</p>}
      </section>
    );
  }

  return (
    <div className="goal-workspace">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Цель · рабочее пространство</span>
            <h2>{goal.title}</h2>
            <p className="muted">{goal.description}</p>
            <small>
              <span className="event-type-badge">статус: {goal.status}</span> #{goal.id}
            </small>
          </div>
          <button onClick={onBack}>← К списку</button>
        </div>
        <div className="event-buttons" style={{ marginTop: 10 }}>
          {lifecycle.map(({ label, from }) => (
            <button key={from[0]} className="primary" disabled={busy} onClick={() => transition(from[0])}>
              {label}
            </button>
          ))}
          {!isOwner && !myParticipation && (
            <button disabled={busy} onClick={join}>
              Присоединиться к цели
            </button>
          )}
          {myParticipation && (
            <button disabled={busy} onClick={leave}>
              Выйти из цели (роль: {myParticipation.role})
            </button>
          )}
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {explain && explain.chain.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Обоснование</span>
              <h2>Почему эта цель существует</h2>
            </div>
            <button onClick={() => setExplainOpen(!explainOpen)}>{explainOpen ? "Свернуть" : "Показать цепочку"}</button>
          </div>
          {explainOpen ? (
            <div className="event-timeline">
              {explain.chain.map((node, i) => (
                <div key={`${node.kind}-${node.id}-${i}`} className="event-timeline-item">
                  <span className={`event-type-badge event-type-${node.kind}`}>{node.kind} #{node.id}</span>
                  <div>
                    <b>{node.title}</b>
                    {node.detail && <p className="muted">{node.detail}</p>}
                    <small>{node.status}</small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">
              Проблема → решения ({explain.counts.decisions}) → обязательства ({explain.counts.commitments}) → задачи (
              {explain.counts.tasks}) → результаты ({explain.counts.results}).
            </p>
          )}
        </section>
      )}

      {impact && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Влияние</span>
              <h2>Что остановится, если цель провалится</h2>
            </div>
          </div>
          <div className="project-meta">
            <span>Зависят напрямую: <b>{impact.direct_dependents}</b></span>
            <span>Зависят транзитивно: <b>{impact.transitive_dependents}</b></span>
            <span>Поддерживают: <b>{impact.supporters}</b></span>
            <span>Конфликты: <b>{impact.conflicts}</b></span>
            <span>Подцели: <b>{impact.sub_goals}</b></span>
            <span>Проекты: <b>{impact.projects}</b></span>
            <span>Решения: <b>{impact.decisions}</b></span>
          </div>
        </section>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Граф целей</span>
            <h2>Связи</h2>
          </div>
          <span className="count">{relations.length}</span>
        </div>
        {relations.length === 0 ? (
          <p className="muted empty">Связей пока нет.</p>
        ) : (
          <div className="problem-list">
            {relations.map((r) => (
              <article key={r.id}>
                <span className="problem-icon">→</span>
                <div>
                  <h3>
                    {r.source_goal_id === goalId ? "Эта цель" : goalTitle(r.source_goal_id)}{" "}
                    <span className="event-type-badge">{r.relation_type}</span>{" "}
                    {r.target_goal_id === goalId ? "эта цель" : goalTitle(r.target_goal_id)}
                  </h3>
                  <p>{r.rationale}</p>
                </div>
              </article>
            ))}
          </div>
        )}
        <form onSubmit={addRelation} className="problem-form">
          <select value={relTarget} onChange={(e) => setRelTarget(e.target.value)} required>
            <option value="">Цель…</option>
            {goals
              .filter((g) => g.id !== goalId)
              .map((g) => (
                <option key={g.id} value={g.id}>
                  {g.title}
                </option>
              ))}
          </select>
          <select value={relType} onChange={(e) => setRelType(e.target.value)}>
            {GOAL_RELATION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <input placeholder="Почему эта связь существует" value={relRationale} onChange={(e) => setRelRationale(e.target.value)} required minLength={3} />
          <button className="primary" type="submit" disabled={busy}>
            Связать
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Участие</span>
            <h2>Участники</h2>
          </div>
          <span className="count">{participations.filter((p) => p.status === "active").length}</span>
        </div>
        {participations.length === 0 ? (
          <p className="muted empty">Пока никто не присоединился явно.</p>
        ) : (
          <div className="problem-list">
            {participations.map((p) => (
              <article key={p.id}>
                <span className="problem-icon">◦</span>
                <div>
                  <h3>
                    {p.display_name} <span className="event-type-badge">{p.role}</span>
                  </h3>
                  <small>{p.status === "active" ? `с ${p.joined_at.slice(0, 10)}` : `вышел(ла) ${p.left_at?.slice(0, 10) ?? ""}`}</small>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Обязательства</span>
            <h2>Кто взял ответственность</h2>
          </div>
          <span className="count">{commitments.length}</span>
        </div>
        {commitments.map((c) => (
          <article key={c.id} style={{ marginBottom: 8 }}>
            <div>
              <h3>
                {c.display_name}: {c.description} <span className="event-type-badge">{c.status}</span>
              </h3>
              {c.expected_result && <p className="muted">Ожидание: {c.expected_result}</p>}
              {c.user_id === user.id && (COMMITMENT_NEXT[c.status] ?? []).length > 0 && (
                <div className="event-buttons">
                  {COMMITMENT_NEXT[c.status].map((next) => (
                    <button key={next} disabled={busy} onClick={() => act(() => request(`/commitments/${c.id}/status`, { method: "POST", body: JSON.stringify({ status: next }) }))}>
                      {COMMITMENT_LABELS[next]}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </article>
        ))}
        <form onSubmit={createCommitment} className="problem-form">
          <input placeholder="Я беру на себя…" value={commitmentText} onChange={(e) => setCommitmentText(e.target.value)} required minLength={3} />
          <input placeholder="Ожидаемый результат" value={commitmentResult} onChange={(e) => setCommitmentResult(e.target.value)} />
          <button className="primary" type="submit" disabled={busy}>
            Взять обязательство
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Измеримость</span>
            <h2>Критерии достижения</h2>
          </div>
          <span className="count">{criteria.length}</span>
        </div>
        {criteria.length === 0 ? (
          <p className="muted empty">Критериев нет — цель непроверяема.</p>
        ) : (
          <div className="problem-list">
            {criteria.map((c) => {
              const history = measurements[c.id] ?? [];
              return (
              <article key={c.id}>
                <span className="problem-icon">≡</span>
                <div>
                  <h3>
                    {c.name} <span className="event-type-badge">{c.criterion_type}</span>
                  </h3>
                  <small>
                    {c.baseline && `базовая: ${c.baseline} → `}цель: {c.target_value} {c.unit}
                  </small>
                  {history.length > 0 && (
                    <small style={{ display: "block" }}>
                      динамика: {history.map((m) => m.value).join(" → ")}
                    </small>
                  )}
                  <div className="event-buttons" style={{ marginTop: 4 }}>
                    <button onClick={() => setMeasurementFor(measurementFor === c.id ? null : c.id)}>
                      {measurementFor === c.id ? "Отмена" : "Записать измерение"}
                    </button>
                  </div>
                  {measurementFor === c.id && (
                    <div className="problem-form" style={{ marginTop: 6 }}>
                      <input placeholder="Значение (74%)" value={measurementValue} onChange={(e) => setMeasurementValue(e.target.value)} />
                      <input placeholder="Источник (аналитика курса)" value={measurementSource} onChange={(e) => setMeasurementSource(e.target.value)} />
                      <button className="primary" disabled={busy || !measurementValue.trim()} onClick={() => recordMeasurement(c.id)}>
                        Записать
                      </button>
                    </div>
                  )}
                </div>
              </article>
              );
            })}
          </div>
        )}
        <form onSubmit={createCriterion} className="problem-form">
          <input placeholder="Критерий (например: доля завершивших курс)" value={criterionName} onChange={(e) => setCriterionName(e.target.value)} required minLength={3} />
          <input placeholder="Целевое значение (78%)" value={criterionTarget} onChange={(e) => setCriterionTarget(e.target.value)} />
          <button className="primary" type="submit" disabled={busy}>
            Добавить критерий
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Результаты</span>
            <h2>Изменение положения дел</h2>
          </div>
          <span className="count">{results.length}</span>
        </div>
        {results.map((r) => (
          <article key={r.id} style={{ marginBottom: 10 }}>
            <div>
              <h3>
                {r.description} <span className="event-type-badge">{r.status}</span>
              </h3>
              {r.actual_state && <p className="muted">Фактически: {r.actual_state}</p>}
              <small>
                доказательств: {r.evidence_count}
                {r.verified_at && ` · проверено ${r.verified_at.slice(0, 10)}`}
              </small>
              <div className="event-buttons" style={{ marginTop: 6 }}>
                {r.status === "reported" && r.reported_by !== user.id && (
                  <>
                    <button disabled={busy} onClick={() => verifyResult(r.id, "verified")}>
                      Подтвердить
                    </button>
                    <button disabled={busy} onClick={() => verifyResult(r.id, "rejected")}>
                      Отклонить
                    </button>
                  </>
                )}
                <button onClick={() => setEvidenceFor(evidenceFor === r.id ? null : r.id)}>
                  {evidenceFor === r.id ? "Отмена" : "Добавить доказательство"}
                </button>
              </div>
              {evidenceFor === r.id && (
                <div className="problem-form" style={{ marginTop: 6 }}>
                  <input placeholder="Доказательство (факт, ссылка, измерение)" value={evidenceText} onChange={(e) => setEvidenceText(e.target.value)} />
                  <button className="primary" onClick={() => attachEvidence(r.id)} disabled={busy || !evidenceText.trim()}>
                    Прикрепить
                  </button>
                </div>
              )}
              <div className="event-buttons" style={{ marginTop: 4 }}>
                <button
                  onClick={() => {
                    setEvalFor(evalFor === r.id ? null : r.id);
                    void loadEvaluations(r.id);
                  }}
                >
                  {evalFor === r.id ? "Скрыть оценки" : "Оценки смысла"}
                </button>
              </div>
              {evalFor === r.id && (
                <div style={{ marginTop: 6 }}>
                  {(evaluations[r.id] ?? []).map((ev) => (
                    <small key={ev.id} style={{ display: "block" }}>
                      <span className="event-type-badge">{ev.conclusion}</span> {ev.insight}
                    </small>
                  ))}
                  {(evaluations[r.id] ?? []).length === 0 && <p className="muted">Оценок пока нет.</p>}
                  <div className="problem-form" style={{ marginTop: 4 }}>
                    <select value={evalConclusion} onChange={(e) => setEvalConclusion(e.target.value)}>
                      <option value="successful">Цель достигнута</option>
                      <option value="partially_successful">Частично достигнута</option>
                      <option value="unsuccessful">Не достигнута</option>
                      <option value="decision_correct_implementation_failed">Решение верно, исполнение подвело</option>
                      <option value="decision_flawed">Решение ошибочно</option>
                      <option value="external_factors">Вмешались внешние факторы</option>
                    </select>
                    <input placeholder="Что это значит и чему учит" value={evalInsight} onChange={(e) => setEvalInsight(e.target.value)} />
                    <button className="primary" disabled={busy} onClick={() => createEvaluation(r.id)}>
                      Оценить
                    </button>
                  </div>
                </div>
              )}
            </div>
          </article>
        ))}
        <form onSubmit={reportResult} className="problem-form">
          <input placeholder="Результат: что изменилось в положении дел" value={resultText} onChange={(e) => setResultText(e.target.value)} required minLength={3} />
          <input placeholder="Фактическое состояние (74% завершивших)" value={resultActual} onChange={(e) => setResultActual(e.target.value)} />
          <button className="primary" type="submit" disabled={busy}>
            Сообщить результат
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Деятельность</span>
            <h2>Формы работы вокруг цели</h2>
          </div>
          <span className="count">{activities.length}</span>
        </div>
        {activities.map((a) => (
          <article key={a.id} style={{ marginBottom: 6 }}>
            <div>
              <h3>
                {a.title} <span className="event-type-badge">{a.activity_type}</span>
              </h3>
              {a.description && <p className="muted">{a.description}</p>}
              <small>
                {a.status} · {a.creator_name}
                {a.started_at && ` · начата ${a.started_at.slice(0, 10)}`}
                {a.completed_at && ` · завершена ${a.completed_at.slice(0, 10)}`}
              </small>
              {a.created_by === user.id && (a.status === "planned" || a.status === "in_progress") && (
                <div className="event-buttons" style={{ marginTop: 4 }}>
                  {a.status === "planned" && (
                    <button disabled={busy} onClick={() => advanceActivity(a.id, "in_progress")}>
                      Начать
                    </button>
                  )}
                  {a.status === "in_progress" && (
                    <button className="primary" disabled={busy} onClick={() => advanceActivity(a.id, "completed")}>
                      Завершить
                    </button>
                  )}
                  <button disabled={busy} onClick={() => advanceActivity(a.id, "cancelled")}>
                    Отменить
                  </button>
                </div>
              )}
            </div>
          </article>
        ))}
        <form onSubmit={createActivity} className="problem-form">
          <select value={activityType} onChange={(e) => setActivityType(e.target.value)}>
            <option value="task">Задача</option>
            <option value="meeting">Встреча</option>
            <option value="research">Исследование</option>
            <option value="discussion">Обсуждение</option>
            <option value="decision">Решение</option>
            <option value="external_action">Внешнее действие</option>
          </select>
          <input placeholder="Название деятельности" value={activityTitle} onChange={(e) => setActivityTitle(e.target.value)} required minLength={3} />
          <button className="primary" type="submit" disabled={busy}>
            Добавить
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Полномочия</span>
            <h2>Делегирования</h2>
          </div>
          <span className="count">{delegations.filter((d) => d.is_active).length}</span>
        </div>
        {delegations.map((d) => (
          <article key={d.id} style={{ marginBottom: 6 }}>
            <div>
              <h3>
                {d.capability} → {d.recipient_display_name || `#${d.recipient_id}`}
              </h3>
              <small>
                от {d.issuer_display_name || `#${d.issuer_id}`} · до {d.valid_until.slice(0, 10)} ·{" "}
                <span className="event-type-badge">{d.revoked_at ? "отозвано" : d.is_active ? "активно" : "истекло"}</span>
              </small>
              {d.reason && <p className="muted">{d.reason}</p>}
              {d.is_active && (isOwner || d.issuer_id === user.id) && (
                <button className="link-button" onClick={() => revokeDelegation(d.id)}>
                  Отозвать
                </button>
              )}
            </div>
          </article>
        ))}
        {isOwner && (
          <div className="problem-form" style={{ marginTop: 6 }}>
            <select value={delegRecipient} onChange={(e) => setDelegRecipient(e.target.value)}>
              <option value="">Кому…</option>
              {participations
                .filter((p) => p.status === "active" && p.user_id !== user.id)
                .map((p) => (
                  <option key={p.user_id} value={p.user_id}>
                    {p.display_name} ({p.role})
                  </option>
                ))}
            </select>
            <select value={delegCapability} onChange={(e) => setDelegCapability(e.target.value)}>
              <option value="coordinate">Координация</option>
              <option value="transition">Переводы цели по циклу</option>
              <option value="verify_result">Верификация результатов</option>
            </select>
            <input
              type="datetime-local"
              value={delegUntil}
              onChange={(e) => setDelegUntil(e.target.value)}
              required
            />
            <input placeholder="Основание (например: отпуск координатора)" value={delegReason} onChange={(e) => setDelegReason(e.target.value)} required minLength={3} />
            <button className="primary" disabled={busy || !delegRecipient || !delegUntil || !delegReason.trim()} onClick={createDelegation}>
              Делегировать
            </button>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Возражения</span>
            <h2>Оспаривание цели</h2>
          </div>
          <span className="count">{challenges.length}</span>
        </div>
        {challenges.map((ch) => (
          <article key={ch.id} style={{ marginBottom: 8 }}>
            <div>
              <h3>
                {ch.claim} <span className="event-type-badge">{ch.status}</span>
              </h3>
              <p className="muted">{ch.argument}</p>
              {ch.resolution && <small>Резолюция: {ch.resolution}</small>}
              {isOwner && ch.status === "open" && (
                <div className="event-buttons" style={{ marginTop: 6 }}>
                  <button
                    disabled={busy}
                    onClick={() =>
                      act(() =>
                        request(`/challenges/${ch.id}/resolve`, {
                          method: "POST",
                          body: JSON.stringify({ status: "accepted", resolution: "Возражение учтено" }),
                        }),
                      )
                    }
                  >
                    Принять возражение
                  </button>
                  <button
                    disabled={busy}
                    onClick={() =>
                      act(() =>
                        request(`/challenges/${ch.id}/resolve`, {
                          method: "POST",
                          body: JSON.stringify({ status: "rejected", resolution: "Отклонено с обоснованием" }),
                        }),
                      )
                    }
                  >
                    Отклонить
                  </button>
                </div>
              )}
            </div>
          </article>
        ))}
        <form onSubmit={createChallenge} className="problem-form">
          <input placeholder="С чем вы не согласны (утверждение)" value={challengeClaim} onChange={(e) => setChallengeClaim(e.target.value)} required minLength={3} />
          <input placeholder="Аргумент" value={challengeArgument} onChange={(e) => setChallengeArgument(e.target.value)} required minLength={3} />
          <button type="submit" disabled={busy}>
            Оспорить цель
          </button>
        </form>
      </section>
    </div>
  );
}
