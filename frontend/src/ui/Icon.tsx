/** One icon set for the whole app: 16px, stroke 1.5, currentColor.
 *  Icons take the color of their text role — never their own color. */

type IconName = "check" | "circle" | "alert" | "download" | "edit" | "help";

const PATHS: Record<IconName, React.ReactNode> = {
  check: <path d="M3 8.5l3.2 3.2L13 5" />,
  circle: <circle cx="8" cy="8" r="5.2" />,
  alert: (
    <>
      <path d="M8 2.6l5.4 9.2H2.6L8 2.6z" />
      <path d="M8 6.6v2.6" />
      <path d="M8 11.1h.01" />
    </>
  ),
  download: (
    <>
      <path d="M8 2.8v7" />
      <path d="M5 7l3 3 3-3" />
      <path d="M3 12.6h10" />
    </>
  ),
  edit: (
    <>
      <path d="M10.9 2.9l2.2 2.2L5.6 12.6l-2.9.7.7-2.9 7.5-7.5z" />
    </>
  ),
  help: (
    <>
      <circle cx="8" cy="8" r="5.6" />
      <path d="M6.3 6.2c.2-.9 1-1.5 1.9-1.4 1 .1 1.7.9 1.6 1.8 0 .9-1.3 1.1-1.6 2.1" />
      <path d="M8.1 10.6h.01" />
    </>
  ),
};

export function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ flexShrink: 0, display: "inline-block", verticalAlign: "-2px" }}
    >
      {PATHS[name]}
    </svg>
  );
}
