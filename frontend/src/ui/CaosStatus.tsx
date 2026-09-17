import { statusLabel } from "../labels";

const GREEN = new Set(["active", "verified", "accepted", "fulfilled", "completed", "qualified", "addressed"]);
const RED = new Set(["rejected", "failed", "cancelled", "disputed"]);
const BLUE = new Set(["in_progress", "proposed", "under_review", "in_discussion", "voting", "reported", "under_verification"]);
const YELLOW = new Set(["suspended", "achieved", "deferred", "acknowledged", "open", "planned"]);
// draft, closed, abandoned, superseded, withdrawn, left -> gray (default)

function colorFor(status: string): "green" | "red" | "blue" | "yellow" | "gray" {
  const s = status.toLowerCase();
  if (GREEN.has(s)) return "green";
  if (RED.has(s)) return "red";
  if (BLUE.has(s)) return "blue";
  if (YELLOW.has(s)) return "yellow";
  return "gray";
}

/** Semantic status badge (Step 35): the color carries meaning and the
 * text is always Russian (domain vocabulary lives in labels.ts). */
export function CaosStatus({ status, label, context }: { status: string; label?: string; context?: string }) {
  return <span className={`caos-status status-${colorFor(status)}`}>{label ?? statusLabel(status, context)}</span>;
}
