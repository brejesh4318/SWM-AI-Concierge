import type { ReactNode } from "react";
import { useApi } from "./hooks";
import type { Count } from "./api";

export const fmtDate = (value: string | null) =>
  value
    ? new Date(value).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "—";

export function Stat(props: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "warn" | "good";
  onClick?: () => void;
}) {
  const body = (
    <>
      <div className="stat-label">{props.label}</div>
      <div className="stat-value">{props.value}</div>
      {props.hint && <div className="stat-hint">{props.hint}</div>}
    </>
  );

  return props.onClick ? (
    <button
      className={`stat clickable ${props.tone ?? ""}`}
      onClick={props.onClick}
    >
      {body}
    </button>
  ) : (
    <div className={`stat ${props.tone ?? ""}`}>{body}</div>
  );
}

export function Badge({ value }: { value: string }) {
  return <span className={`badge badge-${value}`}>{value}</span>;
}

export function Card(props: { title: string; children: ReactNode }) {
  return (
    <section className="card">
      <h3>{props.title}</h3>
      {props.children}
    </section>
  );
}

/** Horizontal bars, one per row, scaled to the largest count. */
export function BarList({
  rows,
  onSelect,
}: {
  rows: Count[];
  onSelect?: (label: string) => void;
}) {
  if (!rows.length) return <p className="muted">No data yet.</p>;
  const max = Math.max(...rows.map((r) => r.count));
  return (
    <ul className="bars">
      {rows.map((r) => (
        <li
          key={r.label}
          className={onSelect && r.label !== "Unknown" ? "clickable" : ""}
          onClick={
            onSelect && r.label !== "Unknown"
              ? () => onSelect(r.label)
              : undefined
          }
        >
          <span className="bar-label" title={r.label}>
            {r.label}
          </span>
          <span className="bar-track">
            <span
              className="bar-fill"
              style={{ width: `${(r.count / max) * 100}%` }}
            />
          </span>
          <span className="bar-count">{r.count}</span>
        </li>
      ))}
    </ul>
  );
}

/** Daily complaint counts as vertical columns. */
export function DayChart({
  rows,
  onSelect,
}: {
  rows: Count[];
  onSelect?: (day: string) => void;
}) {
  if (!rows.length) return <p className="muted">No complaints in the last 30 days.</p>;
  const max = Math.max(...rows.map((r) => r.count));
  return (
    <div className="days">
      {rows.map((r) => (
        <div
          key={r.label}
          className={`day ${onSelect ? "clickable" : ""}`}
          onClick={onSelect ? () => onSelect(r.label) : undefined}
          title={`${r.label}: ${r.count}`}
          style={{ height: `${Math.max((r.count / max) * 100, 4)}%` }}
        />
      ))}
    </div>
  );
}

export function Status(props: {
  loading: boolean;
  error: string | null;
  children: ReactNode;
}) {
  if (props.error) return <p className="error">Could not load: {props.error}</p>;
  if (props.loading) return <p className="muted">Loading…</p>;
  return <>{props.children}</>;
}

/** A stored photo, shown via a short-lived signed URL. */
export function Photo({ path }: { path: string | null }) {
  // A bare WhatsApp media id (no folder) means the upload to storage failed.
  const stored = !!path && path.includes("/");
  const { data, error, loading } = useApi<{ url: string }>(
    stored ? "/photo-url" : "/auth",
    stored ? { path: path! } : {},
  );

  if (!path) return <>—</>;
  if (!stored) return <span className="muted mono">{path} (not in storage)</span>;
  if (loading) return <span className="muted">Loading photo…</span>;
  if (error || !data || !("url" in data))
    return <span className="error">Photo unavailable</span>;

  return (
    <a href={data.url} target="_blank" rel="noreferrer">
      <img className="photo" src={data.url} alt={path} loading="lazy" />
    </a>
  );
}
