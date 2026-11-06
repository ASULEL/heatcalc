import { computed, ref, watch, type Ref } from 'vue'
import type {
  CostCalculationResult, ParameterField, RevenueTaxAnnualField, RevenueTaxInputs,
} from '../types'

export const revenueTaxAnnualFields: RevenueTaxAnnualField[] = [
  'steam_revenue_by_year', 'carbon_revenue_by_year', 'steam_volume_by_year',
]

type AnnualRow = { year: number; phase: string; electricityCost: number } & Record<RevenueTaxAnnualField, number | string>

export function useRevenueTaxInputs(cost: Ref<CostCalculationResult>, fields: Ref<ParameterField[]>) {
  const values = ref<Record<string, string>>({})
  const annualRows = ref<AnnualRow[]>([])
  const fieldsByName = computed(() => new Map(fields.value.map(field => [field.name, field])))
  const scalarFields = computed(() => fields.value.filter(field => !revenueTaxAnnualFields.includes(field.name as RevenueTaxAnnualField)))
  const availableYears = computed(() => cost.value.schedule.filter(row => row.phase === '运营期').length)
  const operatingRows = computed(() => annualRows.value.filter(row => row.phase === '运营期').slice(0, Number(values.value.operating_years)))
  const activeYears = computed(() => new Set(operatingRows.value.map(row => row.year)))

  watch([cost, fields], () => {
    values.value = Object.fromEntries(scalarFields.value.map(field => [field.name, field.value == null ? '' : String(field.value)]))
    if (Number(values.value.operating_years) > availableYears.value) values.value.operating_years = String(availableYears.value)
    annualRows.value = cost.value.schedule.map(row => ({
      year: row.year, phase: row.phase, electricityCost: row.electricity_cost,
      ...Object.fromEntries(revenueTaxAnnualFields.map(name => {
        const field = fieldsByName.value.get(name)
        const known = field?.value
        const value = Array.isArray(known) ? known[row.year - 1] : field?.annualDefault
        return [name, row.phase === '建设期' ? (name === 'steam_volume_by_year' ? '' : 0) : value ?? '']
      })) as Record<RevenueTaxAnnualField, number | string>,
    }))
  }, { immediate: true })

  function applyToOperatingYears(source: AnnualRow) {
    for (const row of operatingRows.value) {
      for (const name of revenueTaxAnnualFields) row[name] = source[name]
    }
  }

  function buildInputs(): RevenueTaxInputs {
    const scalars = Object.fromEntries(scalarFields.value.map(field => [
      field.name, field.inputType === 'select' ? values.value[field.name] : Number(values.value[field.name]) * (field.toToolFactor ?? 1),
    ])) as unknown as Omit<RevenueTaxInputs, RevenueTaxAnnualField>
    return {
      ...scalars,
      steam_revenue_by_year: annualRows.value.map(row => activeYears.value.has(row.year) ? Number(row.steam_revenue_by_year) : 0),
      carbon_revenue_by_year: annualRows.value.map(row => activeYears.value.has(row.year) ? Number(row.carbon_revenue_by_year) : 0),
      steam_volume_by_year: annualRows.value.map(row => !activeYears.value.has(row.year) || row.steam_volume_by_year === '' ? null : Number(row.steam_volume_by_year)),
    }
  }

  return { values, annualRows, scalarFields, fieldsByName, availableYears, activeYears, applyToOperatingYears, buildInputs }
}
