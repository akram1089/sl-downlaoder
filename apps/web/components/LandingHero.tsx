"use client";

import { motion } from "framer-motion";
import Link from "next/link";

export function LandingHero() {
  return (
    <section className="mt-24 flex flex-1 flex-col justify-center md:mt-10 md:max-w-3xl">
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
        Paste a link. Pick a format. Watch the queue breathe. Private, multi-user media capture for your team —
        tuned for speed, cookies, playlists, and live progress.
      </motion.p>
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.24 }}
        className="mt-10 flex flex-wrap items-center gap-4"
      >
        <Link
          href="/register"
          className="rounded-full bg-paper px-6 py-3 text-sm font-semibold text-ink transition hover:bg-lime"
        >
          Create account
        </Link>
        <Link
          href="/login"
          className="rounded-full border border-line px-6 py-3 text-sm font-semibold text-paper transition hover:border-lime/50"
        >
          Sign in
        </Link>
      </motion.div>
    </section>
  );
}
