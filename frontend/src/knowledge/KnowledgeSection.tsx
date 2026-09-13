import { FormEvent, useCallback, useEffect, useState } from "react";
import { request } from "../api/client";
import type { Goal, KnowledgeItem, KnowledgeRelation, Project } from "../types";

const RELATION_TYPES = ["supports", "explains", "evidences", "relates", "contradicts"] as const;

const RELATION_LABELS: Record<string, string> = {
  supports: "поддерживает",
  explains: "объясняет",
  evidences: "доказывает",
  relates: "относится к",
  contradicts: "противоречит",
};

/** Knowledge base with graph links (Track F, C7 UI): knowledge supports
 * goals, explains decisions, evidences results — instead of living only
 * inside one project. */
export function KnowledgeSection({
  knowledge,
  projects,
  goals,
  onReload,
  onError,
}: {
  knowledge: KnowledgeItem[];
  projects: Project[];
  goals: Goal[];
  onReload: () => void;
  onError: (message: string) => void;
}) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [projectId, setProjectId] = useState("");
  const [filterProjectId, setFilterProjectId] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [relations, setRelations] = useState<Record<number, KnowledgeRelation[]>>({});
  const [linkGoalId, setLinkGoalId] = useState("");
  const [linkType, setLinkType] = useState<string>("supports");

  const createKnowledge = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await request("/knowledge", {
        method: "POST",
        body: JSON.stringify({ title, content, project_id: projectId ? Number(projectId) : null }),
      });
      setTitle("");
      setContent("");
      setProjectId("");
      onReload();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Не удалось сохранить запись");
    } finally {
      setBusy(false);
    }
  };

  const loadRelations = useCallback(async (knowledgeId: number) => {
    try {
      const data = await request<KnowledgeRelation[]>(`/knowledge/${knowledgeId}/relations`);
      setRelations((prev) => ({ ...prev, [knowledgeId]: data }));
    } catch {
      setRelations((prev) => ({ ...prev, [knowledgeId]: [] }));
    }
  }, []);

  const toggle = (knowledgeId: number) => {
    const next = expandedId === knowledgeId ? null : knowledgeId;
    setExpandedId(next);
    if (next !== null && relations[next] === undefined) void loadRelations(next);
  };

  const linkToGoal = (knowledgeId: number) => {
    if (!linkGoalId) return;
    setBusy(true);
    void request(`/knowledge/${knowledgeId}/relations`, {
      method: "POST",
      body: JSON.stringify({ target_type: "goal", target_id: Number(linkGoalId), relation_type: linkType }),
    })
      .then(() => loadRelations(knowledgeId))
      .catch((err) => onError(err instanceof Error ? err.message : "Не удалось связать"))
      .finally(() => setBusy(false));
  };

  const visible = knowledge.filter((k) => filterProjectId === null || k.project_id === filterProjectId);

  return (
    <div className="catalog-layout">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Методологическая память</span>
            <h2>Новая запись</h2>
          </div>
        </div>
        <form onSubmit={createKnowledge} className="problem-form">
          <input placeholder="Название" value={title} onChange={(e) => setTitle(e.target.value)} required minLength={3} />
          <textarea placeholder="Содержание: опыт, практики, выводы" value={content} onChange={(e) => setContent(e.target.value)} required />
          <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
            <option value="">Без привязки к проекту</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
          <button className="primary" type="submit" disabled={busy}>
            Сохранить в базу знаний
          </button>
        </form>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Коллективный опыт в графе</span>
            <h2>База знаний</h2>
          </div>
          <span className="count">{visible.length}</span>
        </div>
        <div className="knowledge-filter">
          <select value={filterProjectId ?? ""} onChange={(e) => setFilterProjectId(e.target.value ? Number(e.target.value) : null)}>
            <option value="">Все записи</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </div>
        {knowledge.length === 0 ? (
          <p className="muted empty">Записей пока нет. Сохраните первый опыт после завершения проекта.</p>
        ) : (
          <div className="problem-list">
            {visible.map((item) => (
              <article key={item.id}>
                <span className="problem-icon">✦</span>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.content}</p>
                  <small>
                    Знание · #{item.id}
                    {item.project_name && ` · проект: ${item.project_name}`}
                    {item.created_at && ` · ${new Date(item.created_at).toLocaleDateString("ru-RU")}`}
                  </small>
                  <div className="event-buttons" style={{ marginTop: 6 }}>
                    <button onClick={() => toggle(item.id)}>
                      {expandedId === item.id ? "Скрыть связи" : "Связи с целями"}
                    </button>
                  </div>
                  {expandedId === item.id && (
                    <div style={{ marginTop: 6 }}>
                      {(relations[item.id] ?? []).length === 0 ? (
                        <p className="muted">Связей пока нет — знание не входит в граф целей.</p>
                      ) : (
                        (relations[item.id] ?? []).map((r) => (
                          <small key={r.id} style={{ display: "block" }}>
                            <span className="event-type-badge">{RELATION_LABELS[r.relation_type] ?? r.relation_type}</span>{" "}
                            {r.target_type} #{r.target_id}
                          </small>
                        ))
                      )}
                      <div className="problem-form" style={{ marginTop: 6 }}>
                        <select value={linkGoalId} onChange={(e) => setLinkGoalId(e.target.value)}>
                          <option value="">Цель…</option>
                          {goals.map((g) => (
                            <option key={g.id} value={g.id}>
                              {g.title}
                            </option>
                          ))}
                        </select>
                        <select value={linkType} onChange={(e) => setLinkType(e.target.value)}>
                          {RELATION_TYPES.map((t) => (
                            <option key={t} value={t}>
                              {RELATION_LABELS[t]}
                            </option>
                          ))}
                        </select>
                        <button className="primary" disabled={busy || !linkGoalId} onClick={() => linkToGoal(item.id)}>
                          Связать
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </article>
            ))}
            {visible.length === 0 && <p className="muted empty">Нет записей для выбранного проекта.</p>}
          </div>
        )}
      </section>
    </div>
  );
}
