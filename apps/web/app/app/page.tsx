"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  CookieProfile,
  FormatOut,
  JobOut,
  ProbeOut,
  UserOut,
  client,
  getToken,
  setToken,
} from "@/lib/api";

function formatBytes(n?: number | null) {
  if (!n) return "";
  const units = ["B", "KB", "MB", "GB"];
  let v = n;
  let i = 0;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function statusColor(status: string) {
  switch (status) {
    case "completed":
      return "text-lime";
    case "failed":
      return "text-red-400";
    case "running":
      return "text-sky-300";
    case "cancelled":
      return "text-mist";
    default:
      return "text-amber-300";
  }
}

export default function AppPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserOut | null>(null);
  const [url, setUrl] = useState("");
  const [probe, setProbe] = useState<ProbeOut | null>(null);
  const [selectedFormat, setSelectedFormat] = useState<string>("");
  const [audioOnly, setAudioOnly] = useState(false);
  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [cookies, setCookies] = useState<CookieProfile[]>([]);
  const [cookieId, setCookieId] = useState("");
  const [selectedEntries, setSelectedEntries] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);

  const loadJobs = useCallback(async () => {
    const list = await client.listJobs();
    setJobs(list);
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const me = await client.me();
        setUser(me);
        const [j, c] = await Promise.all([client.listJobs(), client.listCookies()]);
        setJobs(j);
        setCookies(c);
      } catch {
        setToken(null);
        router.replace("/login");
      }
    })();
  }, [router]);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const active = jobs.filter((j) => ["queued", "running", "pending"].includes(j.status));
    const sockets: WebSocket[] = [];
    for (const job of active.slice(0, 8)) {
      const ws = new WebSocket(client.wsUrl(job.id, token));
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          setJobs((prev) =>
            prev.map((j) =>
              j.id === job.id
                ? {
                    ...j,
                    status: data.status ?? j.status,
                    progress: data.progress ?? j.progress,
                    speed: data.speed ?? j.speed,
                    eta: data.eta ?? j.eta,
                    error: data.error ?? j.error,
                    filename: data.filename ?? j.filename,
                    title: data.title ?? j.title,
                  }
                : j,
            ),
          );
        } catch {
          /* ignore */
        }
      };
      sockets.push(ws);
    }
    return () => sockets.forEach((s) => s.close());
  }, [jobs.map((j) => `${j.id}:${j.status}`).join("|")]);

  const videoFormats = useMemo(
    () => (probe?.formats || []).filter((f) => !f.is_audio && (f.resolution || f.vcodec)),
    [probe],
  );
  const audioFormats = useMemo(() => (probe?.formats || []).filter((f) => f.is_audio), [probe]);

  async function onProbe(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    setProbe(null);
    try {
      const data = await client.probe(url, cookieId || undefined);
      setProbe(data);
      if (data.is_playlist) {
        const map: Record<string, boolean> = {};
        data.entries.forEach((entry, idx) => {
          const key = entry.url || entry.id || String(idx);
          map[key] = true;
        });
        setSelectedEntries(map);
      } else {
        const best =
          data.formats.find((f) => !f.is_audio && (f.note?.includes("1080") || f.resolution?.includes("1080"))) ||
          data.formats.find((f) => !f.is_audio) ||
          data.formats[0];
        setSelectedFormat(best?.format_id || "");
      }
      setMessage("Metadata loaded");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Probe failed");
    } finally {
      setBusy(false);
    }
  }

  async function onEnqueue() {
    if (!probe) return;
    setBusy(true);
    setError(null);
    try {
      if (probe.is_playlist) {
        const playlist_urls = (probe.entries || [])
          .filter((entry, idx) => selectedEntries[entry.url || entry.id || String(idx)])
          .map((entry) => entry.url)
          .filter(Boolean) as string[];
        if (!playlist_urls.length) throw new Error("Select at least one playlist item");
        await client.createJobs({
          url,
          audio_only: audioOnly,
          format_id: selectedFormat || undefined,
          cookie_profile_id: cookieId || undefined,
          playlist_urls,
        });
      } else {
        await client.createJobs({
          url,
          audio_only: audioOnly,
          format_id: selectedFormat || undefined,
          cookie_profile_id: cookieId || undefined,
        });
      }
      setMessage("Queued");
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enqueue failed");
    } finally {
      setBusy(false);
    }
  }

  async function onUploadCookies(file: File | null) {
    if (!file) return;
    setBusy(true);
    try {
      await client.uploadCookies(file.name.replace(/\.[^.]+$/, "") || "cookies", file);
      setCookies(await client.listCookies());
      setMessage("Cookies uploaded");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Cookie upload failed");
    } finally {
      setBusy(false);
    }
  }

  function FormatCard({ f, active, onClick }: { f: FormatOut; active: boolean; onClick: () => void }) {
    return (
      <motion.button
        type="button"
        layout
        whileHover={{ y: -2 }}
        onClick={onClick}
        className={`rounded-xl border px-3 py-3 text-left transition ${
          active ? "border-lime bg-lime/10 shadow-glow" : "border-line bg-ink/60 hover:border-mist/50"
        }`}
      >
        <div className="text-sm font-medium text-paper">{f.resolution || f.note || f.ext || f.format_id}</div>
        <div className="mt-1 text-xs text-mist">
          {f.ext || "?"} · {f.format_id}
          {f.filesize ? ` · ${formatBytes(f.filesize)}` : ""}
        </div>
      </motion.button>
    );
  }

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center text-mist">
        Loading StreamLine…
      </main>
    );
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-8">
      <header className="mb-10 flex flex-wrap items-center justify-between gap-4">
        <Link href="/" className="font-display text-2xl font-bold text-paper">
          Stream<span className="text-lime">Line</span>
        </Link>
        <div className="flex items-center gap-4 text-sm text-mist">
          <span>{user.email}</span>
          <button
            onClick={() => {
              setToken(null);
              router.push("/");
            }}
            className="rounded-full border border-line px-3 py-1.5 text-paper hover:border-lime/50"
          >
            Sign out
          </button>
        </div>
      </header>

      <section className="grid gap-8 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <motion.form
            onSubmit={onProbe}
            animate={{ scale: focused ? 1.01 : 1 }}
            className={`rounded-3xl border bg-panel/70 p-2 backdrop-blur transition ${
              focused ? "border-lime/60 shadow-glow" : "border-line"
            }`}
          >
            <div className="flex flex-col gap-2 sm:flex-row">
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setFocused(false)}
                placeholder="Paste media URL…"
                className="flex-1 rounded-2xl bg-ink px-5 py-4 text-base outline-none"
                required
              />
              <button
                disabled={busy}
                className="rounded-2xl bg-lime px-6 py-4 font-semibold text-ink transition hover:brightness-110 disabled:opacity-60"
              >
                {busy ? "Working…" : "Inspect"}
              </button>
            </div>
          </motion.form>

          <div className="mt-4 flex flex-wrap items-center gap-3 text-sm">
            <label className="flex items-center gap-2 text-mist">
              Cookies
              <select
                value={cookieId}
                onChange={(e) => setCookieId(e.target.value)}
                className="rounded-lg border border-line bg-ink px-2 py-1 text-paper"
              >
                <option value="">None</option>
                {cookies.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="cursor-pointer rounded-lg border border-dashed border-line px-3 py-1 text-mist hover:border-lime/40 hover:text-paper">
              Upload cookies.txt
              <input
                type="file"
                accept=".txt"
                className="hidden"
                onChange={(e) => onUploadCookies(e.target.files?.[0] || null)}
              />
            </label>
            <label className="flex items-center gap-2 text-mist">
              <input type="checkbox" checked={audioOnly} onChange={(e) => setAudioOnly(e.target.checked)} />
              Audio only (mp3)
            </label>
          </div>

          <AnimatePresence>
            {(message || error) && (
              <motion.p
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className={`mt-3 text-sm ${error ? "text-red-400" : "text-lime"}`}
              >
                {error || message}
              </motion.p>
            )}
          </AnimatePresence>

          <AnimatePresence mode="wait">
            {probe && (
              <motion.div
                key={probe.id || probe.title || "probe"}
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="mt-8 overflow-hidden rounded-3xl border border-line bg-panel/60"
              >
                <div className="flex flex-col gap-4 p-5 md:flex-row">
                  {probe.thumbnail && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={probe.thumbnail}
                      alt=""
                      className="h-36 w-full rounded-2xl object-cover md:h-40 md:w-64"
                    />
                  )}
                  <div className="flex-1">
                    <p className="text-xs uppercase tracking-[0.18em] text-mist">{probe.extractor || "source"}</p>
                    <h2 className="mt-2 font-display text-2xl font-semibold leading-tight">{probe.title}</h2>
                    {probe.duration ? (
                      <p className="mt-2 text-sm text-mist">{Math.round(probe.duration / 60)} min</p>
                    ) : null}
                  </div>
                </div>

                {!probe.is_playlist && (
                  <div className="border-t border-line p-5">
                    <p className="mb-3 text-sm text-mist">{audioOnly ? "Audio formats" : "Video formats"}</p>
                    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {(audioOnly ? audioFormats : videoFormats).slice(0, 18).map((f, i) => (
                        <motion.div key={f.format_id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
                          <FormatCard
                            f={f}
                            active={selectedFormat === f.format_id}
                            onClick={() => setSelectedFormat(f.format_id)}
                          />
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )}

                {probe.is_playlist && (
                  <div className="max-h-72 space-y-2 overflow-y-auto border-t border-line p-5">
                    {probe.entries.map((entry, idx) => {
                      const key = entry.url || entry.id || String(idx);
                      return (
                        <label key={key} className="flex items-center gap-3 rounded-xl border border-line bg-ink/40 px-3 py-2">
                          <input
                            type="checkbox"
                            checked={!!selectedEntries[key]}
                            onChange={(e) =>
                              setSelectedEntries((prev) => ({ ...prev, [key]: e.target.checked }))
                            }
                          />
                          <span className="truncate text-sm">{entry.title || entry.url || key}</span>
                        </label>
                      );
                    })}
                  </div>
                )}

                <div className="border-t border-line p-5">
                  <button
                    disabled={busy}
                    onClick={onEnqueue}
                    className="rounded-2xl bg-paper px-6 py-3 font-semibold text-ink transition hover:bg-lime disabled:opacity-60"
                  >
                    Add to queue
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <aside>
          <div className="sticky top-6 rounded-3xl border border-line bg-panel/70 p-5 backdrop-blur">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-display text-xl font-semibold">Queue</h3>
              <button onClick={() => loadJobs()} className="text-xs text-mist hover:text-paper">
                Refresh
              </button>
            </div>
            <div className="space-y-3">
              {jobs.length === 0 && <p className="text-sm text-mist">No jobs yet.</p>}
              {jobs.map((job) => (
                <motion.div
                  layout
                  key={job.id}
                  className="rounded-2xl border border-line bg-ink/50 p-3"
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{job.title || job.url}</p>
                      <p className={`mt-1 text-xs ${statusColor(job.status)}`}>
                        {job.status}
                        {job.speed ? ` · ${job.speed}` : ""}
                        {job.eta ? ` · ETA ${job.eta}` : ""}
                      </p>
                    </div>
                    {job.status === "completed" && (
                      <a
                        href={client.fileUrl(job.id)}
                        className="shrink-0 text-xs text-lime underline"
                        onClick={(e) => {
                          e.preventDefault();
                          const token = getToken();
                          fetch(client.fileUrl(job.id), {
                            headers: token ? { Authorization: `Bearer ${token}` } : {},
                          })
                            .then((r) => r.blob())
                            .then((blob) => {
                              const a = document.createElement("a");
                              a.href = URL.createObjectURL(blob);
                              a.download = job.filename || "download";
                              a.click();
                            });
                        }}
                      >
                        Download
                      </a>
                    )}
                  </div>
                  <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-line">
                    <motion.div
                      className="h-full rounded-full bg-lime"
                      animate={{ width: `${Math.max(2, job.progress)}%` }}
                      transition={{ type: "spring", stiffness: 120, damping: 20 }}
                    />
                  </div>
                  <div className="mt-2 flex gap-2 text-xs">
                    {["queued", "running"].includes(job.status) && (
                      <button className="text-mist hover:text-paper" onClick={() => client.cancelJob(job.id).then(loadJobs)}>
                        Cancel
                      </button>
                    )}
                    {["failed", "cancelled"].includes(job.status) && (
                      <button className="text-mist hover:text-paper" onClick={() => client.retryJob(job.id).then(loadJobs)}>
                        Retry
                      </button>
                    )}
                    {job.error && <span className="truncate text-red-400">{job.error}</span>}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </aside>
      </section>
    </main>
  );
}
