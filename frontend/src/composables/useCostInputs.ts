import { computed, ref, watch, type Ref } from 'vue'
import type {
  AnnualCostField, CostScheduleInputs, LoanCalculationResult,
  MaintenanceRatioPeriod, ParameterField,
} from '../types'

export const annualCostFields: AnnualCostField[] = [
  'total_electricity_by_year', 'water_cost_by_year', 'labor_cost_by_year',
  'amortization_expense_by_year', 'working_capital_loan_interest_by_year',
]

type AnnualInputRow = { year: number; phase: string } & Record<AnnualCostField, number | string>

export function useCostInputs(loan: Ref<LoanCalculationResult>, fields: Ref<ParameterField[]>) {
  const equipmentTotalCost = ref<number | string>('') // 设备总成本，万元
  const depreciationYears = ref<number | string>('') // 折旧年限，年
  const periods = ref<MaintenanceRatioPeriod[]>([]) // 可编辑的维修费比例区间
  const annualRows = ref<AnnualInputRow[]>([]) // 各项目年份的输入费用
  const fieldsByName = computed(() => new Map(fields.value.map(field => [field.name, field])))

  watch(fields, () => {
    equipmentTotalCost.value = String(fieldsByName.value.get('equipment_total_cost')?.value ?? '')
    depreciationYears.value = String(fieldsByName.value.get('depreciation_years')?.value ?? '')
  }, { immediate: true })

  watch([loan, fields], () => {
    const source = loan.value // 当前方案固定的借款表
    const operatingRows = source.schedule.filter(row => row.phase === '运营期')
    const knownPeriods = fieldsByName.value.get('maintenance_ratio_periods')?.value
    const periodDefaults = fieldsByName.value.get('maintenance_ratio_periods')!.periodDefaults! // Tool 的区间示例

    // 图片中的维修费示例每5个运营年一段，用户可修改起止年份和比例。
    periods.value = Array.isArray(knownPeriods) ? knownPeriods.map(period => ({ ...period })) : []
    if (!periods.value.length) {
      for (let index = 0; index < operatingRows.length; index += periodDefaults.years) {
        periods.value.push({
          start_year: operatingRows[index]!.year,
          end_year: operatingRows[Math.min(index + periodDefaults.years - 1, operatingRows.length - 1)]!.year,
          ratio: Number((periodDefaults.first_ratio + index / periodDefaults.years * periodDefaults.ratio_step).toFixed(6)),
        })
      }
    }
    annualRows.value = source.schedule.map(row => {
      const amounts = Object.fromEntries(annualCostFields.map(name => {
        const field = fieldsByName.value.get(name)
        const knownValues = field?.value
        const value = Array.isArray(knownValues) ? knownValues[row.year - 1] : field?.annualDefault ?? ''
        return [name, row.phase === '建设期' ? 0 : value]
      })) as Record<AnnualCostField, number | string>
      return { year: row.year, phase: row.phase, ...amounts }
    })
  }, { immediate: true })

  function applyToOperatingYears(row: AnnualInputRow) {
    for (const target of annualRows.value) {
      if (target.phase === '运营期') {
        for (const name of annualCostFields) target[name] = row[name]
      }
    }
  }

  function addPeriod() {
    const last = periods.value.at(-1)
    const example = fieldsByName.value.get('maintenance_ratio_periods')!.periodDefaults!
    const firstYear = loan.value!.schedule.find(row => row.phase === '运营期')!.year
    periods.value.push({
      start_year: last ? last.end_year + 1 : firstYear,
      end_year: last ? last.end_year + example.years : firstYear + example.years - 1,
      ratio: last ? last.ratio : example.first_ratio,
    })
  }

  function buildInputs(): CostScheduleInputs {
    const annualValues = Object.fromEntries(annualCostFields.map(name => [
      name, annualRows.value.map(row => Number(row[name])),
    ])) as Record<AnnualCostField, number[]>
    return {
      equipment_total_cost: Number(equipmentTotalCost.value),
      depreciation_years: Number(depreciationYears.value),
      maintenance_ratio_periods: periods.value.map(period => ({
        start_year: Number(period.start_year), end_year: Number(period.end_year), ratio: Number(period.ratio),
      })),
      ...annualValues,
    }
  }

  return {
    loan, equipmentTotalCost, depreciationYears,
    periods, annualRows, fieldsByName, addPeriod, applyToOperatingYears, buildInputs,
  }
}
