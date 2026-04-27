"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import type { ScoreComponents } from "@/types/api";

interface ScoreBreakdownChartProps {
  components: ScoreComponents;
}

const COLORS: Record<string, string> = {
  R: "#3b82f6",
  Q: "#10b981",
  C: "#f59e0b",
  I: "#8b5cf6",
};

const LABELS: Record<string, string> = {
  R: "Recency",
  Q: "Quality",
  C: "Contextual Fit",
  I: "Integrity",
};

export default function ScoreBreakdownChart({ components }: ScoreBreakdownChartProps) {
  const data = [
    { name: "R", value: components.R, label: LABELS.R },
    { name: "Q", value: components.Q, label: LABELS.Q },
    { name: "C", value: components.C, label: LABELS.C },
    { name: "I", value: components.I, label: LABELS.I },
  ];

  return (
    <div className="w-full h-24">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
          <XAxis type="number" domain={[0, 1]} hide />
          <YAxis type="category" dataKey="name" width={20} tick={{ fontSize: 11 }} />
          <Tooltip
            formatter={((value: number, name: string) => [
              value.toFixed(3),
              LABELS[name] || name,
            ]) as never}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={COLORS[entry.name]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
