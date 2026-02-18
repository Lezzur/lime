import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        lime: {
          50: "#f7fee7",
          100: "#ecfccb",
          400: "#a3e635",
          500: "#84cc16",
          600: "#65a30d",
          900: "#1a2e05",
        },
      },
      animation: {
        "breathe-calm": "breathe-calm 4s ease-in-out infinite",
        "breathe-alert": "breathe-alert 2s ease-in-out infinite",
        "breathe-urgent": "breathe-urgent 0.8s ease-in-out infinite",
        "tap-fade": "tap-fade 0.3s ease-out forwards",
        "pulse-slow": "pulse 3s ease-in-out infinite",
      },
      keyframes: {
        "breathe-calm": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.7" },
          "50%": { transform: "scale(1.15)", opacity: "1" },
        },
        "breathe-alert": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.8" },
          "50%": { transform: "scale(1.3)", opacity: "1" },
        },
        "breathe-urgent": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.9" },
          "50%": { transform: "scale(1.5)", opacity: "1" },
        },
        "tap-fade": {
          "0%": { opacity: "0.6", transform: "scale(0.8)" },
          "50%": { opacity: "0.4", transform: "scale(1.2)" },
          "100%": { opacity: "0", transform: "scale(1.5)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
