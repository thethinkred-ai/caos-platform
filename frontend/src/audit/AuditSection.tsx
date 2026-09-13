import type { AuditEvent } from "../types";

export function AuditSection({ auditEvents }: { auditEvents: AuditEvent[] }) {
  return (
    <div className="catalog-layout">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">Audit trail</span>
            <h2>Журнал действий</h2>
          </div>
          <span className="count">{auditEvents.length}</span>
        </div>
        {auditEvents.length === 0 ? (
          <p className="muted empty">Записей в журнале пока нет.</p>
        ) : (
          <div className="problem-list">
            {auditEvents.map((ev) => (
              <article key={ev.id} className="audit-entry">
                <span className="problem-icon">◇</span>
                <div>
                  <h3>{ev.action}</h3>
                  <p>{ev.detail}</p>
                  <small>
                    {ev.entity_type} #{ev.entity_id} · {new Date(ev.created_at).toLocaleString("ru-RU")}
                  </small>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
