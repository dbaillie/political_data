import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { RegionalFiscal } from '../lib/types'
import { gbpBn } from '../lib/format'

export function RegionalBalanceChart({ data }: { data: RegionalFiscal[] }) {
  const chartData = data
    .filter((r) => !['uk', 'england'].includes(r.region_slug))
    .map((r) => ({
      region: r.region_name,
      balance: r.net_balance_bn,
      revenue: r.revenue_bn,
      spend: r.expenditure_identifiable_bn,
    }))
    .sort((a, b) => b.balance - a.balance)

  return (
    <ResponsiveContainer width="100%" height={420}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
        <XAxis type="number" tickFormatter={(v) => `£${v}bn`} />
        <YAxis type="category" dataKey="region" width={160} tick={{ fontSize: 12 }} />
        <ReferenceLine x={0} stroke="#64748b" />
        <Tooltip
          formatter={(value, name) => {
            const v = Number(value ?? 0)
            const label = name === 'balance' ? 'Net balance (spend − revenue)' : String(name)
            return [gbpBn(v), label]
          }}
        />
        <Bar dataKey="balance" radius={[0, 4, 4, 0]}>
          {chartData.map((entry) => (
            <Cell key={entry.region} fill={entry.balance >= 0 ? '#dc2626' : '#059669'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
