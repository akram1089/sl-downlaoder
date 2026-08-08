"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { client } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await client.login(email, password);
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-6">
      <Link href="/" className="mb-10 font-display text-2xl font-bold text-paper">
        Stream<span className="text-lime">Line</span>
      </Link>
      <motion.form
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={onSubmit}
        className="space-y-4 rounded-2xl border border-line bg-panel/80 p-6 backdrop-blur"
      >
        <h1 className="font-display text-2xl font-semibold">Sign in</h1>
        <input
          className="w-full rounded-xl border border-line bg-ink px-4 py-3 outline-none ring-lime focus:ring-1"
          placeholder="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          className="w-full rounded-xl border border-line bg-ink px-4 py-3 outline-none ring-lime focus:ring-1"
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button
          disabled={loading}
          className="w-full rounded-xl bg-lime py-3 font-semibold text-ink transition hover:brightness-110 disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Continue"}
        </button>
        <p className="text-sm text-mist">
          No account?{" "}
          <Link href="/register" className="text-paper underline">
            Create one
          </Link>
        </p>
      </motion.form>
    </main>
  );
}
