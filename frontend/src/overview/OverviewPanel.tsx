import { useEffect, useState } from "react";
import { request } from "../api/client";
import { statusLabel, TARGET_LABELS } from "../labels";
import type { AuditEvent, Challenge, Commitment, Goal, Notification } from "../types";

/** The action map (critique, sections 86/116): four questions instead of
 * counters — where am I needed, my goals, what changed, where are the
 * problems. */
export function OverviewPanel({
  goals,
  notifications,
  auditEvents,
  onOpenGoal,
  onGoSection,
}: {
  goals: Goal[];
  notifications: Notification[];
  auditEvents: AuditEvent[];
  onOpenGoal: (goalId: number) => void;
  onGoSection: (section: "activity" | "notifications" | "goals") => void;
}) {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const [mine, myChallenges] = await Promise.all([
          request<Commitment[]>("/commitments/my"),
          request<Challenge[]>("/challenges?mine=true"),
        ]);
        if (!cancelled) {
          setCommitments(mine);
          setChallenges(myChallenges.filter((c) => c.status === "open" || c.status === "acknowledged"));
        }
      } catch {
        /* the map degrades gracefully — panels just stay empty */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const activeCommitments = commitments.filter((c) => c.status === "open" || c.status === "in_progress");
  const unread = notifications.filter((n) => !n.is_read);
  const activeGoals = goals.filter((g) => g.status === "active" || g.status === "accepted" || g.status === "draft");

  return (
    <div className="grid">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Где я нужен</span>
            <h2>Мои обязательства</h2>
          </div>
          <span className="count">{activeCommitments.length}</span>
        </div>
        {activeCommitments.length === 0 ? (
          <p className="muted empty">Активных обязательств нет.</p>
        ) : (
          <div className="problem-list">
            {activeCommitments.slice(0, 3).map((c) => (
              <article key={c.id}>
                <span className="problem-icon">◈</span>
                <div>
                  <h3>{c.description}</h3>
                  <small>
                    <span className="event-type-badge">{c.status === "open" ? "взято" : "в работе"}</span>
                    {c.goal_id && (
                      <>
                        {" · цель "}
                        <button className="link-button" onClick={() => onOpenGoal(c.goal_id)}>
                          #{c.goal_id}
                        </button>
                      </>
                    )}
                  </small>
                </div>
              </article>
            ))}
          </div>
        )}
        <button className="link-button" onClick={() => onGoSection("activity")}>
          Вся моя деятельность →
        </button>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Что изменилось</span>
            <h2>Требует внимания</h2>
          </div>
          <span className="count">{unread.length}</span>
        </div>
        {unread.length === 0 ? (
          <p className="muted empty">Новых событий нет.</p>
        ) : (
          <div className="problem-list">
            {unread.slice(0, 3).map((n) => (
              <article key={n.id}>
                <span className="problem-icon">!</span>
                <div>
                  <h3>{n.message}</h3>
                  <small>{n.entity_type} #{n.entity_id}</small>
                </div>
              </article>
            ))}
          </div>
        )}
        <button className="link-button" onClick={() => onGoSection("notifications")}>
          Все уведомления →
        </button>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Мои цели</span>
            <h2>В работе</h2>
          </div>
          <span className="count">{activeGoals.length}</span>
        </div>
        {activeGoals.length === 0 ? (
          <p className="muted empty">Целей пока нет — начните с вопроса «что должно измениться?».</p>
        ) : (
          <div className="problem-list">
            {activeGoals.slice(0, 4).map((g) => (
              <article key={g.id}>
                <span className="problem-icon">◎</span>
                <div>
                  <h3>
                    <button className="link-button" onClick={() => onOpenGoal(g.id)}>
                      {g.title}
                    </button>
                  </h3>
                  <small>{statusLabel(g.status, "goal")} · №{g.id}</small>
                </div>
              </article>
            ))}
          </div>
        )}
        <button className="link-button" onClick={() => onGoSection("goals")}>
          Все цели →
        </button>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Где проблемы</span>
            <h2>Открытые возражения</h2>
          </div>
          <span className="count">{challenges.length}</span>
        </div>
        {challenges.length === 0 ? (
          <p className="muted empty">Открытых возражений нет.</p>
        ) : (
          <div className="problem-list">
            {challenges.slice(0, 3).map((ch) => (
              <article key={ch.id}>
                <span className="problem-icon">⚑</span>
                <div>
                  <h3>{ch.claim}</h3>
                  <small>
                    {TARGET_LABELS[ch.target_type] ?? ch.target_type} №{ch.target_id} · {statusLabel(ch.status, "challenge")}
                  </small>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      {auditEvents.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">История</span>
              <h2>Последние события</h2>
            </div>
          </div>
          <div className="problem-list">
            {auditEvents.slice(0, 5).map((ev) => (
              <article key={ev.id}>
                <span className="problem-icon">·</span>
                <div>
                  <h3>{ev.action}</h3>
                  <small>{ev.detail} — {new Date(ev.created_at).toLocaleDateString("ru-RU")}</small>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
