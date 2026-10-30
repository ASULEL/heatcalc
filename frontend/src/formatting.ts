export const MONEY_DECIMALS = 4 // 金额展示精度，方案保留原始数值

export function formatMoney(value: number | string): string {
  return Number(value).toFixed(MONEY_DECIMALS)
}
