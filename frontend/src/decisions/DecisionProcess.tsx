import { FormEvent, useCallback, useEffect, useState } from "react";
import { request } from "../api/client";
import type { Challenge, Decision, ProposalVersion, User, VoteSummary } from "../types";

/** The decision as a process (Track F): versions of the proposal, the
 * vote state with aggregates, and structured objections — not just a
 * status label. */
export function DecisionProcess({
  decision,
  user,
  onReload,
}: {
  decision: Decision;
  user: User;
  onReload: () => void;
}) {
  const [votes, setVotes] = useState<VoteSummary | null>(null);
  const [versions, setVersions] = useState<ProposalVersion[]>([]);
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [challengeClaim, setChallengeClaim] = useState("");
  const [challengeArgument, setChallengeArgument] = useState("");

  const decisionId = decision.id;
  const reload = useCallback(async () => {
    try {
      const [voteData, versionData, challengeData] = await Promise.all([
        request<VoteSummary>(`/decisions/${decisionId}/votes`),
        request<ProposalVersion[]>(`/decisions/${decisionId}/versions`),
        request<Challenge[]>(`/challenges?target_type=decision&target_id=${decisionId}`),
      ]);
      setVotes(voteData);
      setVersions(versionData);
      setChallenges(challengeData);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки процесса решения");
    }
  }, [decisionId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await fn();
      await reload();
      onReload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Действие не удалось");
    } finally {
      setBusy(false);
    }
  };

  const vote = (variant: string) =>
    act(() => request(`/decisions/${decisionId}/vote`, { method: "POST", body: JSON.stringify({ variant }) }));

  const finalize = () => act(() => request(`/decisions/${decisionId}/finalize`, { method: "POST" }));

  const createChallenge = (e: FormEvent) => {
    e.preventDefault();
    if (!challengeClaim.trim() || !challengeArgument.trim()) return;
    void act(async () => {
      await request(`/challenges`, {
        method: "POST",
        body: JSON.stringify({ target_type: "decision", target_id: decisionId, claim: challengeClaim, argument: challengeArgument }),
      });
      setChallengeClaim("");
      setChallengeArgument("");
    });
  };

  const open = decision.status === "proposed" || decision.status === "in_discussion" || decision.status === "voting";
  const isAuthor = decision.author_id === user.id;
  const canVote = open; // eligibility (goal context) is enforced by the backend

  return (
    <div className="decision-process" style={{ marginTop: 10 }}>
      <div className="project-meta">
        <span>метод: <b>{decision.decision_method}</b></span>
        <span>кворум: <b>{decision.quorum}</b></span>
        {decision.valid_until && <span>действует до: <b>{decision.valid_until.slice(0, 10)}</b></span>}
      </div>
      {error && <p className="error">{error}</p>}

      {votes && (
        <div style={{ marginTop: 8 }}>
          <b>
            За {votes.accept} · Против {votes.reject} · всего {votes.total}/{votes.quorum}
            {votes.quorum_met ? " ✓" : " — кворум не собран"}
          </b>
          {votes.own_vote && <small> · ваш голос: {votes.own_vote.variant}</small>}
          {open && canVote && !votes.own_vote && (
            <div className="event-buttons" style={{ marginTop: 6 }}>
              <button className="primary" disabled={busy} onClick={() => vote("accept")}>
                Голосовать за
              </button>
              <button disabled={busy} onClick={() => vote("reject")}>
                Голосовать против
              </button>
            </div>
          )}
          {open && isAuthor && (
            <div className="event-buttons" style={{ marginTop: 6 }}>
              <button disabled={busy} onClick={finalize}>
                Подвести итог
              </button>
            </div>
          )}
          {votes.votes && (
            <div className="event-timeline" style={{ marginTop: 6 }}>
              {votes.votes.map((v) => (
                <div key={v.id} className="event-timeline-item">
                  <span className={`event-type-badge event-type-${v.variant === "accept" ? "accepted" : "rejected"}`}>{v.variant}</span>
                  <div>
                    {v.comment && <p>{v.comment}</p>}
                    <small>{new Date(v.created_at).toLocaleDateString("ru-RU")}</small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {versions.length > 1 && (
        <div style={{ marginTop: 10 }}>
          <b>Версии предложения</b>
          <div className="event-timeline" style={{ marginTop: 6 }}>
            {versions.map((v) => (
              <div key={v.id} className="event-timeline-item">
                <span className="event-type-badge">v{v.version}</span>
                <div>
                  <p>{v.content}</p>
                  <small>{new Date(v.created_at).toLocaleDateString("ru-RU")}</small>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {challenges.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <b>Возражения</b>
          {challenges.map((ch) => (
            <div key={ch.id} className="event-timeline-item" style={{ marginTop: 6 }}>
              <span className="event-type-badge">{ch.status}</span>
              <div>
                <b>{ch.claim}</b>
                <p className="muted">{ch.argument}</p>
                {ch.resolution && <small>Резолюция: {ch.resolution}</small>}
              </div>
            </div>
          ))}
        </div>
      )}

      {open && (
        <form onSubmit={createChallenge} className="problem-form" style={{ marginTop: 8 }}>
          <input placeholder="Возражение: что именно неверно" value={challengeClaim} onChange={(e) => setChallengeClaim(e.target.value)} required minLength={3} />
          <input placeholder="Аргумент" value={challengeArgument} onChange={(e) => setChallengeArgument(e.target.value)} required minLength={3} />
          <button type="submit" disabled={busy}>
            Оспорить решение
          </button>
        </form>
      )}
    </div>
  );
}
