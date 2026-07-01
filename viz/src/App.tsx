import { useState } from 'react'
import { FunctionHistoryChart } from './components/FunctionHistoryChart'
import { KpiCard, Panel } from './components/Layout'
import { RegionalBalanceChart } from './components/RegionalBalanceChart'
import { RevenueByTypeChart } from './components/RevenueByTypeChart'
import { SpendingByFunctionChart } from './components/SpendingByFunctionChart'
import { TmeHistoryChart } from './components/TmeHistoryChart'
import { useFiscalData } from './hooks/useFiscalData'
import { gbpBn } from './lib/format'
import type { TabId } from './lib/types'
import './App.css'

const TABS: { id: TabId; label: string }[] = [
  { id: 'overview', label: 'UK overview' },
  { id: 'regions', label: 'Regions' },
  { id: 'history', label: 'History' },
  { id: 'revenue', label: 'Revenue' },
]

function App() {
  const { data, loading, error } = useFiscalData()
  const [tab, setTab] = useState<TabId>('overview')

  if (loading) {
    return <div className="app app--centered">Loading fiscal data…</div>
  }

  if (error || !data) {
    return (
      <div className="app app--centered app--error">
        <h1>Could not load data</h1>
        <p>{error ?? 'Unknown error'}</p>
        <p className="muted">
          Run <code>python scripts/export_viz_data.py</code> from the repo root, then refresh.
        </p>
      </div>
    )
  }

  const metrics = Object.fromEntries(data.ukSummary.map((r) => [r.metric, r.value_bn]))
  const fye = data.ukSummary[0]?.fye ?? '2024-25'

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">UK public finances</p>
          <h1>Where government money goes</h1>
          <p className="lede">
            FYE {fye.replace('-', '–')} · ONS Country &amp; Regional PSF + HM Treasury PESA
          </p>
        </div>
        <nav className="tabs" aria-label="Views">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? 'active' : ''}
              onClick={() => setTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      {tab === 'overview' && (
        <>
          <section className="kpi-grid">
            <KpiCard label="Total revenue" value={gbpBn(metrics.revenue ?? 0)} />
            <KpiCard label="Total managed expenditure" value={gbpBn(metrics.expenditure_tme ?? 0)} />
            <KpiCard
              label="Fiscal deficit"
              value={gbpBn(metrics.fiscal_deficit ?? 0)}
              tone="negative"
              hint="Revenue minus TME"
            />
            <KpiCard
              label="Debt interest"
              value={gbpBn(metrics.debt_interest ?? 0)}
              hint="Within general public services"
            />
          </section>
          <Panel
            title="Spending by function"
            subtitle="UK total managed expenditure, COFOG Level 0 (FYE 2024–25)"
          >
            <SpendingByFunctionChart data={data.ukSpending} />
          </Panel>
        </>
      )}

      {tab === 'regions' && (
        <>
          <Panel
            title="Regional net fiscal balance"
            subtitle="Identifiable expenditure minus revenue · positive = net recipient"
          >
            <RegionalBalanceChart data={data.regional} />
          </Panel>
          <p className="footnote">
            London and the South East are large net contributors on an identifiable basis; Wales,
            Northern Ireland and the North East receive more identifiable spend than they raise in
            revenue.
          </p>
        </>
      )}

      {tab === 'history' && (
        <>
          <Panel title="Total managed expenditure" subtitle="HM Treasury PESA table 4.1 · from 1990">
            <TmeHistoryChart data={data.tmeHistory} />
          </Panel>
          <Panel
            title="Major spending areas over time"
            subtitle="Health, welfare, education and debt-related services"
          >
            <FunctionHistoryChart data={data.functionHistory} />
          </Panel>
        </>
      )}

      {tab === 'revenue' && (
        <Panel
          title="Revenue by tax type"
          subtitle="ONS Table S9 accrued receipts · residence basis"
        >
          <RevenueByTypeChart regional={data.regional} revenue={data.regionalRevenue} />
        </Panel>
      )}

      <footer className="footer">
        Data: <code>data/export/*.csv</code> · Schema: <code>supabase/schema.sql</code>
      </footer>
    </div>
  )
}

export default App
