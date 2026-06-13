import clsx from "clsx";

const TONES = {
  muted: "bg-raised text-muted border border-line",
  primary: "bg-primary/12 text-primary border border-primary/25",
  accent: "bg-accent/12 text-accent border border-accent/25",
  success: "bg-success/12 text-success border border-success/25",
  warning: "bg-warning/12 text-warning border border-warning/25",
  danger: "bg-danger/12 text-danger border border-danger/25",
};

export default function Badge({ tone = "muted", className, children, ...props }) {
  return (
    <span className={clsx("chip", TONES[tone], className)} {...props}>
      {children}
    </span>
  );
}

/** Maps a pipeline-run / transcript status string to a consistent badge tone. */
export function statusTone(status) {
  switch (status) {
    case "success":
    case "ok":
      return "success";
    case "running":
    case "pending":
      return "accent";
    case "partial":
    case "halted_quota":
    case "unavailable":
      return "warning";
    case "failed":
    case "error":
      return "danger";
    default:
      return "muted";
  }
}
