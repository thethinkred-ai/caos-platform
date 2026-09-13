import { FormEvent, useState } from "react";
import { request } from "../api/client";
import type { Competence } from "../types";

/** Own competences: visible-to-participants by default (is_visible=false),
 * feeding task matching and AI analysis. */
export function CompetencesSection({
  competences,
  onReload,
  onError,
}: {
  competences: Competence[];
  onReload: () => void;
  onError: (message: string) => void;
}) {
  const [name, setName] = useState("");
  const [level, setLevel] = useState(3);
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const createCompetence = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await request("/competences", {
        method: "POST",
        body: JSON.stringify({ name, level, description }),
      });
      setName("");
      setDescription("");
      onReload();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось добавить компетенцию");
    } finally {
      setBusy(false);
    }
  };

  const deleteCompetence = async (id: number) => {
    setBusy(true);
    try {
      await request(`/competences/${id}`, { method: "DELETE" });
      onReload();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось удалить");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="catalog-layout">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Навыки</span>
            <h2>Добавить компетенцию</h2>
          </div>
        </div>
        <form onSubmit={createCompetence} className="problem-form">
          <input placeholder="Название (например, фасилитация)" value={name} onChange={(e) => setName(e.target.value)} required minLength={2} />
          <select value={level} onChange={(e) => setLevel(Number(e.target.value))}>
            <option value={1}>Уровень 1 — новичок</option>
            <option value={2}>Уровень 2 — базовый</option>
            <option value={3}>Уровень 3 — уверенный</option>
            <option value={4}>Уровень 4 — продвинутый</option>
            <option value={5}>Уровень 5 — эксперт</option>
          </select>
          <textarea placeholder="Описание (контекст, опыт применения)" value={description} onChange={(e) => setDescription(e.target.value)} />
          <button className="primary" type="submit" disabled={busy}>
            Добавить
          </button>
        </form>
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Ваши навыки</span>
            <h2>Компетенции</h2>
          </div>
          <span className="count">{competences.length}</span>
        </div>
        {competences.length === 0 ? (
          <p className="muted empty">Добавьте первую компетенцию, чтобы отметить свои навыки.</p>
        ) : (
          <div className="problem-list">
            {competences.map((c) => (
              <article key={c.id} className="competence-entry">
                <span className="problem-icon">★</span>
                <div>
                  <h3>{c.name}</h3>
                  {c.description && <p>{c.description}</p>}
                  <small>
                    Уровень {c.level}/5 · #{c.id}
                  </small>
                  <button className="link-button" onClick={() => void deleteCompetence(c.id)}>
                    Удалить
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
