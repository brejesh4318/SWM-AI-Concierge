import { useState } from "react";
import { login, logout } from "./api";
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

function Login({ onDone }: { onDone: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <form
      className="login"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        try {
          await login(username, password);
          onDone(); // re-checks /auth, which now succeeds -> dashboard
        } catch (err) {
          setError(err instanceof Error ? err.message : "Login failed");
        } finally {
          setBusy(false);
        }
      }}
    >
      <h1>Thuyan Admin</h1>
      <p className="muted">Sign in to open the dashboard.</p>
      <input
        autoFocus
        autoComplete="username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        placeholder="Username"
      />
      <input
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
      />
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={busy}>
        {busy ? "Signing in…" : "Sign in"}
      </button>
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
    return <Login onDone={() => setAttempt(attempt + 1)} />;
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
          <button
            onClick={() => {
              logout();
              setAttempt(attempt + 1);
            }}
          >
            Sign out
          </button>
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
