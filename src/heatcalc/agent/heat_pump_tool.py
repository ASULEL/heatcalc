"""热泵计算工具。"""

from langchain_core.tools import tool
from pydantic import BaseModel, ConfigDict, Field

from heatcalc.agent.common_inputs import HeatSourceInputs
from heatcalc.heat_source.cop import calculate_cop
from heatcalc.heat_source.heat_pump import HeatPumpStrategy


class HeatPumpCycleInputs(BaseModel):
    """热泵循环参数，按设备分段排列；工具压力单位为 kPa。"""

    # 热泵基础参数
    waste_heat_temp: float = Field(
        description="余热温度",
        json_schema_extra={"unit": "°C", "group": "热泵基础参数"},
    )
    working_fluid: str = Field(
        description="循环介质",
        json_schema_extra={"unit": "名称", "group": "热泵基础参数", "options": [{"value": "air", "label": "air（空气）"}]},
    )

    # 压缩机参数
    compressor_inlet_pressure: float = Field(
        description="压缩机进口压力",
        json_schema_extra={
            "unit": "kPa", "group": "压缩机参数", "advanced": True,
            "display_unit": "MPa", "toToolFactor": 1000,
        },
    )
    compressor_outlet_pressure: float = Field(
        description="压缩机出口压力",
        json_schema_extra={
            "unit": "kPa", "group": "压缩机参数", "advanced": True,
            "display_unit": "MPa", "toToolFactor": 1000,
        },
    )
    compressor_isentropic_efficiency: float = Field(
        description="压缩机等熵效率",
        json_schema_extra={"unit": "小数", "group": "压缩机参数", "advanced": True},
    )
    compressor_mechanical_loss: float = Field(
        description="压缩机机械损失功率",
        json_schema_extra={"unit": "kW", "group": "压缩机参数", "advanced": True},
    )

    # 放热器参数
    compressor_to_heat_release_pressure_drop: float = Field(
        description="压缩机至放热器管道压损",
        json_schema_extra={"unit": "kPa", "group": "放热器参数", "advanced": True},
    )
    heat_release_temp_approach: float = Field(
        description="放热器端差",
        json_schema_extra={"unit": "°C", "group": "放热器参数", "advanced": True},
    )
    heat_release_pressure_drop: float = Field(
        description="放热器压损",
        json_schema_extra={"unit": "kPa", "group": "放热器参数", "advanced": True},
    )
    heat_release_to_regenerator_pressure_drop: float = Field(
        description="放热器至回热器管道压损",
        json_schema_extra={"unit": "kPa", "group": "放热器参数", "advanced": True},
    )

    # 回热器参数
    regenerator_temp_approach: float = Field(
        description="回热器端差",
        json_schema_extra={"unit": "°C", "group": "回热器参数", "advanced": True},
    )
    regenerator_high_side_pressure_drop: float = Field(
        description="回热器高压侧压损",
        json_schema_extra={"unit": "kPa", "group": "回热器参数", "advanced": True},
    )
    regenerator_low_side_pressure_drop: float = Field(
        description="回热器低压侧压损",
        json_schema_extra={"unit": "kPa", "group": "回热器参数", "advanced": True},
    )

    # 膨胀机参数
    regenerator_to_expander_pressure_drop: float = Field(
        description="回热器至膨胀机管道压损",
        json_schema_extra={"unit": "kPa", "group": "膨胀机参数", "advanced": True},
    )
    expander_outlet_pressure: float = Field(
        description="膨胀机出口压力",
        json_schema_extra={
            "unit": "kPa", "group": "膨胀机参数", "advanced": True,
            "display_unit": "MPa", "toToolFactor": 1000,
        },
    )
    expander_isentropic_efficiency: float = Field(
        description="膨胀机等熵效率",
        json_schema_extra={"unit": "小数", "group": "膨胀机参数", "advanced": True},
    )
    expander_mechanical_loss: float = Field(
        description="膨胀机机械损失功率",
        json_schema_extra={"unit": "kW", "group": "膨胀机参数", "advanced": True},
    )

    # 吸热器参数
    expander_to_heat_absorption_pressure_drop: float = Field(
        description="膨胀机至吸热器管道压损",
        json_schema_extra={"unit": "kPa", "group": "吸热器参数", "advanced": True},
    )
    heat_absorption_temp_approach: float = Field(
        description="吸热器端差",
        json_schema_extra={"unit": "°C", "group": "吸热器参数", "advanced": True},
    )
    heat_absorption_pressure_drop: float = Field(
        description="吸热器压损",
        json_schema_extra={"unit": "kPa", "group": "吸热器参数", "advanced": True},
    )
    heat_absorption_to_regenerator_pressure_drop: float = Field(
        description="吸热器至回热器管道压损",
        json_schema_extra={"unit": "kPa", "group": "吸热器参数", "advanced": True},
    )

    # 传动与连接参数
    regenerator_to_compressor_pressure_drop: float = Field(
        description="回热器至压缩机管道压损",
        json_schema_extra={"unit": "kPa", "group": "传动与连接参数", "advanced": True},
    )
    motor_efficiency: float = Field(
        description="电动机效率",
        json_schema_extra={"unit": "小数", "group": "传动与连接参数", "advanced": True},
    )
    gearbox_efficiency: float = Field(
        description="齿轮箱效率",
        json_schema_extra={"unit": "小数", "group": "传动与连接参数", "advanced": True},
    )


class HeatPumpCostInputs(HeatSourceInputs, HeatPumpCycleInputs):
    """热泵按蒸汽需求计算购电成本的输入。"""

    # 蒸汽与供热参数
    mass_flow: float = Field(
        description="蒸汽质量流量",
        json_schema_extra={"unit": "kg/s", "group": "蒸汽与供热参数"},
    )


class HeatPumpFlowInputs(HeatSourceInputs, HeatPumpCycleInputs):
    """热泵按购电预算计算蒸汽流量的输入。"""

    # 电价与预算参数
    electricity_cost: float = Field(
        description="指定购电成本",
        json_schema_extra={"unit": "元", "group": "电价与预算参数"},
    )


class HeatPumpCopInputs(HeatPumpCycleInputs):
    """独立 COP 计算；示例只用于表单预填，参数仍须明确提交。"""

    model_config = ConfigDict(
        json_schema_extra={
            # Excel 示例采用前端显示单位：压力 MPa，热功率 MWt。
            "form_defaults": {
                "working_fluid": "air",
                "waste_heat_temp": 400,
                "salt_temp_low": 310,
                "charging_power": 100,
                "compressor_inlet_pressure": 2.7,
                "compressor_outlet_pressure": 11.5,
                "compressor_isentropic_efficiency": 0.85,
                "heat_release_temp_approach": 10,
                "heat_release_pressure_drop": 200,
                "heat_release_to_regenerator_pressure_drop": 0,
                "regenerator_temp_approach": 20,
                "regenerator_high_side_pressure_drop": 200,
                "regenerator_low_side_pressure_drop": 200,
                "regenerator_to_expander_pressure_drop": 0,
                "expander_outlet_pressure": 2.95,
                "expander_isentropic_efficiency": 0.92,
                "expander_mechanical_loss": 0,
                "expander_to_heat_absorption_pressure_drop": 0,
                "heat_absorption_temp_approach": 130,
                "heat_absorption_pressure_drop": 50,
                "motor_efficiency": 0.98,
                "gearbox_efficiency": 0.985,
            },
        },
    )

    # 储热系统参数
    salt_temp_low: float = Field(
        description="熔盐最低温度",
        json_schema_extra={"unit": "°C", "group": "储热系统参数"},
    )

    # 热泵基础参数
    charging_power: float = Field(
        description="热泵输出热功率",
        json_schema_extra={"unit": "kW", "group": "热泵基础参数", "display_unit": "MWt", "toToolFactor": 1000},
    )


@tool(args_schema=HeatPumpCostInputs)
def calculate_heat_pump_cost(
        steam_pressure: float,
        steam_temp: float,
        feedwater_pressure: float,
        feedwater_temp: float,
        mass_flow: float,
        operating_hours: float,
        electricity_price: float,
        heat_exchange_efficiency: float,
        storage_efficiency: float,
        salt_specific_heat: float,
        salt_temp_high: float,
        salt_temp_low: float,
        waste_heat_temp: float,
        steam_supply_hours: float,
        working_fluid: str,
        compressor_inlet_pressure: float,
        compressor_outlet_pressure: float,
        compressor_isentropic_efficiency: float,
        compressor_mechanical_loss: float,
        compressor_to_heat_release_pressure_drop: float,
        heat_release_temp_approach: float,
        heat_release_pressure_drop: float,
        heat_release_to_regenerator_pressure_drop: float,
        regenerator_temp_approach: float,
        regenerator_high_side_pressure_drop: float,
        regenerator_low_side_pressure_drop: float,
        regenerator_to_expander_pressure_drop: float,
        expander_outlet_pressure: float,
        expander_isentropic_efficiency: float,
        expander_mechanical_loss: float,
        expander_to_heat_absorption_pressure_drop: float,
        heat_absorption_temp_approach: float,
        heat_absorption_pressure_drop: float,
        heat_absorption_to_regenerator_pressure_drop: float,
        regenerator_to_compressor_pressure_drop: float,
        motor_efficiency: float,
        gearbox_efficiency: float,
) -> dict[str, float]:
    """
    根据蒸汽需求和循环参数计算供热 COP，再计算热泵的购电成本。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。
    循环参数均须由用户提供，缺少参数时先向用户询问，不能代入示例或默认值。

    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :param mass_flow: 蒸汽质量流量 (kg/s)，若给定 t/h，需除以 3.6
    :param operating_hours: 谷电充热时长 (h)，必须大于零
    :param electricity_price: 电价 (元/kWh)
    :param heat_exchange_efficiency: 换热效率，大于 0 且不超过 1
    :param storage_efficiency: 储热效率，大于 0 且不超过 1
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)
    :param salt_temp_low: 熔盐最低温度 (°C)，必须低于最高温度
    :param waste_heat_temp: 余热温度 (°C)
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :param working_fluid: 循环介质的 CoolProp 名称，如 Air、Nitrogen
    :param compressor_inlet_pressure: 兼容原字段 (kPa)，实际进口压力由回热器低压侧出口减去管道压降推导
    :param compressor_outlet_pressure: 压缩机出口压力 (kPa)
    :param compressor_isentropic_efficiency: 压缩机等熵效率，使用小数
    :param compressor_mechanical_loss: 压缩机机械损失功率 (kW)
    :param compressor_to_heat_release_pressure_drop: 压缩机出口至放热器进口管道压降 (kPa)
    :param heat_release_temp_approach: 放热器端差 (°C)
    :param heat_release_pressure_drop: 放热器压降 (kPa)
    :param heat_release_to_regenerator_pressure_drop: 放热器出口至回热器高压侧进口管道压降 (kPa)
    :param regenerator_temp_approach: 回热器端差 (°C)
    :param regenerator_high_side_pressure_drop: 回热器高压侧压降 (kPa)
    :param regenerator_low_side_pressure_drop: 回热器低压侧压降 (kPa)
    :param regenerator_to_expander_pressure_drop: 回热器高压侧出口至膨胀机进口管道压降 (kPa)
    :param expander_outlet_pressure: 膨胀机出口压力 (kPa)
    :param expander_isentropic_efficiency: 膨胀机等熵效率，使用小数
    :param expander_mechanical_loss: 膨胀机机械损失功率 (kW)
    :param expander_to_heat_absorption_pressure_drop: 膨胀机出口至吸热器进口管道压降 (kPa)
    :param heat_absorption_temp_approach: 吸热器端差 (°C)
    :param heat_absorption_pressure_drop: 吸热器压降 (kPa)
    :param heat_absorption_to_regenerator_pressure_drop: 吸热器出口至回热器低压侧进口管道压降 (kPa)
    :param regenerator_to_compressor_pressure_drop: 回热器低压侧出口至压缩机进口管道压降 (kPa)
    :param motor_efficiency: 电动机效率，使用小数
    :param gearbox_efficiency: 齿轮箱效率，使用小数
    :return: 包含各阶段功率 (kW)、耗电量 (kWh)、购电成本 (元)、
             供热量 (kWh) 和供热 COP（无量纲）的字典
    """
    # 1.先创建热泵实体
    salt_temp_delta = salt_temp_high - salt_temp_low
    heat_pump_strategy = HeatPumpStrategy(
        waste_heat_temp=waste_heat_temp,
        heat_exchange_efficiency=heat_exchange_efficiency,
        storage_efficiency=storage_efficiency,
        salt_specific_heat=salt_specific_heat,
        salt_temp_delta=salt_temp_delta,
        salt_temp_low=salt_temp_low,
        cop_parameters={
            "working_fluid": working_fluid,
            "compressor_inlet_pressure": compressor_inlet_pressure,
            "compressor_outlet_pressure": compressor_outlet_pressure,
            "compressor_isentropic_efficiency": compressor_isentropic_efficiency,
            "compressor_mechanical_loss": compressor_mechanical_loss,
            "compressor_to_heat_release_pressure_drop": compressor_to_heat_release_pressure_drop,
            "heat_release_temp_approach": heat_release_temp_approach,
            "heat_release_pressure_drop": heat_release_pressure_drop,
            "heat_release_to_regenerator_pressure_drop": heat_release_to_regenerator_pressure_drop,
            "regenerator_temp_approach": regenerator_temp_approach,
            "regenerator_high_side_pressure_drop": regenerator_high_side_pressure_drop,
            "regenerator_low_side_pressure_drop": regenerator_low_side_pressure_drop,
            "regenerator_to_expander_pressure_drop": regenerator_to_expander_pressure_drop,
            "expander_outlet_pressure": expander_outlet_pressure,
            "expander_isentropic_efficiency": expander_isentropic_efficiency,
            "expander_mechanical_loss": expander_mechanical_loss,
            "expander_to_heat_absorption_pressure_drop": expander_to_heat_absorption_pressure_drop,
            "heat_absorption_temp_approach": heat_absorption_temp_approach,
            "heat_absorption_pressure_drop": heat_absorption_pressure_drop,
            "heat_absorption_to_regenerator_pressure_drop": heat_absorption_to_regenerator_pressure_drop,
            "regenerator_to_compressor_pressure_drop": regenerator_to_compressor_pressure_drop,
            "motor_efficiency": motor_efficiency,
            "gearbox_efficiency": gearbox_efficiency,
        },
    )
    # 2.调用热泵策略计算购电成本
    return heat_pump_strategy.calculate_cost_from_steam(
        steam_pressure=steam_pressure,
        steam_temp=steam_temp,
        feedwater_pressure=feedwater_pressure,
        feedwater_temp=feedwater_temp,
        mass_flow=mass_flow,
        operating_hours=operating_hours,
        electricity_price=electricity_price,
        steam_supply_hours=steam_supply_hours,
    )


@tool(args_schema=HeatPumpFlowInputs)
def calculate_heat_pump_mass_flow(
    steam_pressure: float,
    steam_temp: float,
    feedwater_pressure: float,
    feedwater_temp: float,
    operating_hours: float,
    electricity_price: float,
    heat_exchange_efficiency: float,
    storage_efficiency: float,
    salt_specific_heat: float,
    salt_temp_high: float,
    salt_temp_low: float,
    waste_heat_temp: float,
    electricity_cost: float,
    steam_supply_hours: float,
    working_fluid: str,
    compressor_inlet_pressure: float,
    compressor_outlet_pressure: float,
    compressor_isentropic_efficiency: float,
    compressor_mechanical_loss: float,
    compressor_to_heat_release_pressure_drop: float,
    heat_release_temp_approach: float,
    heat_release_pressure_drop: float,
    heat_release_to_regenerator_pressure_drop: float,
    regenerator_temp_approach: float,
    regenerator_high_side_pressure_drop: float,
    regenerator_low_side_pressure_drop: float,
    regenerator_to_expander_pressure_drop: float,
    expander_outlet_pressure: float,
    expander_isentropic_efficiency: float,
    expander_mechanical_loss: float,
    expander_to_heat_absorption_pressure_drop: float,
    heat_absorption_temp_approach: float,
    heat_absorption_pressure_drop: float,
    heat_absorption_to_regenerator_pressure_drop: float,
    regenerator_to_compressor_pressure_drop: float,
    motor_efficiency: float,
    gearbox_efficiency: float,
) -> dict[str, float]:
    """根据指定购电成本和循环参数，计算热泵能够供给的蒸汽质量流量。

    谷电充热时长和供汽时长需要分别提供，不能默认两者相同。
    循环参数均须由用户提供，缺少参数时先向用户询问，不能代入示例或默认值。

    :param steam_pressure: 蒸汽压力 (MPa)
    :param steam_temp: 蒸汽温度 (°C)
    :param feedwater_pressure: 给水压力 (MPa)
    :param feedwater_temp: 给水温度 (°C)
    :param operating_hours: 谷电充热时长 (h)，必须大于零
    :param electricity_price: 电价 (元/kWh)，必须大于零
    :param heat_exchange_efficiency: 换热效率，大于 0 且不超过 1
    :param storage_efficiency: 储热效率，大于 0 且不超过 1
    :param salt_specific_heat: 熔盐比热容 (kJ/(kg·K))
    :param salt_temp_high: 熔盐最高温度 (°C)
    :param salt_temp_low: 熔盐最低温度 (°C)，必须低于最高温度
    :param waste_heat_temp: 余热温度 (°C)
    :param electricity_cost: 指定购电成本 (元)，允许为零
    :param steam_supply_hours: 供汽时长 (h)，必须大于零
    :param working_fluid: 循环介质的 CoolProp 名称，如 Air、Nitrogen
    :param compressor_inlet_pressure: 兼容原字段 (kPa)，实际进口压力由回热器低压侧出口减去管道压降推导
    :param compressor_outlet_pressure: 压缩机出口压力 (kPa)
    :param compressor_isentropic_efficiency: 压缩机等熵效率，使用小数
    :param compressor_mechanical_loss: 压缩机机械损失功率 (kW)
    :param compressor_to_heat_release_pressure_drop: 压缩机出口至放热器进口管道压降 (kPa)
    :param heat_release_temp_approach: 放热器端差 (°C)
    :param heat_release_pressure_drop: 放热器压降 (kPa)
    :param heat_release_to_regenerator_pressure_drop: 放热器出口至回热器高压侧进口管道压降 (kPa)
    :param regenerator_temp_approach: 回热器端差 (°C)
    :param regenerator_high_side_pressure_drop: 回热器高压侧压降 (kPa)
    :param regenerator_low_side_pressure_drop: 回热器低压侧压降 (kPa)
    :param regenerator_to_expander_pressure_drop: 回热器高压侧出口至膨胀机进口管道压降 (kPa)
    :param expander_outlet_pressure: 膨胀机出口压力 (kPa)
    :param expander_isentropic_efficiency: 膨胀机等熵效率，使用小数
    :param expander_mechanical_loss: 膨胀机机械损失功率 (kW)
    :param expander_to_heat_absorption_pressure_drop: 膨胀机出口至吸热器进口管道压降 (kPa)
    :param heat_absorption_temp_approach: 吸热器端差 (°C)
    :param heat_absorption_pressure_drop: 吸热器压降 (kPa)
    :param heat_absorption_to_regenerator_pressure_drop: 吸热器出口至回热器低压侧进口管道压降 (kPa)
    :param regenerator_to_compressor_pressure_drop: 回热器低压侧出口至压缩机进口管道压降 (kPa)
    :param motor_efficiency: 电动机效率，使用小数
    :param gearbox_efficiency: 齿轮箱效率，使用小数
    :return: 各阶段计算结果及 mass_flow (kg/s)，供热 COP 无量纲
    """
    heat_pump_strategy = HeatPumpStrategy(
        waste_heat_temp=waste_heat_temp,
        heat_exchange_efficiency=heat_exchange_efficiency,
        storage_efficiency=storage_efficiency,
        salt_specific_heat=salt_specific_heat,
        salt_temp_delta=salt_temp_high - salt_temp_low,
        salt_temp_low=salt_temp_low,
        cop_parameters={
            "working_fluid": working_fluid,
            "compressor_inlet_pressure": compressor_inlet_pressure,
            "compressor_outlet_pressure": compressor_outlet_pressure,
            "compressor_isentropic_efficiency": compressor_isentropic_efficiency,
            "compressor_mechanical_loss": compressor_mechanical_loss,
            "compressor_to_heat_release_pressure_drop": compressor_to_heat_release_pressure_drop,
            "heat_release_temp_approach": heat_release_temp_approach,
            "heat_release_pressure_drop": heat_release_pressure_drop,
            "heat_release_to_regenerator_pressure_drop": heat_release_to_regenerator_pressure_drop,
            "regenerator_temp_approach": regenerator_temp_approach,
            "regenerator_high_side_pressure_drop": regenerator_high_side_pressure_drop,
            "regenerator_low_side_pressure_drop": regenerator_low_side_pressure_drop,
            "regenerator_to_expander_pressure_drop": regenerator_to_expander_pressure_drop,
            "expander_outlet_pressure": expander_outlet_pressure,
            "expander_isentropic_efficiency": expander_isentropic_efficiency,
            "expander_mechanical_loss": expander_mechanical_loss,
            "expander_to_heat_absorption_pressure_drop": expander_to_heat_absorption_pressure_drop,
            "heat_absorption_temp_approach": heat_absorption_temp_approach,
            "heat_absorption_pressure_drop": heat_absorption_pressure_drop,
            "heat_absorption_to_regenerator_pressure_drop": heat_absorption_to_regenerator_pressure_drop,
            "regenerator_to_compressor_pressure_drop": regenerator_to_compressor_pressure_drop,
            "motor_efficiency": motor_efficiency,
            "gearbox_efficiency": gearbox_efficiency,
        },
    )
    return heat_pump_strategy.calculate_mass_flow_from_cost(
        steam_pressure=steam_pressure,
        steam_temp=steam_temp,
        feedwater_pressure=feedwater_pressure,
        feedwater_temp=feedwater_temp,
        operating_hours=operating_hours,
        electricity_price=electricity_price,
        electricity_cost=electricity_cost,
        steam_supply_hours=steam_supply_hours,
    )


@tool(args_schema=HeatPumpCopInputs)
def calculate_heat_pump_cop(
        *,
        working_fluid: str,  # E2
        waste_heat_temp: float,  # E4
        salt_temp_low: float,  # E5
        charging_power: float,  # E9，接口单位为 kW

        # 压缩机
        compressor_inlet_pressure: float,  # E11，接口单位为 kPa
        compressor_outlet_pressure: float,  # E14，接口单位为 kPa
        compressor_isentropic_efficiency: float,  # E17
        compressor_mechanical_loss: float,  # E20

        # 放热器及连接管道
        compressor_to_heat_release_pressure_drop: float,  # E21
        heat_release_temp_approach: float,  # E22
        heat_release_pressure_drop: float,  # E29
        heat_release_to_regenerator_pressure_drop: float,  # E31

        # 回热器
        regenerator_temp_approach: float,  # E32
        regenerator_high_side_pressure_drop: float,  # E39
        regenerator_low_side_pressure_drop: float,  # E46

        # 膨胀机及连接管道
        regenerator_to_expander_pressure_drop: float,  # E48
        expander_outlet_pressure: float,  # E52，当前为公式；接口单位为 kPa
        expander_isentropic_efficiency: float,  # E55
        expander_mechanical_loss: float,  # E58

        # 吸热器及连接管道
        expander_to_heat_absorption_pressure_drop: float,  # E59
        heat_absorption_temp_approach: float,  # E60
        heat_absorption_pressure_drop: float,  # E67
        heat_absorption_to_regenerator_pressure_drop: float,  # E69
        regenerator_to_compressor_pressure_drop: float,  # E70

        # 传动效率
        motor_efficiency: float,  # E71
        gearbox_efficiency: float,  # E72
) -> dict[str, float]:
    """
    根据循环介质、运行工况和设备参数，计算热泵系统供热 COP。

    单独计算 COP，只需热泵输出热功率和循环参数。
    缺少参数时先向用户询问，不能代入示例或默认值。
    压力和压降统一使用 kPa，温度和端差使用 ℃，功率使用 kW。
    若用户给出的热泵输出热功率为 MW，需乘以 1000 后传入 charging_power。

    :param working_fluid: 循环介质的 CoolProp 名称，如 "Air"、"Nitrogen"
    :param waste_heat_temp: 余热温度 (℃)
    :param salt_temp_low: 熔盐下限温度 (℃)
    :param charging_power: 热泵输出热功率 (kW)

    :param compressor_inlet_pressure: 兼容原字段 (kPa)，实际进口压力由回热器低压侧出口减去管道压降推导
    :param compressor_outlet_pressure: 压缩机出口压力 (kPa)
    :param compressor_isentropic_efficiency: 压缩机等熵效率，取值 (0, 1]
    :param compressor_mechanical_loss: 压缩机机械损失功率 (kW)

    :param compressor_to_heat_release_pressure_drop: 压缩机出口至放热器进口管道压降 (kPa)
    :param heat_release_temp_approach: 放热器端差 (℃)
    :param heat_release_pressure_drop: 放热器压降 (kPa)
    :param heat_release_to_regenerator_pressure_drop: 放热器出口至回热器高压侧进口管道压降 (kPa)

    :param regenerator_temp_approach: 回热器端差 (℃)
    :param regenerator_high_side_pressure_drop: 回热器高压侧压降 (kPa)
    :param regenerator_low_side_pressure_drop: 回热器低压侧压降 (kPa)

    :param regenerator_to_expander_pressure_drop: 回热器高压侧出口至膨胀机进口管道压降 (kPa)
    :param expander_outlet_pressure: 膨胀机出口压力 (kPa)
    :param expander_isentropic_efficiency: 膨胀机等熵效率，取值 (0, 1]
    :param expander_mechanical_loss: 膨胀机机械损失功率 (kW)

    :param expander_to_heat_absorption_pressure_drop: 膨胀机出口至吸热器进口管道压降 (kPa)
    :param heat_absorption_temp_approach: 吸热器端差 (℃)
    :param heat_absorption_pressure_drop: 吸热器压降 (kPa)
    :param heat_absorption_to_regenerator_pressure_drop: 吸热器出口至回热器低压侧进口管道压降 (kPa)
    :param regenerator_to_compressor_pressure_drop: 回热器低压侧出口至压缩机进口管道压降 (kPa)

    :param motor_efficiency: 电动机效率，取值 (0, 1]
    :param gearbox_efficiency: 齿轮箱效率，取值 (0, 1]

    :return: 包含以下结果的字典：
        cop：系统供热 COP，无量纲；
        charging_power：热泵输出热功率 (kW)；
        electrical_power：系统输入电功率 (kW)；
        cycle_mass_flow：循环介质质量流量 (kg/s)。
    """
    return calculate_cop(
        working_fluid=working_fluid,
        waste_heat_temp=waste_heat_temp,
        salt_temp_low=salt_temp_low,
        charging_power=charging_power,
        compressor_inlet_pressure=compressor_inlet_pressure,
        compressor_outlet_pressure=compressor_outlet_pressure,
        compressor_isentropic_efficiency=compressor_isentropic_efficiency,
        compressor_mechanical_loss=compressor_mechanical_loss,
        compressor_to_heat_release_pressure_drop=compressor_to_heat_release_pressure_drop,
        heat_release_temp_approach=heat_release_temp_approach,
        heat_release_pressure_drop=heat_release_pressure_drop,
        heat_release_to_regenerator_pressure_drop=heat_release_to_regenerator_pressure_drop,
        regenerator_temp_approach=regenerator_temp_approach,
        regenerator_high_side_pressure_drop=regenerator_high_side_pressure_drop,
        regenerator_low_side_pressure_drop=regenerator_low_side_pressure_drop,
        regenerator_to_expander_pressure_drop=regenerator_to_expander_pressure_drop,
        expander_outlet_pressure=expander_outlet_pressure,
        expander_isentropic_efficiency=expander_isentropic_efficiency,
        expander_mechanical_loss=expander_mechanical_loss,
        expander_to_heat_absorption_pressure_drop=expander_to_heat_absorption_pressure_drop,
        heat_absorption_temp_approach=heat_absorption_temp_approach,
        heat_absorption_pressure_drop=heat_absorption_pressure_drop,
        heat_absorption_to_regenerator_pressure_drop=heat_absorption_to_regenerator_pressure_drop,
        regenerator_to_compressor_pressure_drop=regenerator_to_compressor_pressure_drop,
        motor_efficiency=motor_efficiency,
        gearbox_efficiency=gearbox_efficiency,
    )
