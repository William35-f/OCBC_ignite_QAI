// Small chart kit for the admin dashboard (Recharts). Thin marks, recessive axes,
// a legend whenever there are 2+ series, a hover tooltip, and a table view for every chart.
import { useState, type ReactNode } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { colors, verdictChartColors } from "../theme";

const axis = { stroke: colors.line, tick: { fill: colors.ink.muted, fontSize: 12 } };
const tooltipStyle = {
  contentStyle: { borderRadius: 12, border: `1px solid ${colors.line}`, background: colors.surface, fontSize: 13 },
  labelStyle: { color: colors.ink.DEFAULT, fontWeight: 600 },
  cursor: { fill: colors.muted.tint },
};

/** A card with a title, the chart, and a "Show as table" toggle. */
export function ChartCard({
  title,
  subtitle,
  table,
  children,
}: {
  title: string;
  subtitle?: string;
  table: ReactNode;
  children: ReactNode;
}) {
  const [asTable, setAsTable] = useState(false);
  return (
    <section className="card space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-bold">{title}</h3>
          {subtitle && <p className="text-xs text-ink-muted">{subtitle}</p>}
        </div>
        <button className="text-xs font-semibold text-ink-muted underline hover:text-ink" onClick={() => setAsTable(!asTable)}>
          {asTable ? "Show chart" : "Show as table"}
        </button>
      </div>
      {asTable ? <div className="overflow-x-auto">{table}</div> : children}
    </section>
  );
}

export function StatTile({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return (
    <div className="card py-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
      <p className="mt-1 text-3xl font-bold text-ink">{value}</p>
      {note && <p className="mt-0.5 text-xs text-ink-muted">{note}</p>}
    </div>
  );
}

export function SimpleTable({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-line text-xs uppercase text-ink-muted">
        <tr>
          {head.map((h) => (
            <th key={h} className="py-2 pr-4">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="border-b border-line last:border-0">
            {r.map((c, j) => (
              <td key={j} className="py-2 pr-4">
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Stacked columns: final verdicts per day. 2px surface gaps between segments, legend + tooltip. */
export function VerdictChart({ data }: { data: { day: string; Green: number; Amber: number; Red: number }[] }) {
  const keys = ["Green", "Amber", "Red"] as const;
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={colors.line} />
        <XAxis dataKey="day" {...axis} tickLine={false} />
        <YAxis allowDecimals={false} {...axis} tickLine={false} axisLine={false} />
        <Tooltip {...tooltipStyle} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 13, color: colors.ink.muted }} />
        {keys.map((k) => (
          <Bar
            key={k}
            dataKey={k}
            stackId="v"
            fill={verdictChartColors[k]}
            stroke={colors.surface}
            strokeWidth={2}
            maxBarSize={24}
            radius={k === "Red" ? [4, 4, 0, 0] : 0}
            isAnimationActive={false}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

/** One series, horizontal bars, value at the tip. */
export function BarList({
  data,
  color = colors.ink.DEFAULT,
  valueLabel = "Count",
}: {
  data: { label: string; value: number }[];
  color?: string;
  valueLabel?: string;
}) {
  const height = Math.max(120, data.length * 34 + 24);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 32, left: 0, bottom: 0 }}>
        <XAxis type="number" hide allowDecimals={false} />
        <YAxis type="category" dataKey="label" width={170} {...axis} tickLine={false} axisLine={false} />
        <Tooltip {...tooltipStyle} formatter={(v: number) => [v, valueLabel]} />
        <Bar dataKey="value" fill={color} barSize={16} radius={[0, 4, 4, 0]} isAnimationActive={false}>
          <LabelList dataKey="value" position="right" fill={colors.ink.DEFAULT} fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
