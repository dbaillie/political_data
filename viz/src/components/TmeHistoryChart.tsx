import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { PesaTmeHistory } from '../lib/types'
import { gbpBn } from '../lib/format'

export function TmeHistoryChart({ data }: { data: PesaTmeHistory[] }) {
  const recent = data.filter((row) => {
    const startYear = Number(row.financial_year.split('-')[0])
    return startYear >= 1990
  })

  return (
    <ResponsiveContainer width="100%" height={360}>
      <LineChart data={recent} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
        <XAxis
          dataKey="financial_year"
          minTickGap={24}
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
        />
        <YAxis tickFormatter={(v) => `£${v}bn`} width={72} />
        <Tooltip formatter={(value) => [gbpBn(Number(value ?? 0)), 'TME']} />
        <Line
          type="monotone"
          dataKey="tme_bn"
          stroke="#1d4ed8"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
