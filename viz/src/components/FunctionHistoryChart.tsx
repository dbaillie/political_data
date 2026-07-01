import { useMemo, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { PesaFunctionHistory } from '../lib/types'
import { shortFunctionName } from '../lib/format'

const SERIES = [
  { slug: 'health', color: '#2563eb', label: 'Health' },
  { slug: 'social-protection', color: '#dc2626', label: 'Social protection' },
  { slugPrefix: 'education', color: '#059669', label: 'Education' },
  { slug: 'general-public-services', color: '#d97706', label: 'General public services' },
]

function matchFunction(
  data: PesaFunctionHistory[],
  year: string,
  series: (typeof SERIES)[number],
) {
  return data.find((d) => {
    if (d.financial_year !== year) return false
    if ('slugPrefix' in series && series.slugPrefix) {
      return d.function_slug.startsWith(series.slugPrefix)
    }
    return d.function_slug === series.slug
  })
}

export function FunctionHistoryChart({ data }: { data: PesaFunctionHistory[] }) {
  const [mode, setMode] = useState<'spend' | 'share'>('spend')

  const chartData = useMemo(() => {
    const years = [...new Set(data.map((d) => d.financial_year))]
      .filter((y) => Number(y.split('-')[0]) >= 2002)
      .sort()

    return years.map((year) => {
      const row: Record<string, string | number> = { year }
      for (const series of SERIES) {
        const match = matchFunction(data, year, series)
        const key = 'slugPrefix' in series && series.slugPrefix ? series.slugPrefix : series.slug!
        row[key] = match
          ? mode === 'spend'
            ? match.spend_bn
            : match.pct_of_total
          : 0
      }
      return row
    })
  }, [data, mode])

  return (
    <div className="history-controls">
      <div className="segmented">
        <button
          type="button"
          className={mode === 'spend' ? 'active' : ''}
          onClick={() => setMode('spend')}
        >
          £ billion
        </button>
        <button
          type="button"
          className={mode === 'share' ? 'active' : ''}
          onClick={() => setMode('share')}
        >
          % of total
        </button>
      </div>
      <ResponsiveContainer width="100%" height={360}>
        <AreaChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="year" minTickGap={20} tick={{ fontSize: 11 }} />
          <YAxis
            tickFormatter={(v) => (mode === 'spend' ? `£${v}bn` : `${v}%`)}
            width={56}
          />
          <Tooltip
            formatter={(value, name) => {
              const label =
                SERIES.find(
                  (s) =>
                    s.slug === name ||
                    ('slugPrefix' in s && s.slugPrefix === name),
                )?.label ?? String(name)
              const formatted =
                mode === 'spend'
                  ? `£${Number(value ?? 0).toFixed(1)}bn`
                  : `${Number(value ?? 0).toFixed(1)}%`
              return [formatted, shortFunctionName(label)]
            }}
          />
          <Legend />
          {SERIES.map((series) => {
            const key =
              'slugPrefix' in series && series.slugPrefix ? series.slugPrefix : series.slug!
            return (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                name={series.label}
                stackId="1"
                stroke={series.color}
                fill={series.color}
                fillOpacity={0.65}
              />
            )
          })}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
