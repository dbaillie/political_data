import Papa from 'papaparse'

export async function loadCsv<T extends Record<string, string>>(
  path: string,
): Promise<T[]> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`Failed to load ${path}: ${response.status}`)
  }
  const text = await response.text()
  const parsed = Papa.parse<T>(text, { header: true, skipEmptyLines: true })
  if (parsed.errors.length) {
    throw new Error(parsed.errors.map((e) => e.message).join('; '))
  }
  return parsed.data
}

export function num(value: string | number | undefined): number {
  if (typeof value === 'number') return value
  return Number(value ?? 0)
}
