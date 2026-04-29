"use client";

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface ScoreHistoryEntry {
  query_id: string;
  score: number;
  rank: number;
  date: string;
  task_description?: string;
}

interface ScoreHistoryChartProps {
  history: ScoreHistoryEntry[];
}

export default function ScoreHistoryChart({ history }: ScoreHistoryChartProps) {
  const data = history
    .map((entry) => ({
      date: new Date(entry.date).toLocaleDateString(),
      score: entry.score,
      rank: entry.rank,
      tooltip: entry.task_description ?? entry.query_id,
    }))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  if (data.length === 0) {
    return <p className="text-sm text-gray-500">No score history available.</p>;
  }

  return (
    <div className="w-full h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <YAxis
            domain={[0, 1]}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <Tooltip
            contentStyle={{ fontSize: 12 }}
            formatter={((value: number) => [value.toFixed(4), "Score"]) as never}
            labelFormatter={((label: string, payload: Array<{ payload: (typeof data)[number] }>) => {
              if (payload && payload.length > 0) {
                const entry = payload[0].payload;
                return `${String(label)} - Rank #${entry.rank}\n${entry.tooltip}`;
              }
              return String(label);
            }) as never}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: "#3b82f6", r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
