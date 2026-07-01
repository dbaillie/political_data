export interface Region {
  slug: string
  name: string
  nation: string
  sort_order: number
}

export interface UkFiscalSummary {
  fye: string
  metric: string
  value_bn: number
}

export interface UkSpendingByFunction {
  fye: string
  function_slug: string
  function_name: string
  spend_bn: number
  pct_of_tme: number
}

export interface RegionalFiscal {
  fye: string
  region_slug: string
  region_name: string
  revenue_bn: number
  expenditure_identifiable_bn: number
  net_balance_bn: number
  revenue_per_head_gbp: number
  expenditure_per_head_gbp: number
  net_balance_per_head_gbp: number
}

export interface RegionalRevenueByType {
  fye: string
  region_slug: string
  region_name: string
  revenue_type_slug: string
  amount_bn: number
  pct_of_regional_total: number
}

export interface PesaTmeHistory {
  financial_year: string
  tme_bn: number
}

export interface PesaFunctionHistory {
  financial_year: string
  function_slug: string
  function_name: string
  spend_bn: number
  pct_of_total: number
}

export interface FiscalData {
  ukSummary: UkFiscalSummary[]
  ukSpending: UkSpendingByFunction[]
  regional: RegionalFiscal[]
  regionalRevenue: RegionalRevenueByType[]
  tmeHistory: PesaTmeHistory[]
  functionHistory: PesaFunctionHistory[]
  regions: Region[]
}

export type TabId = 'overview' | 'regions' | 'history' | 'revenue'
