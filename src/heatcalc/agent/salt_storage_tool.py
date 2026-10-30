"""热源共用的熔盐储量工具。"""

from math import isfinite

from langchain_core.tools import tool
from pydantic import Field

from heatcalc.agent.common_inputs import SaltInputs

from heatcalc.thermal_storage import molten_salt


class SaltStorageInputs(SaltInputs):
    """熔盐储量计算输入。"""

    # 热泵基础参数
    charging_power: float = Field(
        description="充热端热功率",
        json_schema_extra={"unit": "kW", "group": "储热系统参数"},
    )

    # 储热系统参数
    storage_duration: float = Field(
        description="储热时长",
        json_schema_extra={"unit": "h", "group": "储热系统参数"},
    )


@tool(args_schema=SaltStorageInputs)
def calculate_salt_mass(
    charging_power: float,
    storage_duration: float,
    salt_specific_heat: float,
    salt_temp_high: float,
    salt_temp_low: float,
) -> dict[str, float]:
    """根据充热端热功率、储热时长和熔盐物性，计算所需熔盐质量。

    可以使用电加热器或热泵计算结果中的 charging_power，输入单位为 kW。

    :param charging_power: 充热端热功率 (kW)，若给定 MW，需乘以 1000
    :param storage_duration: 按充热功率配置的储热容量时长 (h)
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)，必须高于最低温度
    :param salt_temp_low: 熔盐最低温度 (°C)
    :return: 包含 salt_mass 的字典，熔盐质量单位为吨
    """
    if not isfinite(salt_temp_high) or not isfinite(salt_temp_low):
        raise ValueError("熔盐最高温度和最低温度必须是有限数值")

    salt_mass = molten_salt.calculate_salt_mass(
        charging_power=charging_power,
        storage_duration=storage_duration,
        salt_specific_heat=salt_specific_heat,
        salt_temp_delta=salt_temp_high - salt_temp_low,
    )
    return {"salt_mass": salt_mass}
