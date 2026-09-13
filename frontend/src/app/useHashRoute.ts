import { useEffect, useState } from "react";
import type { Section } from "../types";

export type Route = { section: Section; goalId: number | null };

const SECTIONS: Section[] = [
  "overview", "activity", "problems", "goals", "projects", "teams",
  "decisions", "knowledge", "profile", "notifications", "audit", "competences",
];

function parseHash(): Route {
  const hash = window.location.hash.replace(/^#\/?/, "");
  const goalMatch = hash.match(/^goals\/(\d+)$/);
  if (goalMatch) return { section: "goals", goalId: Number(goalMatch[1]) };
  if ((SECTIONS as string[]).includes(hash)) return { section: hash as Section, goalId: null };
  return { section: "overview", goalId: null };
}

/** Hash routing: sections and goals get linkable URLs (#/goals/42).
 * Hash routing needs no server config and keeps the SPA behind any host. */
export function useHashRoute(): [Route, (section: Section, goalId?: number | null) => void] {
  const [route, setRoute] = useState<Route>(parseHash);

  useEffect(() => {
    const onHashChange = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const navigate = (section: Section, goalId: number | null = null) => {
    window.location.hash = goalId !== null ? `#/goals/${goalId}` : `#/${section}`;
  };

  return [route, navigate];
}
