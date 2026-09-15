/** Skeleton placeholders (design system rule: skeletons, not spinners).
 * Rendered while section data is loading instead of flashing empty
 * states. */
export function SkeletonRows({ rows = 3, tall = false }: { rows?: number; tall?: boolean }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className={`skeleton${tall ? " skeleton-lg" : ""}`} style={{ width: `${88 - i * 14}%` }} />
      ))}
    </div>
  );
}
