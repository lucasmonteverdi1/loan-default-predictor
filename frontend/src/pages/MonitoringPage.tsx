import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from "recharts";
import { getStats, type StatsResponse } from "../api";

const RECOMMENDATION_COLORS: Record<string, string> = {
  APPROVED: "#16a34a",
  CONDITIONAL: "#ca8a04",
  REVIEW_NEEDED: "#ea580c",
  REJECTED: "#dc2626",
};

const POLL_INTERVAL_MS = 10_000;

export default function MonitoringPage() {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  async function fetchStats() {
    try {
      const data = await getStats();
      setStats(data);
      setLastUpdated(new Date());
      setError(null);
    } catch {
      setError("Could not reach backend.");
    }
  }

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (!stats) {
    return <p className="text-sm text-gray-400 animate-pulse">Loading stats…</p>;
  }

  const total = stats.total;
  const counts = stats.recommendation_counts;

  const approvedPct = total > 0 ? (((counts.APPROVED ?? 0) / total) * 100).toFixed(0) : "—";
  const rejectedPct = total > 0 ? (((counts.REJECTED ?? 0) / total) * 100).toFixed(0) : "—";

  const pieData = Object.entries(counts).map(([name, value]) => ({ name, value }));

  const histData = stats.histogram.map((b) => ({
    bin: `${(b.bin_start * 100).toFixed(0)}–${(b.bin_end * 100).toFixed(0)}%`,
    count: b.count,
  }));

  const timelineData = [...stats.recent].reverse().map((r, i) => ({
    i,
    prob: +(r.prob * 100).toFixed(1),
    recommendation: r.recommendation,
  }));

  return (
    <div className="flex flex-col gap-6">
      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Total predictions" value={total.toString()} />
        <StatCard label="Approved" value={total > 0 ? `${approvedPct}%` : "—"} color="text-green-600" />
        <StatCard label="Rejected" value={total > 0 ? `${rejectedPct}%` : "—"} color="text-red-600" />
      </div>

      {total === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-400 shadow-sm">
          No predictions yet — go to <strong>Evaluate</strong> to score a loan application.
        </div>
      ) : (
        <>
          {/* Histogram */}
          <ChartCard title="Default probability distribution">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={histData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="bin" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Pie */}
            <ChartCard title="Decision distribution">
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }: { name?: string; percent?: number }) =>
                      name && percent != null
                        ? `${name.replace("_", " ")} ${(percent * 100).toFixed(0)}%`
                        : ""
                    }
                    labelLine={false}
                  >
                    {pieData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={RECOMMENDATION_COLORS[entry.name] ?? "#9ca3af"}
                      />
                    ))}
                  </Pie>
                  <Legend
                    formatter={(v) => v.replace("_", " ")}
                    iconSize={10}
                    wrapperStyle={{ fontSize: 11 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>

            {/* Timeline */}
            <ChartCard title="Recent predictions (last 20)">
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={timelineData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="i" hide />
                  <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => [`${v}%`, "Default prob."]} />
                  <Line
                    type="monotone"
                    dataKey="prob"
                    stroke="#6366f1"
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    activeDot={{ r: 5 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}

      {lastUpdated && (
        <p className="text-xs text-gray-400 text-right">
          Last updated: {lastUpdated.toLocaleTimeString()} · auto-refreshes every 10s
        </p>
      )}
    </div>
  );
}

function StatCard({ label, value, color = "text-gray-900" }: { label: string; value: string; color?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm text-center">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-semibold text-gray-700 mb-3">{title}</p>
      {children}
    </div>
  );
}
