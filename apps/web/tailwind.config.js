/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#0B0F14",
        paper: "#F3F0E8",
        lime: "#B8FF3C",
        mist: "#8A93A3",
        panel: "#121821",
        line: "#1E2733",
      },
      fontFamily: {
        display: ["var(--font-syne)", "sans-serif"],
        sans: ["var(--font-plex)", "sans-serif"],
      },
      boxShadow: {
        glow: "0 0 40px rgba(184, 255, 60, 0.18)",
      },
    },
  },
  plugins: [],
};
