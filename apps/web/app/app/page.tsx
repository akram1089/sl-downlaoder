"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ApiError,
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
  const [selectedPreset, setSelectedPreset] = useState<string>("1080");
  const [audioOnly, setAudioOnly] = useState(false);
  const [jobs, setJobs] = useState<JobOut[]>([]);
  const [cookies, setCookies] = useState<CookieProfile[]>([]);
  const [cookieId, setCookieId] = useState("");
  const [selectedEntries, setSelectedEntries] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [needsCookies, setNeedsCookies] = useState(false);
  const [hasServerCookies, setHasServerCookies] = useState(false);
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
        const [j, c, status] = await Promise.all([
          client.listJobs(),
          client.listCookies(),
          client.cookieStatus(),
        ]);
        setJobs(j);
        setCookies(c);
        setHasServerCookies(status.has_default);
        if (c[0]) setCookieId(c[0].id);
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
    () =>
      (probe?.formats || []).filter(
        (f) =>
          !f.is_audio &&
          f.ext !== "mhtml" &&
          !String(f.format_id).startsWith("sb") &&
          (f.height || f.resolution || f.vcodec),
      ),
    [probe],
  );
  const audioFormats = useMemo(() => (probe?.formats || []).filter((f) => f.is_audio), [probe]);
  const presets = probe?.presets || [];

  async function onProbe(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setNeedsCookies(false);
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
          data.formats.find((f) => !f.is_audio && (f.height || 0) >= 1080) ||
          data.formats.find((f) => !f.is_audio && (f.height || 0) >= 720) ||
          data.formats.find((f) => !f.is_audio) ||
          data.formats[0];
        setSelectedFormat(best?.format_id || "");
        setSelectedPreset((data.max_height || 0) >= 2160 ? "2160" : "1080");
      }
      const heightNote = data.max_height ? ` · up to ${data.max_height}p listed` : "";
      setMessage(
        (data.used_cookies ? "Metadata loaded (cookies)" : "Metadata loaded") + heightNote,
      );    } catch (err) {
      if (err instanceof ApiError && err.code === "youtube_cookies_required") {
        setNeedsCookies(true);
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Probe failed");
      }
    } finally {
      setBusy(false);
    }
  }

  async function onEnqueue() {
    if (!probe) return;
    setBusy(true);
    setError(null);
    try {
      const preset = presets.find((p) => p.id === selectedPreset);
      const format_id = audioOnly
        ? selectedFormat || undefined
        : preset?.format || selectedFormat || undefined;

      if (probe.is_playlist) {
        const playlist_urls = (probe.entries || [])
          .filter((entry, idx) => selectedEntries[entry.url || entry.id || String(idx)])
          .map((entry) => entry.url)
          .filter(Boolean) as string[];
        if (!playlist_urls.length) throw new Error("Select at least one playlist item");
        await client.createJobs({
          url,
          audio_only: audioOnly,
          format_id,
          cookie_profile_id: cookieId || undefined,
          playlist_urls,
        });
      } else {
        await client.createJobs({
          url,
          audio_only: audioOnly,
          format_id,
          cookie_profile_id: cookieId || undefined,
        });
      }
      setMessage(`Queued${preset && !audioOnly ? ` · ${preset.label}` : ""}`);
      await loadJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Enqueue failed");
    } finally {
      setBusy(false);
    }
  }

  async function onUploadCookies(file: File | null, asDefault = false) {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      if (asDefault) {
        await client.uploadDefaultCookies(file);
        setHasServerCookies(true);
        setMessage("Server default YouTube cookies saved");
      } else {
        const profile = await client.uploadCookies(file.name.replace(/\.[^.]+$/, "") || "youtube", file, false);
        const list = await client.listCookies();
        setCookies(list);
        setCookieId(profile.id);
        setMessage("Cookies uploaded — select them and Inspect again");
      }
      setNeedsCookies(false);
      const status = await client.cookieStatus();
      setHasServerCookies(status.has_default);
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
                <option value="">{hasServerCookies ? "Server default" : "None"}</option>
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
                onChange={(e) => onUploadCookies(e.target.files?.[0] || null, false)}
              />
            </label>
            {user.is_admin && (
              <label className="cursor-pointer rounded-lg border border-dashed border-lime/40 px-3 py-1 text-lime/90 hover:bg-lime/10">
                Set server default
                <input
                  type="file"
                  accept=".txt"
                  className="hidden"
                  onChange={(e) => onUploadCookies(e.target.files?.[0] || null, true)}
                />
              </label>
            )}
            <label className="flex items-center gap-2 text-mist">
              <input type="checkbox" checked={audioOnly} onChange={(e) => setAudioOnly(e.target.checked)} />
              Audio only (mp3)
            </label>
            <span className={`text-xs ${hasServerCookies ? "text-lime" : "text-mist"}`}>
              {hasServerCookies ? "Server cookies ready" : "No server cookies yet"}
            </span>
          </div>

          <AnimatePresence>
            {needsCookies && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mt-4 rounded-2xl border border-amber-400/40 bg-amber-400/10 p-4 text-sm text-paper"
              >
                <p className="font-semibold text-amber-200">YouTube bot check — cookies required</p>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-mist">
                  <li>Install a cookie export extension (e.g. “Get cookies.txt LOCALLY”).</li>
                  <li>Open youtube.com while logged in, export Netscape cookies.txt.</li>
                  <li>Upload that file here, select it, then Inspect again.</li>
                  <li>Admins can also set a shared server default for the whole VPS.</li>
                </ol>
                <p className="mt-3 text-xs text-mist">
                  Engine:{" "}
                  <a
                    className="underline hover:text-paper"
                    href="https://github.com/akram1089/yt-dlp"
                    target="_blank"
                    rel="noreferrer"
                  >
                    akram1089/yt-dlp
                  </a>{" "}
                  ·{" "}
                  <a
                    className="underline hover:text-paper"
                    href="https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Cookie export guide
                  </a>
                </p>
              </motion.div>
            )}
          </AnimatePresence>

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
                  <div className="border-t border-line p-5 space-y-5">
                    {!audioOnly && (
                      <div>
                        <p className="mb-3 text-sm text-mist">
                          Quality target (uses ffmpeg merge for HD/4K)
                          {probe.max_height ? ` · listed up to ${probe.max_height}p` : ""}
                        </p>
                        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                          {presets.map((p, i) => (
                            <motion.button
                              key={p.id}
                              type="button"
                              initial={{ opacity: 0, y: 8 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: i * 0.03 }}
                              onClick={() => {
                                setSelectedPreset(p.id);
                                setSelectedFormat("");
                              }}
                              className={`rounded-xl border px-3 py-3 text-left transition ${
                                selectedPreset === p.id && !selectedFormat
                                  ? "border-lime bg-lime/10 shadow-glow"
                                  : "border-line bg-ink/60 hover:border-mist/50"
                              }`}
                            >
                              <div className="text-sm font-medium text-paper">{p.label}</div>
                              <div className="mt-1 text-xs text-mist">{p.note}</div>
                            </motion.button>
                          ))}
                        </div>
                        {(probe.max_height || 0) > 0 && (probe.max_height || 0) < 720 && (
                          <p className="mt-3 text-xs text-amber-300">
                            YouTube only exposed low progressive formats in the listing. Presets still request HD/4K via
                            adaptive merge — re-export fresh cookies if the download stays at 360p.
                          </p>
                        )}
                      </div>
                    )}

                    <div>
                      <p className="mb-3 text-sm text-mist">
                        {audioOnly ? "Audio formats" : "Advanced · exact streams (optional)"}
                      </p>
                      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                        {(audioOnly ? audioFormats : videoFormats).slice(0, 18).map((f, i) => (
                          <motion.div
                            key={f.format_id}
                            initial={{ opacity: 0, y: 8 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.03 }}
                          >
                            <FormatCard
                              f={f}
                              active={selectedFormat === f.format_id}
                              onClick={() => {
                                setSelectedFormat(f.format_id);
                                setSelectedPreset("");
                              }}
                            />
                          </motion.div>
                        ))}
                      </div>
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
