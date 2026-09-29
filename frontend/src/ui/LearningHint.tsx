import { useState, type ReactNode } from "react";

/** Embedded learning hint (Step 30): the system explains why it asks
 * what it asks. Collapsed by default so it never clutters. */
export function LearningHint({ children, question = "Почему это спрашивают?" }: { children: ReactNode; question?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: -2 }}>
      <button type="button" className="link-button" onClick={() => setOpen(!open)}>
        {open ? "Скрыть пояснение" : `? ${question}`}
      </button>
      {open && (
        <p className="muted" style={{ fontSize: "var(--font-meta)", lineHeight: 1.55, marginTop: 4 }}>
          {children}
        </p>
      )}
    </div>
  );
}
