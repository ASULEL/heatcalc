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
  const values = ref<Record<string, string>>({}) // 标量参数，按显示单位保存
  const periods = ref<MaintenanceRatioPeriod[]>([]) // 可编辑的维修费比例区间
  const annualRows = ref<AnnualInputRow[]>([]) // 各项目年份的输入费用
  const fieldsByName = computed(() => new Map(fields.value.map(field => [field.name, field])))
  const scalarFields = computed(() => fields.value.filter(field =>
    !annualCostFields.includes(field.name as AnnualCostField) && field.name !== 'maintenance_ratio_periods',
  ))
  const coreFields = computed(() => scalarFields.value.filter(field => field.group === '计算口径'))
  const coefficientFields = computed(() => scalarFields.value.filter(field => field.group === '计价系数'))
  const constructionYears = computed(() => loan.value.schedule.filter(row => row.phase === '建设期').length)
  const operatingYears = computed(() => Number(values.value.operating_years) || 0)
  const activeEndYear = computed(() => constructionYears.value + operatingYears.value)

  watch(fields, () => {
    values.value = Object.fromEntries(scalarFields.value.map(field => [
      field.name, field.value == null ? '' : String(field.value),
    ]))
  }, { immediate: true })

  watch([loan, fields], () => {
    const source = loan.value // 当前方案固定的借款表
    const operatingRows = source.schedule.filter(row => row.phase === '运营期')
    // 运营年数不能超过本方案借款表的运营年份。
    if (Number(values.value.operating_years) > operatingRows.length) {
      values.value.operating_years = String(operatingRows.length)
    }
    const activeRows = operatingRows.slice(0, operatingYears.value || operatingRows.length)
    const knownPeriods = fieldsByName.value.get('maintenance_ratio_periods')?.value
    const periodDefaults = fieldsByName.value.get('maintenance_ratio_periods')!.periodDefaults! // Excel 的区间示例

    // 默认每5个运营年一段，从 0.003 起每段增加 0.002；用户可修改起止年份和比例。
    periods.value = Array.isArray(knownPeriods) ? knownPeriods.map(period => ({ ...period })) : []
    if (!periods.value.length) {
      for (let index = 0; index < activeRows.length; index += periodDefaults.years) {
        periods.value.push({
          start_year: activeRows[index]!.year,
          end_year: activeRows[Math.min(index + periodDefaults.years - 1, activeRows.length - 1)]!.year,
          ratio: Number((periodDefaults.first_ratio + index / periodDefaults.years * periodDefaults.ratio_step).toFixed(6)),
        })
      }
    }
    annualRows.value = source.schedule.map(row => {
      const amounts = Object.fromEntries(annualCostFields.map(name => {
        const field = fieldsByName.value.get(name)
        const knownValues = field?.value
        const value = Array.isArray(knownValues) ? knownValues[row.year - 1] : field?.annualDefault ?? ''
        const inactive = row.phase === '建设期' || row.year > activeEndYear.value
        return [name, inactive ? 0 : value]
      })) as Record<AnnualCostField, number | string>
      return { year: row.year, phase: row.phase, ...amounts }
    })
  }, { immediate: true })

  // 运营年数改动后，超出范围的年份与 Excel 一致填0。
  watch(operatingYears, (years) => {
    const available = loan.value.schedule.filter(row => row.phase === '运营期').length
    if (years > available) {
      values.value.operating_years = String(available) // 不超过本方案借款表的运营年份
      return
    }
    if (years < 1) return // 清空输入框时不改动已填费用
    for (const row of annualRows.value) {
      if (row.phase === '运营期' && row.year > activeEndYear.value) {
        for (const name of annualCostFields) row[name] = 0
      }
    }
  })

  function applyToOperatingYears(row: AnnualInputRow) {
    for (const target of annualRows.value) {
      if (target.phase === '运营期' && target.year <= activeEndYear.value) {
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

  function toToolValue(value: string, factor: number) {
    return Number((Number(value) * factor).toFixed(10)) // 消除百分数换算的浮点尾差
  }

  function buildInputs(): CostScheduleInputs {
    const scalars = Object.fromEntries(scalarFields.value.map(field => [
      field.name, toToolValue(values.value[field.name] ?? '', field.toToolFactor ?? 1),
    ])) as unknown as Omit<CostScheduleInputs, AnnualCostField | 'maintenance_ratio_periods'>
    const annualValues = Object.fromEntries(annualCostFields.map(name => [
      name, annualRows.value.map(row => Number(row[name])),
    ])) as Record<AnnualCostField, number[]>
    return {
      ...scalars,
      maintenance_ratio_periods: periods.value.map(period => ({
        start_year: Number(period.start_year), end_year: Number(period.end_year), ratio: Number(period.ratio),
      })),
      ...annualValues,
    }
  }

  return {
    loan, values, scalarFields, coreFields, coefficientFields,
    periods, annualRows, fieldsByName, addPeriod, applyToOperatingYears, buildInputs,
  }
}
