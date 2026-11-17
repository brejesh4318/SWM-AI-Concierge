import { Fragment, useEffect, useState } from "react";
import {
  type ComplaintPage,
  type Conversation,
  type Officer,
  type Summary,
  type TableInfo,
  type TableRows,
} from "./api";
import { BarList, Badge, Card, DayChart, fmtDate, Photo, Stat, Status } from "./components";
import { useApi } from "./hooks";

export type Filters = {
  status: string;
  local_body: string;
  complaint_type: string;
  language: string;
  local_body_type: string;
  local_body_block: string;
  unassigned: string;
  has_photo: string;
  has_gps: string;
  since_hours: string;
  day: string;
};

export const NO_FILTERS: Filters = {
  status: "",
  local_body: "",
  complaint_type: "",
  language: "",
  local_body_type: "",
  local_body_block: "",
  unassigned: "",
  has_photo: "",
  has_gps: "",
  since_hours: "",
  day: "",
};

// Labels for the filters the dropdowns do not cover.
const CHIPS: Partial<Record<keyof Filters, (v: string) => string>> = {
  language: (v) => `Language: ${v}`,
  local_body_type: (v) => `Body type: ${v}`,
  local_body_block: (v) => `Block: ${v}`,
  unassigned: () => "Unassigned",
  has_photo: () => "Has photo",
  has_gps: () => "Has GPS pin",
  since_hours: (v) =>
    Number(v) === 24 ? "Last 24 hours" : `Last ${Number(v) / 24} days`,
  day: (v) => `Filed on ${v}`,
};

export function Overview(props: {
  open: (filters: Partial<Filters>) => void;
  go: (tab: "officers") => void;
}) {
  const { data, error, loading } = useApi<Summary>("/summary");
  const { open, go } = props;

  return (
    <Status loading={loading} error={error}>
      {data && (
        <>
          <div className="stats">
            <Stat label="Total complaints" value={data.totals.complaints} onClick={() => open({})} />
            <Stat
              label="Pending"
              onClick={() => open({ status: "pending" })}
              value={data.totals.pending}
              tone={data.totals.pending ? "warn" : undefined}
            />
            <Stat label="Resolved" value={data.totals.resolved} tone="good" onClick={() => open({ status: "resolved" })} />
            <Stat
              label="Resolution rate"
              onClick={() => open({ status: "resolved" })}
              value={`${data.totals.resolution_rate}%`}
            />
            <Stat
              label="Avg time to resolve"
              onClick={() => open({ status: "resolved" })}
              value={
                data.totals.avg_resolution_hours === null
                  ? "—"
                  : `${data.totals.avg_resolution_hours} h`
              }
            />
            {/* <Stat label="Last 24 hours" value={data.totals.last_24h} onClick={() => open({ since_hours: "24" })} /> */}
            <Stat label="Last 7 days" value={data.totals.last_7d} onClick={() => open({ since_hours: "168" })} />
            {/* <Stat
              label="Unassigned"
              onClick={() => open({ unassigned: "1" })}
              value={data.totals.unassigned}
              hint="No officer for the local body"
              tone={data.totals.unassigned ? "warn" : undefined}
            /> */}
            <Stat label="Active officers" value={data.totals.active_officers} onClick={() => go("officers")} />
            {/* <Stat
              label="Chats in progress"
              value={data.totals.open_conversations}
            /> */}
            {/* <Stat label="With photo" value={data.totals.with_photo} onClick={() => open({ has_photo: "1" })} />
            <Stat label="With GPS pin" value={data.totals.with_gps} onClick={() => open({ has_gps: "1" })} /> */}
          </div>

          <div className="grid">
            <Card title="Complaints per day (last 30 days)">
              <DayChart rows={data.by_day} onSelect={(day) => open({ day })} />
            </Card>
            <Card title="By status">
              <BarList rows={data.by_status} onSelect={(l) => open({ status: l === "resolved" ? "resolved" : "pending" })} />
            </Card>
            <Card title="Top complaint types">
              <BarList rows={data.by_type} onSelect={(l) => open({ complaint_type: l })} />
            </Card>
            <Card title="Pending complaints by local body">
              <BarList rows={data.pending_by_local_body} onSelect={(l) => open({ status: "pending", local_body: l })} />
            </Card>
            <Card title="Pending complaints by block">
              <BarList rows={data.pending_by_block} onSelect={(l) => open({ status: "pending", local_body_block: l })} />
            </Card>
            <Card title="By local body type">
              <BarList rows={data.by_local_body_type} onSelect={(l) => open({ local_body_type: l })} />
            </Card>
            {/* <Card title="By language">
              <BarList rows={data.by_language} onSelect={(l) => open({ language: l })} />
            </Card> */}
          </div>
        </>
      )}
    </Status>
  );
}

const PAGE_SIZE = 10;

export function Complaints({ initial }: { initial: Filters }) {
  const [filters, setFilters] = useState<Filters>(initial);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState<number | null>(null);

  // Debounce typing so each keystroke is not a request.
  useEffect(() => {
    const timer = setTimeout(() => {
      setQuery(search);
      setPage(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, error, loading } = useApi<ComplaintPage>("/complaints", {
    ...filters,
    search: query,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const change =
    (key: keyof Filters) => (e: { target: { value: string } }) => {
      setFilters({ ...filters, [key]: e.target.value });
      setPage(0);
    };

  const clear = (key: keyof Filters) => {
    setFilters({ ...filters, [key]: "" });
    setPage(0);
  };

  const chips = (Object.keys(CHIPS) as (keyof Filters)[]).filter(
    (k) => filters[k],
  );

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <div className="toolbar">
        <input
          placeholder="Search reference, phone, name, location…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select value={filters.status} onChange={change("status")}>
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="resolved">Resolved</option>
        </select>
        <select value={filters.local_body} onChange={change("local_body")}>
          <option value="">All local bodies</option>
          {data?.filters.local_bodies.map((b) => (
            <option key={b}>{b}</option>
          ))}
        </select>
        <select value={filters.complaint_type} onChange={change("complaint_type")}>
          <option value="">All types</option>
          {data?.filters.types.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </div>

      {chips.length > 0 && (
        <div className="toolbar">
          {chips.map((k) => (
            <button key={k} className="chip" onClick={() => clear(k)}>
              {CHIPS[k]!(filters[k])} ✕
            </button>
          ))}
        </div>
      )}

      <Status loading={loading && !data} error={error}>
        {data && (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Reference</th>
                    <th>Filed</th>
                    <th>Type</th>
                    <th>Local body</th>
                    <th>Ward</th>
                    <th>Citizen</th>
                    <th>Officer</th>
                    <th>Status</th>
                    <th>Resolved</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <Fragment key={c.id}>
                      <tr
                        className="clickable"
                        onClick={() => setOpen(open === c.id ? null : c.id)}
                      >
                        <td className="mono">{c.reference_no}</td>
                        <td>{fmtDate(c.created_at)}</td>
                        <td>{c.complaint_type || "—"}</td>
                        <td>{c.local_body ?? "—"}</td>
                        <td>{c.ward_number ?? "—"}</td>
                        <td>
                          {c.customer_name ?? "—"}
                          <div className="muted mono">{c.phone_number}</div>
                        </td>
                        <td>{c.officer_name ?? <span className="muted">Unassigned</span>}</td>
                        <td>
                          <Badge value={c.officer_status} />
                        </td>
                        <td>{fmtDate(c.resolved_at)}</td>
                      </tr>
                      {open === c.id && (
                        <tr className="detail">
                          <td colSpan={9}>
                            <dl>
                              <dt>Details</dt>
                              <dd>{c.custom_complaint ?? "—"}</dd>
                              <dt>Location</dt>
                              <dd>
                                {c.location_text ?? "—"}
                                {c.latitude !== null && c.longitude !== null && (
                                  <>
                                    {" · "}
                                    <a
                                      href={`https://maps.google.com/?q=${c.latitude},${c.longitude}`}
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      {c.latitude}, {c.longitude}
                                    </a>
                                  </>
                                )}
                              </dd>
                              <dt>Local body type / block</dt>
                              <dd>
                                {c.local_body_type ?? "—"} / {c.local_body_block ?? "—"}
                              </dd>
                              <dt>Language</dt>
                              <dd>{c.language}</dd>
                              <dt>Assigned</dt>
                              <dd>{fmtDate(c.assigned_at)}</dd>
                              <dt>Photo</dt>
                              <dd><Photo path={c.photo_url} /></dd>
                              <dt>Resolution photo</dt>
                              <dd><Photo path={c.resolved_photo_url} /></dd>
                            </dl>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                  {!data.items.length && (
                    <tr>
                      <td colSpan={9} className="muted">
                        No complaints match.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="pager">
              <span className="muted">{data.total} complaints</span>
              <button disabled={page === 0} onClick={() => setPage(page - 1)}>
                Previous
              </button>
              <span>
                Page {page + 1} of {pages}
              </span>
              <button disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>
                Next
              </button>
            </div>
          </>
        )}
      </Status>
    </>
  );
}

export function Officers() {
  const { data, error, loading } = useApi<Officer[]>("/officers");
  const [search, setSearch] = useState("");

  const rows = (data ?? []).filter((o) =>
    `${o.name} ${o.local_body} ${o.phone}`.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <Status loading={loading} error={error}>
      <div className="toolbar">
        <input
          placeholder="Search officer, local body, phone…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span className="muted">{rows.length} officers</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Phone</th>
              <th>Local body</th>
              <th>Escalates to</th>
              <th>Pending</th>
              <th>Resolved</th>
              <th>Active</th>
              <th>Added</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((o) => (
              <tr key={o.id}>
                <td>{o.name}</td>
                <td className="mono">{o.phone}</td>
                <td>{o.local_body}</td>
                <td>{o.escalation_officer ?? "—"}</td>
                <td>{o.pending}</td>
                <td>{o.resolved}</td>
                <td>
                  <Badge value={o.is_active ? "active" : "inactive"} />
                </td>
                <td>{fmtDate(o.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Status>
  );
}

export function Conversations() {
  const { data, error, loading, reload } = useApi<Conversation[]>("/conversations");

  return (
    <Status loading={loading} error={error}>
      <div className="toolbar">
        <span className="muted">
          {data?.length ?? 0} citizens part-way through the WhatsApp flow
        </span>
        <button onClick={reload}>Refresh</button>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Phone</th>
              <th>State</th>
              <th>Language</th>
              <th>Collected so far</th>
              <th>Last activity</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((c) => (
              <tr key={c.phone_number}>
                <td className="mono">{c.phone_number}</td>
                <td>
                  <Badge value={c.state} />
                </td>
                <td>{c.language ?? "—"}</td>
                <td className="mono small">{JSON.stringify(c.data)}</td>
                <td>{fmtDate(c.updated_at)}</td>
              </tr>
            ))}
            {!data?.length && (
              <tr>
                <td colSpan={5} className="muted">
                  No open conversations.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Status>
  );
}

function TablePreview({ name }: { name: string }) {
  const { data, error, loading } = useApi<TableRows>(`/tables/${name}`, { limit: 50 });

  return (
    <Status loading={loading} error={error}>
      {data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {data.columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j} className="mono small">
                      {cell ?? <span className="muted">null</span>}
                    </td>
                  ))}
                </tr>
              ))}
              {!data.rows.length && (
                <tr>
                  <td colSpan={data.columns.length} className="muted">
                    Table is empty.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </Status>
  );
}

export function Database() {
  const { data, error, loading } = useApi<TableInfo[]>("/tables");
  const [selected, setSelected] = useState<string | null>(null);
  const [view, setView] = useState<"columns" | "rows">("columns");

  const table = data?.find((t) => t.name === selected) ?? data?.[0];

  return (
    <Status loading={loading} error={error}>
      {data && table && (
        <>
          <div className="stats">
            {data.map((t) => (
              <button
                key={t.name}
                className={`stat table-tile ${t.name === table.name ? "active" : ""}`}
                onClick={() => setSelected(t.name)}
              >
                <div className="stat-label">{t.name}</div>
                <div className="stat-value">{t.rows}</div>
                <div className="stat-hint">
                  rows · {t.columns.length} columns
                </div>
              </button>
            ))}
          </div>

          <div className="toolbar">
            <h3 className="inline">{table.name}</h3>
            <button
              className={view === "columns" ? "active" : ""}
              onClick={() => setView("columns")}
            >
              Columns
            </button>
            <button
              className={view === "rows" ? "active" : ""}
              onClick={() => setView("rows")}
            >
              Latest rows
            </button>
          </div>

          {view === "columns" ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Column</th>
                    <th>Type</th>
                    <th>Nullable</th>
                    <th>Key</th>
                    <th>Unique</th>
                    <th>Indexed</th>
                    <th>References</th>
                  </tr>
                </thead>
                <tbody>
                  {table.columns.map((c) => (
                    <tr key={c.name}>
                      <td className="mono">{c.name}</td>
                      <td className="mono">{c.type}</td>
                      <td>{c.nullable ? "yes" : "no"}</td>
                      <td>{c.primary_key ? "PK" : ""}</td>
                      <td>{c.unique ? "yes" : ""}</td>
                      <td>{c.indexed ? "yes" : ""}</td>
                      <td className="mono">{c.foreign_key ?? ""}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <TablePreview name={table.name} />
          )}
        </>
      )}
    </Status>
  );
}
