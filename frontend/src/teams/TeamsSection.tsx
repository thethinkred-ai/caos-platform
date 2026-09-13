import { FormEvent, useState } from "react";
import { request } from "../api/client";
import type { Team } from "../types";

/** Frozen legacy form (ADR-0004): people connect to goals through
 * participation; teams stay as a secondary context and are not developed. */
export function TeamsSection({
  teams,
  onReload,
  onError,
}: {
  teams: Team[];
  onReload: () => void;
  onError: (message: string) => void;
}) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const createTeam = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await request("/teams", { method: "POST", body: JSON.stringify({ title: name, description }) });
      setName("");
      setDescription("");
      onReload();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось создать команду");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="catalog-layout">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Команда</span>
            <h2>Новая команда</h2>
          </div>
        </div>
        <form onSubmit={createTeam} className="problem-form">
          <input placeholder="Название команды" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
          <textarea placeholder="Описание" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button className="primary" type="submit" disabled={busy}>
            Создать команду
          </button>
        </form>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Ваши команды</span>
            <h2>Команды</h2>
          </div>
          <span className="count">{teams.length}</span>
        </div>
        {teams.length === 0 ? (
          <p className="muted empty">Создайте первую команду для совместной работы.</p>
        ) : (
          <div className="problem-list">
            {teams.map((team) => (
              <article key={team.id}>
                <span className="problem-icon">✦</span>
                <div>
                  <h3>{team.name}</h3>
                  <p>{team.description || "Описание пока не добавлено."}</p>
                  <small>Команда · #{team.id}</small>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
