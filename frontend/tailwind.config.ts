import type { Config } from "tailwindcss";

// All colours live here as theme tokens. Do not hard-code colours in components.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#E30613", dark: "#A8000C", tint: "#FDECEC" },
        ink: { DEFAULT: "#14213D", muted: "#4A5568" },
        canvas: "#FBFAF8",
        surface: "#FFFDFB",
        line: "#E7E3DF",
        ok: { DEFAULT: "#1B7F45", tint: "#E7F4EC" },
        warn: { DEFAULT: "#C77700", tint: "#FBF0DF" },
        bad: { DEFAULT: "#E30613", tint: "#FDECEC" },
        muted: { DEFAULT: "#6B7280", tint: "#F1EFEC" },
      },
      fontFamily: {
        sans: ["DM Sans", "system-ui", "sans-serif"],
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
