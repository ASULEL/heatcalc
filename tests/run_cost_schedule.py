"""手动运行图片中的成本计算：.venv/bin/python tests/run_cost_schedule.py。"""

from heatcalc.finance import DEFAULT_LOAN_SCHEDULE_INPUTS, calculate_loan_schedule
from heatcalc.finance import calculate_cost_schedule
from run_bank_loan_schedule import align_left, align_right, display_width


def align_center(value: str, width: int) -> str:
    """按终端显示宽度居中分组标题。"""
    left_padding = (width - display_width(value)) // 2  # 标题左侧空格数
    return align_left(" " * left_padding + value, width)


def main() -> None:
    loan_inputs = {**DEFAULT_LOAN_SCHEDULE_INPUTS, "second_drawdown_year": 2}  # 借款输入
    loan_result = calculate_loan_schedule(**loan_inputs)  # 原始借款结果
    inputs = {  # 成本输入，所有金额为万元，年度列表从项目第1年开始
        "loan_schedule": loan_result,
        "equipment_total_cost": 26400.0,  # 设备总成本，万元
        "depreciation_years": 20,  # 折旧年限，年
        "maintenance_ratio_periods": [  # 可修改的维修费区间
            {"start_year": 3, "end_year": 7, "ratio": 0.003},
            {"start_year": 8, "end_year": 12, "ratio": 0.005},
            {"start_year": 13, "end_year": 17, "ratio": 0.007},
            {"start_year": 18, "end_year": 22, "ratio": 0.009},
            {"start_year": 23, "end_year": 27, "ratio": 0.011},
            {"start_year": 28, "end_year": 30, "ratio": 0.013},
        ],
        "total_electricity_by_year": [0.0] * 2 + [2390.4133] * 28,  # 含税电费
        "water_cost_by_year": [0.0] * 30,  # 水费
        "labor_cost_by_year": [0.0] * 2 + [216.0] * 28,  # 人工费
        "amortization_expense_by_year": [0.0] * 30,  # 摊销费，暂手动输入
        "working_capital_loan_interest_by_year": [0.0] * 30,  # 流动资金利息，暂手动输入
    }
    result = calculate_cost_schedule(**inputs)  # 成本汇总和年度明细
    groups = [  # 分组名称及组内字段、中文表头、显示宽度
        ("", [
            ("year", "年份", 4), ("maintenance_ratio", "维修费比例", 10),
        ]),
        ("经营成本", [
            ("electricity_cost", "电费", 12), ("water_cost", "水费", 10),
            ("labor_cost", "人工费", 10), ("insurance_cost", "保险费", 10),
            ("maintenance_cost", "维修费", 10),
        ]),
        ("折旧摊销", [
            ("depreciation_cost", "折旧费", 12),
            ("amortization_expense", "摊销费", 10),
        ]),
        ("财务成本", [
            ("long_term_loan_interest", "长期借款利息", 14),
            ("working_capital_loan_interest", "流动资金借款利息", 18),
        ]),
        ("", [("total_cost", "总成本", 12)]),
    ]
    group_widths = [  # 各组列宽，包含组内列间空格
        sum(width for _, _, width in columns) + 2 * (len(columns) - 1)
        for _, columns in groups
    ]

    formats = {"year": "d", "maintenance_ratio": ".6f"}  # 年份与比例格式，金额统一四位小数

    print("成本计算表，金额单位：万元")
    for label, columns in groups:
        if label:
            print(f"{label}：{' + '.join(title for _, title, _ in columns)}")
    print("总成本 = 经营成本 + 折旧摊销 + 财务成本\n")

    print(" │ ".join(
        align_center(label, width)
        for (label, _), width in zip(groups, group_widths)
    ))
    print(" │ ".join(
        "  ".join(align_right(label, width) for _, label, width in columns)
        for _, columns in groups
    ))
    print("─┼─".join("─" * width for width in group_widths))
    for row in result["schedule"]:
        print(" │ ".join(
            "  ".join(
                align_right(format(row[name], formats.get(name, ".4f")), width)
                for name, _, width in columns
            )
            for _, columns in groups
        ))
    print("\n当年利息列：[" + ", ".join(f"{row['long_term_loan_interest']:.4f}" for row in result["schedule"]) + "]")
    print("总成本列：[" + ", ".join(f"{row['total_cost']:.4f}" for row in result["schedule"]) + "]")
    print("\n全周期成本汇总，单位：万元")
    print(f"经营成本合计：{result['summary']['operating_cost_total']:.4f}")
    print(f"折旧摊销合计：{result['summary']['depreciation_amortization_total']:.4f}")
    print(f"财务成本合计：{result['summary']['financial_cost_total']:.4f}")
    print(f"总成本合计：{result['summary']['total_cost']:.4f}")


if __name__ == "__main__":
    main()
