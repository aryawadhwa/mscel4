import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

function mergeGroupSeries(beforeGroups = [], afterGroups = [], valueKey) {
  const afterMap = new Map(afterGroups.map((item) => [item.name, item]));
  return beforeGroups.map((item) => ({
    name: item.name,
    before: item[valueKey],
    after: afterMap.get(item.name)?.[valueKey] ?? 0,
  }));
}

function Card({ title, subtitle, children }) {
  return (
    <div className="rounded-xl bg-white/40 p-4 shadow-[0_2px_12px_rgba(0,100,100,0.14)]">
      <h3 className="text-sm font-bold text-slate-800">{title}</h3>
      <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
      <div className="mt-3 h-64">{children}</div>
    </div>
  );
}

function ComparisonChart({ data, afterColor = "#3b82f6" }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data}>
        <CartesianGrid stroke="#e2e8f0" vertical={false} />
        <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
        <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "rgba(255,255,255,0.95)",
            border: "none",
            borderRadius: "8px",
            boxShadow: "0 4px 16px rgba(0,100,100,0.15)",
            fontSize: "12px",
            color: "#334155",
          }}
        />
        <Legend wrapperStyle={{ fontSize: "11px" }} />
        <Bar dataKey="before" fill="#cbd5e1" radius={[6, 6, 0, 0]} />
        <Bar dataKey="after" fill={afterColor} radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function DistributionCharts({ charts }) {
  const before = charts?.before || {};
  const after = charts?.after || {};

  const approvalCharts = (after.approvalRateByProtected || []).map((afterChart) => {
    const beforeChart = (before.approvalRateByProtected || []).find((chart) => chart.column === afterChart.column);
    return {
      key: `approval-${afterChart.column}`,
      title: `Approval Rate by ${afterChart.column.replaceAll("_", " ")}`,
      subtitle: "Before is grey. After is blue.",
      data: mergeGroupSeries(beforeChart?.groups || afterChart.groups, afterChart.groups, "approvalRate"),
      color: "#3b82f6",
    };
  });

  const numericCharts = (after.numericBreakdowns || []).map((afterChart, index) => {
    const beforeChart = (before.numericBreakdowns || []).find(
      (chart) => chart.column === afterChart.column && chart.by === afterChart.by,
    );
    const palette = ["#8b5cf6", "#22c55e", "#f59e0b", "#06b6d4"];
    return {
      key: `numeric-${afterChart.column}-${afterChart.by}`,
      title: `${afterChart.column.replaceAll("_", " ")} by ${afterChart.by.replaceAll("_", " ")}`,
      subtitle: "Average values before and after mitigation.",
      data: mergeGroupSeries(beforeChart?.values || afterChart.values, afterChart.values, "average"),
      color: palette[index % palette.length],
    };
  });

  const representationCharts = (after.representationByProtected || []).map((afterChart, index) => {
    const beforeChart = (before.representationByProtected || []).find((chart) => chart.column === afterChart.column);
    const palette = ["#f59e0b", "#06b6d4", "#ec4899", "#22c55e"];
    return {
      key: `representation-${afterChart.column}`,
      title: `Representation by ${afterChart.column.replaceAll("_", " ")}`,
      subtitle: "How evenly the monitored groups appear in the dataset.",
      data: mergeGroupSeries(beforeChart?.groups || afterChart.groups, afterChart.groups, "representationPct"),
      color: palette[index % palette.length],
    };
  });

  const cards = [...approvalCharts, ...numericCharts, ...representationCharts];

  if (!cards.length) {
    return (
      <div className="rounded-xl bg-white/40 p-5 shadow-[0_2px_12px_rgba(0,100,100,0.14)]">
        <p className="text-sm text-slate-500">Add monitored columns in the Schema Builder to unlock comparison charts.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {cards.map((card) => (
        <Card key={card.key} title={card.title} subtitle={card.subtitle}>
          <ComparisonChart data={card.data} afterColor={card.color} />
        </Card>
      ))}
    </div>
  );
}
