import { useEffect, useState } from 'react'
import { loadCsv, num } from '../lib/csv'
import type { FiscalData } from '../lib/types'

export function useFiscalData() {
  const [data, setData] = useState<FiscalData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [
          ukSummaryRaw,
          ukSpendingRaw,
          regionalRaw,
          regionalRevenueRaw,
          tmeHistoryRaw,
          functionHistoryRaw,
          regionsRaw,
        ] = await Promise.all([
          loadCsv('/data/uk_fiscal_summary.csv'),
          loadCsv('/data/uk_spending_by_function.csv'),
          loadCsv('/data/regional_fiscal.csv'),
          loadCsv('/data/regional_revenue_by_type.csv'),
          loadCsv('/data/pesa_tme_history.csv'),
          loadCsv('/data/pesa_spending_by_function_history.csv'),
          loadCsv('/data/regions.csv'),
        ])

        if (cancelled) return

        setData({
          ukSummary: ukSummaryRaw.map((r) => ({
            fye: r.fye,
            metric: r.metric,
            value_bn: num(r.value_bn),
          })),
          ukSpending: ukSpendingRaw.map((r) => ({
            fye: r.fye,
            function_slug: r.function_slug,
            function_name: r.function_name,
            spend_bn: num(r.spend_bn),
            pct_of_tme: num(r.pct_of_tme),
          })),
          regional: regionalRaw.map((r) => ({
            fye: r.fye,
            region_slug: r.region_slug,
            region_name: r.region_name,
            revenue_bn: num(r.revenue_bn),
            expenditure_identifiable_bn: num(r.expenditure_identifiable_bn),
            net_balance_bn: num(r.net_balance_bn),
            revenue_per_head_gbp: num(r.revenue_per_head_gbp),
            expenditure_per_head_gbp: num(r.expenditure_per_head_gbp),
            net_balance_per_head_gbp: num(r.net_balance_per_head_gbp),
          })),
          regionalRevenue: regionalRevenueRaw.map((r) => ({
            fye: r.fye,
            region_slug: r.region_slug,
            region_name: r.region_name,
            revenue_type_slug: r.revenue_type_slug,
            amount_bn: num(r.amount_bn),
            pct_of_regional_total: num(r.pct_of_regional_total),
          })),
          tmeHistory: tmeHistoryRaw.map((r) => ({
            financial_year: r.financial_year,
            tme_bn: num(r.tme_bn),
          })),
          functionHistory: functionHistoryRaw.map((r) => ({
            financial_year: r.financial_year,
            function_slug: r.function_slug,
            function_name: r.function_name,
            spend_bn: num(r.spend_bn),
            pct_of_total: num(r.pct_of_total),
          })),
          regions: regionsRaw.map((r) => ({
            slug: r.slug,
            name: r.name,
            nation: r.nation,
            sort_order: num(r.sort_order),
          })),
        })
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load data')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  return { data, error, loading }
}
