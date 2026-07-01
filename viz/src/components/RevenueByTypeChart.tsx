import { useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { RegionalFiscal, RegionalRevenueByType } from '../lib/types'
import { gbpBn } from '../lib/format'

const TYPE_LABELS: Record<string, string> = {
  income_tax: 'Income tax',
  vat: 'VAT',
  national_insurance: 'National Insurance',
  corporation_tax: 'Corporation tax',
  council_tax: 'Council tax',
  business_rates: 'Business rates',
  fuel_duties: 'Fuel duties',
  excise_duties: 'Excise duties',
  capital_gains_tax: 'CGT',
  interest_and_dividends: 'Interest & dividends',
  gross_operating_surplus: 'Gross operating surplus',
  other: 'Other',
}

export function RevenueByTypeChart({
  regional,
  revenue,
}: {
  regional: RegionalFiscal[]
  revenue: RegionalRevenueByType[]
}) {
  const regionOptions = regional
    .filter((r) => !['uk', 'england'].includes(r.region_slug))
    .map((r) => ({ slug: r.region_slug, name: r.region_name }))

  const [selected, setSelected] = useState(regionOptions[0]?.slug ?? 'london')

  const chartData = useMemo(() => {
    return revenue
      .filter((r) => r.region_slug === selected)
      .map((r) => ({
        type: TYPE_LABELS[r.revenue_type_slug] ?? r.revenue_type_slug,
        amount: r.amount_bn,
        pct: r.pct_of_regional_total,
      }))
      .sort((a, b) => b.amount - a.amount)
      .slice(0, 8)
  }, [revenue, selected])

  return (
    <div className="revenue-chart">
      <label className="select-label">
        Region
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {regionOptions.map((r) => (
            <option key={r.slug} value={r.slug}>
              {r.name}
            </option>
          ))}
        </select>
      </label>
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="type" tick={{ fontSize: 11 }} interval={0} angle={-20} textAnchor="end" height={70} />
          <YAxis tickFormatter={(v) => `£${v}bn`} width={64} />
          <Tooltip
            formatter={(value, _n, item) => {
              const v = Number(value ?? 0)
              const pct = (item?.payload as { pct?: number })?.pct ?? 0
              return [`${gbpBn(v)} (${pct}%)`, 'Revenue']
            }}
          />
          <Bar dataKey="amount" fill="#7c3aed" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
