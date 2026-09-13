import { useCallback, useEffect, useState } from "react";
import { request } from "../api/client";
import type { AISuggestion } from "../types";

const STATUS_LABELS: Record<string, string> = {
  pending: "ждёт ревью",
  accepted: "принято",
  rejected: "отклонено",
};

/** Review surface for AI proposals (ADR-0003): every AI output is
 * recorded with its model, snapshot and confidence; a human accepts or
 * rejects it here. AI never changes domain state on its own. */
export function AIProposalsPanel() {
  const [proposals, setProposals] = useState<AISuggestion[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reasons, setReasons] = useState<Record<number, string>>({});

  const reload = useCallback(async () => {
    try {
      setProposals(await request<AISuggestion[]>("/ai/suggestions"));
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки предложений AI");
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const resolve = async (id: number, status: string) => {
    setBusy(true);
    try {
      await request(`/ai/suggestions/${id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ status, reason: reasons[id] ?? "" }),
      });
      setReasons((prev) => ({ ...prev, [id]: "" }));
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось сохранить решение");
    } finally {
      setBusy(false);
    }
  };

  const pending = proposals.filter((p) => p.status === "pending");
  const reviewed = proposals.filter((p) => p.status !== "pending");

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">AI предлагает — вы решаете</span>
          <h2>Предложения AI</h2>
        </div>
        <span className="count">{pending.length}</span>
      </div>
      {error && <p className="error">{error}</p>}
      {proposals.length === 0 ? (
        <p className="muted empty">
          Предложений пока нет — они появляются после использования AI-рекомендаций в целях.
        </p>
      ) : (
        <div className="problem-list">
          {pending.map((p) => (
            <article key={p.id}>
              <span className="problem-icon" style={{ color: "var(--ai)" }}>◆</span>
              <div>
                <h3>{p.suggestion}</h3>
                <small>
                  <span className="event-type-badge">{p.endpoint}</span>
                  {p.target_type && ` · ${p.target_type} #${p.target_id}`}
                  {` · источник: ${p.model_name}`}
                  {p.confidence !== null && ` · уверенность ${Math.round(p.confidence * 100)}%`}
                </small>
                <div className="problem-form" style={{ marginTop: 6 }}>
                  <input
                    placeholder="Основание решения (необязательно)"
                    value={reasons[p.id] ?? ""}
                    onChange={(e) => setReasons((prev) => ({ ...prev, [p.id]: e.target.value }))}
                  />
                  <button className="primary" disabled={busy} onClick={() => void resolve(p.id, "accepted")}>
                    Принять
                  </button>
                  <button disabled={busy} onClick={() => void resolve(p.id, "rejected")}>
                    Отклонить
                  </button>
                </div>
              </div>
            </article>
          ))}
          {reviewed.slice(0, 5).map((p) => (
            <article key={p.id}>
              <span className="problem-icon">·</span>
              <div>
                <h3>
                  {p.suggestion} <span className="event-type-badge">{STATUS_LABELS[p.status] ?? p.status}</span>
                </h3>
                {p.reason && <small>решение: {p.reason}</small>}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
