"""手动运行借款还本付息计算，并打印年度结果。"""

from unicodedata import east_asian_width

from heatcalc.finance import calculate_loan_schedule


def display_width(value: str) -> int:
    """计算字符串在终端中的显示宽度。"""
    return sum(
        2 if east_asian_width(char) in {"W", "F"} else 1
        for char in value
    )


def align_left(value: object, width: int) -> str:
    """按显示宽度左对齐文本。"""
    text = str(value)
    return text + " " * max(0, width - display_width(text))


def align_right(value: object, width: int) -> str:
    """按显示宽度右对齐文本。"""
    text = str(value)
    return " " * max(0, width - display_width(text)) + text


def main() -> None:
    # 图片中的项目输入，金额单位为万元，利率和比例使用小数。
    inputs = {
        "static_investment": 31151.0,              # 静态投资
        "loan_ratio": 0.80,                        # 贷款比例
        "investment_interest_rate": 0.03,          # 投资贷款利率
        "construction_interest_rate": 0.03,        # 建设期贷款利率
        "construction_years": 2,                   # 建设期年数
        "first_drawdown_ratio": 0.80,              # 第一次贷款比例
        "second_drawdown_year": 2,                 # 第二次贷款年份
        "repayment_years": 15,                     # 还本期
        "schedule_years": 30,                      # 表内列示年数
    }
    result = calculate_loan_schedule(**inputs)  # 计算结果
    summary = result["summary"]  # 汇总结果
    schedule = result["schedule"]  # 逐年明细

    print("=== 输入参数 ===")
    for name, value in inputs.items():
        print(f"{name}: {value:.4f}" if name == "static_investment" else f"{name}: {value}")

    print("\n=== 汇总结果 ===")
    for name, value in summary.items():
        print(f"{name}: {value}" if name == "repayment_end_year" else f"{name}: {value:.4f}")

    print("\n=== 年度明细 ===")
    headers = [
        align_right("年份", 4),
        align_left("阶段", 8),
        align_right("年初余额", 14),
        align_right("新增借款", 14),
        align_right("偿还本金", 14),
        align_right("当年利息", 14),
        align_right("年末余额", 14),
    ]
    print("  ".join(headers))

    for row in schedule:
        columns = [
            align_right(row["year"], 4),
            align_left(row["phase"], 8),
            align_right(f"{row['beginning_balance']:.4f}", 14),
            align_right(f"{row['new_borrowing']:.4f}", 14),
            align_right(f"{row['principal_repayment']:.4f}", 14),
            align_right(f"{row['interest_expense']:.4f}", 14),
            align_right(f"{row['ending_balance']:.4f}", 14),
        ]
        print("  ".join(columns))


if __name__ == "__main__":
    main()
