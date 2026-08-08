import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How StreamLine handles accounts, cookies files, and download data.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-12 text-paper">
      <Link href="/" className="font-display text-xl font-bold">
        Stream<span className="text-lime">Line</span>
      </Link>
      <h1 className="mt-10 font-display text-4xl font-bold">Privacy Policy</h1>
      <p className="mt-2 text-sm text-mist">Last updated: August 8, 2026</p>
      <div className="mt-8 space-y-4 text-mist leading-relaxed">
        <p>
          StreamLine is operated by SpikeIQ for authorized users. We collect the email address you register with,
          download job metadata (URL, status, timestamps), and optional cookie profiles you upload.
        </p>
        <p>
          Uploaded cookie files and completed media artifacts are stored on the server for operational use and are
          deleted according to retention settings. Do not upload credentials you are not authorized to use.
        </p>
        <p>
          We do not sell personal data. Access is restricted to authenticated accounts on this deployment
          (download.spikeiq.cloud).
        </p>
        <p>
          Contact: <a className="text-paper underline" href="mailto:admin@spikeiq.cloud">admin@spikeiq.cloud</a>
        </p>
      </div>
    </main>
  );
}
