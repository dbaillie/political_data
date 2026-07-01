import type { ReactNode } from 'react'

export function KpiCard({
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  label: string
  value: string
  hint?: string
  tone?: 'neutral' | 'positive' | 'negative'
}) {
  return (
    <article className={`kpi kpi--${tone}`}>
      <p className="kpi__label">{label}</p>
      <p className="kpi__value">{value}</p>
      {hint ? <p className="kpi__hint">{hint}</p> : null}
    </article>
  )
}

export function Panel({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: ReactNode
}) {
  return (
    <section className="panel">
      <header className="panel__header">
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      <div className="panel__body">{children}</div>
    </section>
  )
}
