import { useCallback, useEffect, useState } from "react";
import { request } from "../api/client";
import type { Commitment, Goal } from "../types";

const STATUS_LABELS: Record<string, string> = {
  open: "взято",
  in_progress: "в работе",
  fulfilled: "выполнено",
  failed: "не выполнено",
  withdrawn: "снято",
};

/** «Моя деятельность»: мои обязательства по всем целям — вместо списка
 * «моих проектов» (Track F: деятельность центрирована на целях). */
export function MyActivity({ onOpenGoal }: { onOpenGoal?: (goalId: number) => void }) {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      const [mine, goalData] = await Promise.all([request<Commitment[]>("/commitments/my"), request<Goal[]>("/goals")]);
      setCommitments(mine);
      setGoals(goalData);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const advance = async (id: number, status: string) => {
    setBusy(true);
    try {
      await request(`/commitments/${id}/status`, { method: "POST", body: JSON.stringify({ status }) });
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Действие не удалось");
    } finally {
      setBusy(false);
    }
  };

  const active = commitments.filter((c) => c.status === "open" || c.status === "in_progress");
  const done = commitments.filter((c) => c.status !== "open" && c.status !== "in_progress");

  return (
    <>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Моя деятельность</span>
            <h2>Что я взял(а) на себя</h2>
          </div>
          <span className="count">{active.length}</span>
        </div>
        {error && <p className="error">{error}</p>}
        {active.length === 0 ? (
          <p className="muted empty">Активных обязательств нет. Откройте цель и возьмите обязательство.</p>
        ) : (
          <div className="problem-list">
            {active.map((c) => {
              const goal = goals.find((g) => g.id === c.goal_id);
              return (
                <article key={c.id}>
                  <span className="problem-icon">◈</span>
                  <div>
                    <h3>{c.description}</h3>
                    {c.expected_result && <p className="muted">Ожидание: {c.expected_result}</p>}
                    <small>
                      <span className="event-type-badge">{STATUS_LABELS[c.status] ?? c.status}</span>{" "}
                      {goal ? "цель: " : "цель #"}
                      {goal && (
                        <button className="link-button" onClick={() => onOpenGoal?.(goal.id)}>
                          {goal.title}
                        </button>
                      )}
                      {c.deadline && ` · срок ${c.deadline.slice(0, 10)}`}
                    </small>
                    <div className="event-buttons" style={{ marginTop: 6 }}>
                      {c.status === "open" && (
                        <button disabled={busy} onClick={() => advance(c.id, "in_progress")}>
                          Начать работу
                        </button>
                      )}
                      {c.status === "in_progress" && (
                        <button disabled={busy} className="primary" onClick={() => advance(c.id, "fulfilled")}>
                          Выполнено
                        </button>
                      )}
                      <button disabled={busy} onClick={() => advance(c.id, "withdrawn")}>
                        Снять
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {done.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">История</span>
              <h2>Завершённые обязательства</h2>
            </div>
            <span className="count">{done.length}</span>
          </div>
          <div className="problem-list">
            {done.map((c) => (
              <article key={c.id}>
                <span className="problem-icon">✓</span>
                <div>
                  <h3>
                    {c.description} <span className="event-type-badge">{STATUS_LABELS[c.status] ?? c.status}</span>
                  </h3>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
