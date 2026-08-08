export type FormatOut = {
  format_id: string;
  ext?: string | null;
  resolution?: string | null;
  fps?: number | null;
  vcodec?: string | null;
  acodec?: string | null;
  filesize?: number | null;
  note?: string | null;
  is_audio: boolean;
};

export type PlaylistEntry = {
  id?: string | null;
  title?: string | null;
  url?: string | null;
  duration?: number | null;
  thumbnail?: string | null;
};

export type ProbeOut = {
  id?: string | null;
  title?: string | null;
  thumbnail?: string | null;
  duration?: number | null;
  extractor?: string | null;
  webpage_url?: string | null;
  is_playlist: boolean;
  formats: FormatOut[];
  entries: PlaylistEntry[];
  used_cookies?: boolean;
};

export type JobOut = {
  id: string;
  url: string;
  title?: string | null;
  thumbnail?: string | null;
  extractor?: string | null;
  format_id?: string | null;
  audio_only: boolean;
  status: string;
  progress: number;
  speed?: string | null;
  eta?: string | null;
  error?: string | null;
  filename?: string | null;
  filesize?: number | null;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
};

export type UserOut = {
  id: string;
  email: string;
  is_admin: boolean;
  created_at: string;
};

export type CookieProfile = {
  id: string;
  name: string;
  created_at: string;
};

export type CookieStatus = {
  has_default: boolean;
  default_path: string;
  profiles: CookieProfile[];
};

export class ApiError extends Error {
  code?: string;
  guides?: string[];
  constructor(message: string, opts?: { code?: string; guides?: string[] }) {
    super(message);
    this.name = "ApiError";
    this.code = opts?.code;
    this.guides = opts?.guides;
  }
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/ws";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("sl_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (!token) localStorage.removeItem("sl_token");
  else localStorage.setItem("sl_token", token);
}

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(init.body instanceof FormData) && !headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    try {
      const data = await res.json();
      const detail = data.detail;
      if (detail && typeof detail === "object" && !Array.isArray(detail)) {
        throw new ApiError(detail.message || "Request failed", {
          code: detail.code,
          guides: detail.guides,
        });
      }
      throw new ApiError(typeof detail === "string" ? detail : "Request failed");
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError("Request failed");
    }
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const client = {
  register: (email: string, password: string) =>
    api<UserOut>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: async (email: string, password: string) => {
    const data = await api<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.access_token);
    return data;
  },
  me: () => api<UserOut>("/auth/me"),
  probe: (url: string, cookie_profile_id?: string) =>
    api<ProbeOut>("/jobs/probe", {
      method: "POST",
      body: JSON.stringify({ url, cookie_profile_id: cookie_profile_id || null }),
    }),
  createJobs: (body: {
    url: string;
    format_id?: string;
    audio_only?: boolean;
    cookie_profile_id?: string;
    playlist_urls?: string[];
  }) => api<JobOut[]>("/jobs", { method: "POST", body: JSON.stringify(body) }),
  listJobs: () => api<JobOut[]>("/jobs"),
  cancelJob: (id: string) => api<JobOut>(`/jobs/${id}/cancel`, { method: "POST" }),
  retryJob: (id: string) => api<JobOut>(`/jobs/${id}/retry`, { method: "POST" }),
  listCookies: () => api<CookieProfile[]>("/cookies"),
  cookieStatus: () => api<CookieStatus>("/cookies/status"),
  uploadCookies: async (name: string, file: File, asDefault = false) => {
    const fd = new FormData();
    fd.append("name", name);
    fd.append("file", file);
    fd.append("as_default", asDefault ? "true" : "false");
    return api<CookieProfile>("/cookies", { method: "POST", body: fd });
  },
  uploadDefaultCookies: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return api<{ ok: boolean; path: string }>("/cookies/default", { method: "POST", body: fd });
  },
  deleteCookie: (id: string) => api<{ ok: boolean }>(`/cookies/${id}`, { method: "DELETE" }),
  fileUrl: (jobId: string) => `${API_URL}/files/${jobId}`,
  wsUrl: (jobId: string, token: string) => `${WS_URL}/jobs/${jobId}?token=${encodeURIComponent(token)}`,
};
