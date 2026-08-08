import Link from "next/link";
import type { Metadata } from "next";
import { LandingHero } from "@/components/LandingHero";
import { SITE_DESCRIPTION, SITE_NAME, SITE_TAGLINE } from "@/lib/site";

export const metadata: Metadata = {
  title: `${SITE_NAME} — ${SITE_TAGLINE}`,
  description: SITE_DESCRIPTION,
  alternates: { canonical: "/" },
};

const features = [
  {
    title: "Format control",
    body: "Choose Best, 1080p, or 4K targets. StreamLine merges adaptive streams with ffmpeg for real HD output.",
  },
  {
    title: "Live download queue",
    body: "Track progress, speed, and ETA in real time. Cancel, retry, and keep a personal history.",
  },
  {
    title: "Playlists & cookies",
    body: "Batch playlist items and upload Netscape cookies for authenticated or restricted sources.",
  },
];

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-24 top-24 h-72 w-72 rounded-full bg-lime/20 blur-3xl" />
        <div className="absolute bottom-10 right-0 h-96 w-96 rounded-full bg-sky-500/10 blur-3xl" />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(243,240,232,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(243,240,232,0.35) 1px, transparent 1px)",
            backgroundSize: "48px 48px",
            maskImage: "radial-gradient(ellipse at center, black 20%, transparent 75%)",
          }}
        />
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen max-w-6xl flex-col px-6 pb-16 pt-8">
        <header className="flex items-center justify-between">
          <div className="font-display text-2xl font-extrabold tracking-tight text-paper">
            Stream<span className="text-lime">Line</span>
          </div>
          <nav className="flex items-center gap-3" aria-label="Primary">
            <Link href="/login" className="text-sm text-mist transition hover:text-paper">
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-full bg-lime px-4 py-2 text-sm font-medium text-ink shadow-glow transition hover:brightness-110"
            >
              Get access
            </Link>
          </nav>
        </header>

        <LandingHero />

        <section className="mt-20 grid gap-8 border-t border-line/70 pt-12 md:grid-cols-3" aria-labelledby="features-heading">
          <h2 id="features-heading" className="sr-only">
            Features
          </h2>
          {features.map((f) => (
            <article key={f.title}>
              <h3 className="font-display text-xl font-semibold text-paper">{f.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-mist">{f.body}</p>
            </article>
          ))}
        </section>

        <footer className="mt-16 flex flex-wrap items-center justify-between gap-4 border-t border-line/60 pt-6 text-xs text-mist/80">
          <p>
            Powered by yt-dlp · Self-hosted on SpikeIQ ·{" "}
            <span className="text-mist">download.spikeiq.cloud</span>
          </p>
          <div className="flex gap-4">
            <Link href="/privacy" className="hover:text-paper">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-paper">
              Terms
            </Link>
            <Link href="/sitemap.xml" className="hover:text-paper">
              Sitemap
            </Link>
          </div>
        </footer>
      </div>
    </main>
  );
}
