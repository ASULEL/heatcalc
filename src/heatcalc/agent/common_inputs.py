"""热源工具共用的输入字段，按蒸汽、传热和熔盐物性分组。"""

from pydantic import BaseModel, Field


class SteamInputs(BaseModel):
    """蒸汽和给水工况、供汽时长。"""

    # 蒸汽与供热参数
    steam_pressure: float = Field(
        description="蒸汽压力",
        json_schema_extra={"unit": "MPa", "group": "蒸汽与供热参数"},
    )
    steam_temp: float = Field(
        description="蒸汽温度",
        json_schema_extra={"unit": "°C", "group": "蒸汽与供热参数"},
    )
    feedwater_pressure: float = Field(
        description="给水压力",
        json_schema_extra={"unit": "MPa", "group": "蒸汽与供热参数"},
    )
    feedwater_temp: float = Field(
        description="给水温度",
        json_schema_extra={"unit": "°C", "group": "蒸汽与供热参数"},
    )
    steam_supply_hours: float = Field(
        description="供汽时长",
        json_schema_extra={"unit": "h", "group": "蒸汽与供热参数"},
    )


class HeatTransferInputs(BaseModel):
    """充热时长、换热效率和储热效率。"""

    # 储热系统参数
    operating_hours: float = Field(
        description="充热时长",
        json_schema_extra={"unit": "h", "group": "储热系统参数"},
    )
    heat_exchange_efficiency: float = Field(
        description="换热效率",
        json_schema_extra={"unit": "小数", "group": "储热系统参数"},
    )
    storage_efficiency: float = Field(
        description="储热效率",
        json_schema_extra={"unit": "小数", "group": "储热系统参数"},
    )


class SaltInputs(BaseModel):
    """熔盐比热容及高低温。"""

    # 储热系统参数
    salt_specific_heat: float = Field(
        description="熔盐比热容",
        json_schema_extra={"unit": "kJ/(kg·K)", "group": "储热系统参数"},
    )
    salt_temp_high: float = Field(
        description="熔盐最高温度",
        json_schema_extra={"unit": "°C", "group": "储热系统参数"},
    )
    salt_temp_low: float = Field(
        description="熔盐最低温度",
        json_schema_extra={"unit": "°C", "group": "储热系统参数"},
    )


class HeatSourceInputs(SteamInputs, HeatTransferInputs, SaltInputs):
    """热源购电成本与蒸汽流量共用的工况。"""

    # 电价与预算参数
    electricity_price: float = Field(
        description="电价",
        json_schema_extra={"unit": "元/kWh", "group": "电价与预算参数"},
    )
