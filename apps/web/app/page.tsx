"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0">
        <motion.div
          className="absolute -left-24 top-24 h-72 w-72 rounded-full bg-lime/20 blur-3xl"
          animate={{ x: [0, 40, 0], y: [0, 20, 0] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-10 right-0 h-96 w-96 rounded-full bg-sky-500/10 blur-3xl"
          animate={{ x: [0, -30, 0], y: [0, -25, 0] }}
          transition={{ duration: 12, repeat: Infinity, ease: "easeInOut" }}
        />
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
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm text-mist transition hover:text-paper">
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-full bg-lime px-4 py-2 text-sm font-medium text-ink shadow-glow transition hover:brightness-110"
            >
              Get access
            </Link>
          </div>
        </header>

        <section className="mt-24 flex flex-1 flex-col justify-center md:mt-0 md:max-w-3xl">
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 text-sm uppercase tracking-[0.22em] text-mist"
          >
            SpikeIQ cloud
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 }}
            className="font-display text-5xl font-extrabold leading-[0.95] tracking-tight text-paper md:text-7xl"
          >
            StreamLine
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.16 }}
            className="mt-6 max-w-xl text-lg leading-relaxed text-mist md:text-xl"
          >
            Paste a link. Pick a format. Watch the queue breathe. Private, multi-user media capture for
            your team — tuned for speed, cookies, playlists, and live progress.
          </motion.p>
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.24 }}
            className="mt-10 flex flex-wrap items-center gap-4"
          >
            <Link
              href="/app"
              className="rounded-full bg-paper px-6 py-3 text-sm font-semibold text-ink transition hover:bg-lime"
            >
              Open downloader
            </Link>
            <span className="text-sm text-mist">download.spikeiq.cloud</span>
          </motion.div>
        </section>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
          className="mt-16 h-px w-full bg-gradient-to-r from-transparent via-lime/40 to-transparent"
        />
        <p className="mt-6 text-xs text-mist/70">Powered by yt-dlp · Self-hosted on SpikeIQ</p>
      </div>
    </main>
  );
}
