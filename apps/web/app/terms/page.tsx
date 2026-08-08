import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms of Use",
  description: "Terms for using StreamLine by SpikeIQ.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-12 text-paper">
      <Link href="/" className="font-display text-xl font-bold">
        Stream<span className="text-lime">Line</span>
      </Link>
      <h1 className="mt-10 font-display text-4xl font-bold">Terms of Use</h1>
      <p className="mt-2 text-sm text-mist">Last updated: August 8, 2026</p>
      <div className="mt-8 space-y-4 text-mist leading-relaxed">
        <p>
          StreamLine is provided for lawful personal or organizational use by authorized SpikeIQ users. You are
          responsible for complying with the terms of source platforms and applicable copyright law.
        </p>
        <p>
          Do not use the service to infringe rights, attack infrastructure, or share account credentials. We may
          suspend accounts that abuse rate limits or upload malicious content.
        </p>
        <p>
          The service is provided as-is without warranty of uninterrupted access. Media retention is temporary and
          files may be purged automatically.
        </p>
        <p>
          Contact: <a className="text-paper underline" href="mailto:admin@spikeiq.cloud">admin@spikeiq.cloud</a>
        </p>
      </div>
    </main>
  );
}
