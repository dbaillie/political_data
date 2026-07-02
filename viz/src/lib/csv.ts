import Papa from 'papaparse'

/** Resolve public data paths for both local dev (/) and GitHub Pages (/repo-name/). */
export function dataUrl(filename: string): string {
  const base = import.meta.env.BASE_URL
  return `${base}data/${filename}`
}

export async function loadCsv<T extends Record<string, string>>(
  filename: string,
): Promise<T[]> {
  const response = await fetch(dataUrl(filename))
  if (!response.ok) {
    throw new Error(`Failed to load ${dataUrl(filename)}: ${response.status}`)
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
