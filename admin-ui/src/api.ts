const TOKEN_KEY = "swm-admin-token";

export class AuthError extends Error {}

export const getToken = () => {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? "";
  } catch {
    return "";
  }
};

export const setToken = (token: string) => {
  try {
    sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* storage unavailable: token lasts until reload */
  }
};

export async function login(username: string, password: string) {
  const response = await fetch("/admin/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (response.status === 401) throw new AuthError("Wrong username or password");
  if (!response.ok) throw new Error(`Login failed (${response.status})`);

  setToken((await response.json()).token);
}

export const logout = () => setToken("");

export async function api<T>(
  path: string,
  params: Record<string, string | number | undefined> = {},
): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const qs = query.toString();

  const response = await fetch(`/admin/api${path}${qs ? `?${qs}` : ""}`, {
    headers: { "X-Admin-Token": getToken() },
  });

  if (response.status === 401) throw new AuthError("Invalid admin token");
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);

  return response.json();
}

export type Count = { label: string; count: number };

export type Summary = {
  totals: {
    complaints: number;
    pending: number;
    resolved: number;
    unassigned: number;
    last_24h: number;
    last_7d: number;
    with_photo: number;
    with_gps: number;
    resolution_rate: number;
    avg_resolution_hours: number | null;
    active_officers: number;
    open_conversations: number;
  };
  by_status: Count[];
  by_type: Count[];
  by_local_body: Count[];
  pending_by_local_body: Count[];
  pending_by_block: Count[];
  by_local_body_type: Count[];
  by_language: Count[];
  by_day: Count[];
};

export type Complaint = {
  id: number;
  reference_no: string;
  phone_number: string;
  customer_name: string | null;
  language: string;
  complaint_type: string;
  custom_complaint: string | null;
  local_body_type: string | null;
  local_body_block: string | null;
  local_body: string | null;
  ward_number: string | null;
  location_text: string | null;
  latitude: number | null;
  longitude: number | null;
  photo_url: string | null;
  status: string;
  officer_status: string;
  officer_id: number | null;
  officer_name: string | null;
  created_at: string;
  assigned_at: string | null;
  resolved_at: string | null;
  resolved_photo_url: string | null;
};

export type ComplaintPage = {
  total: number;
  items: Complaint[];
  filters: { local_bodies: string[]; types: string[] };
};

export type Officer = {
  id: number;
  name: string;
  phone: string;
  local_body: string;
  escalation_officer: string | null;
  is_active: boolean;
  created_at: string;
  pending: number;
  resolved: number;
};

export type Conversation = {
  phone_number: string;
  state: string;
  language: string | null;
  data: Record<string, unknown>;
  updated_at: string;
};

export type TableInfo = {
  name: string;
  rows: number;
  columns: {
    name: string;
    type: string;
    nullable: boolean;
    primary_key: boolean;
    unique: boolean;
    indexed: boolean;
    foreign_key: string | null;
  }[];
};

export type TableRows = { columns: string[]; rows: (string | null)[][] };
