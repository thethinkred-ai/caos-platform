import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { request } from "../api/client";

/**
 * Точка обратной связи + автоматическая подсказка застрявшему пользователю.
 *
 * Логика: сервер сам определяет, на каком шаге человек остановился (эндпоинт
 * /feedback/stuck), и возвращает готовый вопрос с вариантами ответа. Если
 * человек «застрял» — окно открывается само, один раз в сутки, без поиска
 * формы обратной связи. Кнопка «Обратная связь» доступна всегда.
 */

type StuckState = {
  stuck: boolean;
  stage: string;
  hours_registered: number;
  message: string;
  checklist: string[];
  objects: Record<string, number>;
};

const ACCENT = "var(--primary)";

function currentPage(): string {
  const hash = window.location.hash.replace(/^#\/?/, "");
  return (hash.split("/")[0] || "overview").slice(0, 64);
}

export function FeedbackWidget({ userId }: { userId: number }) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<StuckState | null>(null);
  const [text, setText] = useState("");
  const [contact, setContact] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const dismissKey = `caos_feedback_dismissed_${userId}`;

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const result = await request<StuckState>("/feedback/stuck");
        if (!alive) return;
        setState(result);
        if (result.stuck && !localStorage.getItem(dismissKey)) setOpen(true);
      } catch {
        /* подсказка не критична: сама кнопка остаётся доступной */
      }
    })();
    return () => {
      alive = false;
    };
  }, [dismissKey]);

  const close = (remember: boolean) => {
    if (remember) localStorage.setItem(dismissKey, "1");
    setOpen(false);
    setSent(false);
    setError("");
  };

  const addChip = (chip: string) => {
    setText((prev) => (prev.trim() ? `${prev.trim()}\n— ${chip}` : `— ${chip}`));
  };

  const submit = async () => {
    if (text.trim().length < 3) {
      setError("Напишите хотя бы пару слов — этого достаточно.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await request("/feedback", {
        method: "POST",
        body: JSON.stringify({
          message: text.trim().slice(0, 4000),
          page: currentPage(),
          kind: state?.stuck ? "stuck" : "idea",
          contact: contact.trim(),
        }),
      });
      setSent(true);
      localStorage.setItem(dismissKey, "1");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Не удалось отправить");
    } finally {
      setBusy(false);
    }
  };

  const title = state?.stuck ? "Что-то не получилось?" : "Обратная связь";

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        title="Написать команде: что не так и что исправить"
        style={{
          position: "fixed",
          right: 18,
          bottom: 18,
          zIndex: 60,
          borderRadius: 999,
          border: "1px solid " + ACCENT,
          background: "var(--surface)",
          color: ACCENT,
          fontWeight: 600,
          fontSize: 13,
          padding: "9px 14px",
          cursor: "pointer",
          boxShadow: "0 6px 18px rgba(0,0,0,.12)",
        }}
      >
        Обратная связь
      </button>
    );
  }

  return (
    <>
      <div
        onClick={() => close(false)}
        style={{ position: "fixed", inset: 0, background: "rgba(12,14,18,.45)", zIndex: 70 }}
      />
      <div
        role="dialog"
        aria-modal="true"
        style={{
          position: "fixed",
          right: 18,
          bottom: 18,
          width: "min(440px, calc(100vw - 36px))",
          maxHeight: "calc(100vh - 36px)",
          overflowY: "auto",
          background: "var(--surface)",
          borderRadius: 14,
          border: "1px solid #e3e6ea",
          boxShadow: "0 18px 48px rgba(0,0,0,.22)",
          zIndex: 80,
          padding: 18,
        }}
      >
        {sent ? (
          <div>
            <h3 style={{ margin: "0 0 8px", fontSize: 16 }}>Спасибо, записали</h3>
            <p style={{ margin: "0 0 14px", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5 }}>
              Сообщение ушло рабочей команде. Если нужен ответ лично — оставьте контакт в
              следующем сообщении или напишите на thethinkred@gmail.com.
            </p>
            <button type="button" onClick={() => close(true)} style={btnPrimary}>
              Закрыть
            </button>
          </div>
        ) : (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", gap: 12 }}>
              <h3 style={{ margin: "0 0 6px", fontSize: 16 }}>{title}</h3>
              <button
                type="button"
                onClick={() => close(true)}
                aria-label="Закрыть"
                style={{ border: "none", background: "none", fontSize: 18, lineHeight: 1, cursor: "pointer", color: "var(--text-muted)" }}
              >
                ×
              </button>
            </div>

            <p style={{ margin: "0 0 12px", fontSize: 13, color: "var(--text)", lineHeight: 1.55 }}>
              {state?.stuck
                ? state.message
                : "Напишите, что не работает или чего не хватает. Сообщение читает рабочая команда, а не бот."}
            </p>

            {state?.stuck && state.checklist.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
                {state.checklist.map((chip) => (
                  <button key={chip} type="button" onClick={() => addChip(chip)} style={chipStyle}>
                    {chip}
                  </button>
                ))}
              </div>
            )}

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Что вы хотели сделать и где остановились? Что исправить?"
              rows={4}
              style={{
                width: "100%",
                boxSizing: "border-box",
                resize: "vertical",
                borderRadius: 10,
                border: "1px solid #d6dae0",
                padding: 10,
                fontSize: 13,
                fontFamily: "inherit",
              }}
            />

            <input
              value={contact}
              onChange={(e) => setContact(e.target.value)}
              placeholder="Контакт для ответа (необязательно)"
              style={{
                width: "100%",
                boxSizing: "border-box",
                marginTop: 8,
                borderRadius: 10,
                border: "1px solid #d6dae0",
                padding: "9px 10px",
                fontSize: 13,
                fontFamily: "inherit",
              }}
            />

            <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
              Страница: {currentPage()}
              {state?.stuck ? " · шаг: " + state.stage : ""}
            </div>

            {error && (
              <div style={{ marginTop: 8, fontSize: 12, color: ACCENT }}>{error}</div>
            )}

            <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
              <button type="button" onClick={() => void submit()} disabled={busy} style={btnPrimary}>
                {busy ? "Отправляем…" : "Отправить"}
              </button>
              <button type="button" onClick={() => close(true)} style={btnGhost}>
                Позже
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

const btnPrimary: CSSProperties = {
  flex: 1,
  border: "none",
  borderRadius: 10,
  background: ACCENT,
  color: "var(--on-primary)",
  fontWeight: 600,
  fontSize: 13,
  padding: "10px 14px",
  cursor: "pointer",
};

const btnGhost: CSSProperties = {
  border: "1px solid #d6dae0",
  borderRadius: 10,
  background: "var(--surface)",
  color: "var(--text)",
  fontSize: 13,
  padding: "10px 14px",
  cursor: "pointer",
};

const chipStyle: CSSProperties = {
  border: "1px solid #d6dae0",
  borderRadius: 999,
  background: "#f7f8fa",
  color: "var(--text)",
  fontSize: 12,
  padding: "5px 10px",
  cursor: "pointer",
};
