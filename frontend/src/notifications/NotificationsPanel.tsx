import { useState } from "react";
import { TARGET_LABELS } from "../labels";
import type { Notification, Section } from "../types";

const TARGET_SECTIONS: Record<string, Section> = {
  goal: "goals",
  decision: "decisions",
  commitment: "activity",
  task: "projects",
  project: "projects",
};

/** Semantic notifications (Track F): each item links to where the action
 * lives, with an unread filter. */
export function NotificationsPanel({
  notifications,
  onOpenGoal,
  onGoSection,
  onMarkRead,
  onMarkAllRead,
}: {
  notifications: Notification[];
  onOpenGoal: (goalId: number) => void;
  onGoSection: (section: Section) => void;
  onMarkRead: (id: number) => void;
  onMarkAllRead: () => void;
}) {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const unreadCount = notifications.filter((n) => !n.is_read).length;
  const visible = unreadOnly ? notifications.filter((n) => !n.is_read) : notifications;

  const open = (n: Notification) => {
    if (n.entity_type === "goal" || n.entity_type === "result") onGoSection("goals");
    else onGoSection(TARGET_SECTIONS[n.entity_type] ?? "overview");
  };

  return (
    <div className="catalog-layout">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="eyebrow">In-app</span>
            <h2>Уведомления</h2>
          </div>
          <div className="event-buttons">
            <button className={unreadOnly ? "" : "primary"} onClick={() => setUnreadOnly(false)}>
              Все
            </button>
            <button className={unreadOnly ? "primary" : ""} onClick={() => setUnreadOnly(true)}>
              Непрочитанные {unreadCount > 0 && `(${unreadCount})`}
            </button>
            {unreadCount > 0 && (
              <button className="link-button" onClick={onMarkAllRead}>
                Отметить все
              </button>
            )}
          </div>
        </div>
        {notifications.length === 0 ? (
          <p className="muted empty">Уведомлений пока нет.</p>
        ) : visible.length === 0 ? (
          <p className="muted empty">Непрочитанных нет — всё изучено.</p>
        ) : (
          <div className="problem-list">
            {visible.map((n) => {
              const navigable = n.entity_type in TARGET_SECTIONS || n.entity_type === "result";
              return (
                <article key={n.id} className={n.is_read ? "read" : ""}>
                  <span className="problem-icon">{n.is_read ? "·" : "!"}</span>
                  <div>
                    <h3>{navigable ? (
                      <button className="link-button" onClick={() => open(n)}>
                        {n.message}
                      </button>
                    ) : (
                      n.message
                    )}</h3>
                    <small>
                      {TARGET_LABELS[n.entity_type] ?? n.entity_type} №{n.entity_id} · {new Date(n.created_at).toLocaleString("ru-RU")}
                    </small>
                    {!n.is_read && (
                      <button className="link-button" onClick={() => onMarkRead(n.id)}>
                        Отметить прочитанным
                      </button>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
