// The one place colours are defined. Tailwind (tailwind.config.ts) and the
// Recharts charts both read these tokens; nothing else hard-codes a colour.
export const colors = {
  brand: { DEFAULT: "#E30613", dark: "#A8000C", tint: "#FDECEC" },
  ink: { DEFAULT: "#14213D", muted: "#4A5568" },
  canvas: "#FBFAF8",
  surface: "#FFFDFB",
  line: "#E7E3DF",
  ok: { DEFAULT: "#1B7F45", tint: "#E7F4EC" },
  warn: { DEFAULT: "#C77700", tint: "#FBF0DF" },
  bad: { DEFAULT: "#E30613", tint: "#FDECEC" },
  muted: { DEFAULT: "#6B7280", tint: "#F1EFEC" },
};

// Chart colours for the verdicts. Red uses the dark red token: the bright red
// sits too close to amber for colour-blind readers when they are stacked
// (checked with a CVD validator). Charts always add a legend and labels too.
export const verdictChartColors = {
  Green: colors.ok.DEFAULT,
  Amber: colors.warn.DEFAULT,
  Red: colors.brand.dark,
};
