export function gbpBn(value: number, digits = 1): string {
  return `£${value.toFixed(digits)}bn`
}

export function gbp(value: number): string {
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    maximumFractionDigits: 0,
  }).format(value)
}

export function shortFunctionName(name: string): string {
  return name.replace(/^\d+\.\s*/, '').replace(/\(includes training\)/i, '').trim()
}
