"use client";

import { useEffect } from "react";

/** Ensures Tailwind CSS is attached even when Next streaming HTML omits link tags. */
export function StyleLoader() {
  useEffect(() => {
    const href = "/streamline.css";
    if (!document.querySelector(`link[href="${href}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      document.head.appendChild(link);
    }
  }, []);
  return null;
}
