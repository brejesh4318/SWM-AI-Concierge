import { useState } from "react";
import { setToken } from "./api";
import { useApi } from "./hooks";
import {
  Complaints,
  NO_FILTERS,
  Officers,
  Overview,
  type Filters,
} from "./pages";

const TABS = [
  ["overview", "Overview"],
  ["complaints", "Complaints"],
  ["officers", "Officers"],

] as const;

type Tab = (typeof TABS)[number][0];

function Login({ onDone, rejected }: { onDone: () => void; rejected: boolean }) {
  const [value, setValue] = useState("");

  return (
    <form
      className="login"
      onSubmit={(e) => {
        e.preventDefault();
        setToken(value);
        onDone();
      }}
    >
      <h1>Thuyan Admin</h1>
      <p className="muted">Enter the admin token (ADMIN_TOKEN in the server .env).</p>
      <input
        type="password"
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Admin token"
      />
      {rejected && <p className="error">That token was not accepted.</p>}
      <button type="submit">Sign in</button>
    </form>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("overview");
  // Bumping the key remounts Complaints so it starts from the new filters.
  const [complaints, setComplaints] = useState({ key: 0, filters: NO_FILTERS });
  const [attempt, setAttempt] = useState(0);
  const auth = useApi<{ ok: boolean }>("/auth", { attempt });

  if (auth.unauthorized) {
    return <Login rejected={attempt > 0} onDone={() => setAttempt(attempt + 1)} />;
  }

  const openComplaints = (filters: Partial<Filters>) => {
    setComplaints((c) => ({
      key: c.key + 1,
      filters: { ...NO_FILTERS, ...filters },
    }));
    setTab("complaints");
  };

  const pages: Record<Tab, JSX.Element> = {
    overview: <Overview open={openComplaints} go={setTab} />,
    complaints: (
      <Complaints key={complaints.key} initial={complaints.filters} />
    ),
    officers: <Officers />,
 
  };

  return (
    <div className="shell">
      <header>
        <h1>Thuyan · Solid Waste Admin</h1>
        <nav>
          {TABS.map(([id, label]) => (
            <button
              key={id}
              className={id === tab ? "active" : ""}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {auth.error && !auth.unauthorized ? (
          <p className="error">
            Cannot reach the API ({auth.error}). Is uvicorn running on port 8000?
          </p>
        ) : (
          pages[tab]
        )}
      </main>
    </div>
  );
}
