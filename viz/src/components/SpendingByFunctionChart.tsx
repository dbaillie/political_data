import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { UkSpendingByFunction } from '../lib/types'
import { gbpBn, shortFunctionName } from '../lib/format'

const COLORS = [
  '#1d4ed8',
  '#2563eb',
  '#3b82f6',
  '#60a5fa',
  '#0ea5e9',
  '#06b6d4',
  '#14b8a6',
  '#10b981',
  '#84cc16',
  '#eab308',
]

export function SpendingByFunctionChart({ data }: { data: UkSpendingByFunction[] }) {
  const chartData = [...data]
    .sort((a, b) => b.spend_bn - a.spend_bn)
    .map((row) => ({
      name: shortFunctionName(row.function_name),
      spend: row.spend_bn,
      pct: row.pct_of_tme,
    }))

  return (
    <ResponsiveContainer width="100%" height={360}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
        <XAxis type="number" tickFormatter={(v) => `£${v}bn`} />
        <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 12 }} />
        <Tooltip
          formatter={(value, _name, item) => {
            const v = Number(value ?? 0)
            const pct = (item?.payload as { pct?: number })?.pct ?? 0
            return [`${gbpBn(v)} (${pct}%)`, 'Spend']
          }}
        />
        <Bar dataKey="spend" radius={[0, 4, 4, 0]}>
          {chartData.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
