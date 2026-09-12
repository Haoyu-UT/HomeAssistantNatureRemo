"""Data types of the Nature API, generated from its OpenAPI specification.

DO NOT EDIT BY HAND.  Regenerate with::

    python3 script/generate_models.py

Field names match the JSON wire format exactly (including ``tempUnit`` and
``fixedButtons``), which is what lets pydantic map a payload onto these
dataclasses without a name translation table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass
class AirConParams:
    air_direction: str
    air_direction_h: str
    air_volume: str
    button: str
    operation_mode: str
    temperature: str
    temperature_unit: str
    extra: dict[str, str] | None = None


@dataclass
class ApplianceELModel:
    id: str
    image: str
    manufacturer: str
    name: str


@dataclass
class ApplianceFloorHeaterModel:
    country: str
    id: str
    image: str
    manufacturer: str
    name: str
    remote_name: str
    series: str


@dataclass
class ApplianceLightModel:
    country: str
    id: str
    image: str
    manufacturer: str
    name: str
    remote_name: str


@dataclass
class ApplianceLightProjectorModel:
    country: str
    id: str
    image: str
    manufacturer: str
    name: str
    remote_name: str


@dataclass
class ApplianceModel:
    country: str
    id: str
    image: str
    manufacturer: str
    name: str
    remote_name: str
    series: str


@dataclass
class ApplianceTVModel:
    country: str
    id: str
    image: str
    manufacturer: str
    name: str
    remote_name: str


Area: TypeAlias = Literal[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


@dataclass
class BLEHueLightControlItem:
    light_type: str


@dataclass
class BLEModel:
    id: str
    image: str
    name: str
    slug: str


@dataclass
class BLEPrivateMacroResponse:
    id: str
    url: str


@dataclass
class BLESesameControlItem:
    device_type: str
    key_level: str
    user_index: list[int] | None
    uuid: str


@dataclass
class ButtonDBButton:
    image: str
    label: str
    name: str


CampaignSlug: TypeAlias = str


CoreSerialNumber: TypeAlias = str


@dataclass
class DeviceCommissioneeFabricResponse:
    cfabric: str
    company_name: str
    label: str
    vendor_name: str


@dataclass
class ELManufacturer:
    code: str
    name: str


@dataclass
class ELResponse:
    identifier: str
    instance: str
    manufacturer: ELManufacturer
    route_type: str
    version: str
    ip: str | None = None


@dataclass
class EVCCStateErrorValueAbnormalTemperature:
    kind: Literal["abnormal_temperature"]
    type: Literal["over_temperature", "unknown"]


@dataclass
class EVCCStateErrorValueMemory:
    kind: Literal["memory"]
    type: Literal[
        "read_status_error",
        "write_status_error",
        "read_energy_error",
        "write_energy_error",
        "unknown",
    ]


@dataclass
class EVCCStateErrorValueMeter:
    kind: Literal["meter"]
    type: Literal[
        "overvoltage", "undervoltage", "overcurrent", "energy_leak", "unknown"
    ]


@dataclass
class EVCCStateErrorValueMeterCommunication:
    kind: Literal["meter_communication"]
    type: Literal["serial_error", "unknown"]


@dataclass
class EVCCStateErrorValueRelay:
    kind: Literal["relay"]
    type: Literal["conflict", "unknown"]


@dataclass
class EVCCStateErrorValueUnrecoverable:
    kind: Literal["unrecoverable"]
    type: Literal[
        "boot_error",
        "self_test_under_fatal_error_failed",
        "emergency_stop_from_server",
        "unknown",
    ]


@dataclass
class EVCCStateErrorValueWarnings:
    kind: Literal["warnings"]
    type: Literal["over_current_warning", "unknown"]


@dataclass
class EmptyObject:
    pass


ExtraOptionText: TypeAlias = str


@dataclass
class LightParams:
    button: str


@dataclass
class LightState:
    brightness: str
    last_button: str
    power: str


@dataclass
class LinkText:
    link: str
    text: str


@dataclass
class MorninPlusDeviceResponse:
    active: bool
    id: str
    image: str
    name: str


@dataclass
class MorninPlusResponse:
    devices: list[MorninPlusDeviceResponse] | None
    hi_speed_mode: bool


@dataclass
class PrivacyPolicyRevisionOutline:
    body: str
    links: dict[str, LinkText] | None
    title: str


@dataclass
class QrioLockDeviceResponse:
    id: int
    image: str
    name: str


@dataclass
class QrioLockResponse:
    bd_address: str
    device: QrioLockDeviceResponse
    is_available: bool
    sub_bd_address: str | None = None


@dataclass
class RangeResponseMode:
    dir: list[str] | None
    dirh: list[str] | None
    temp: list[str] | None
    vol: list[str] | None


@dataclass
class Signal:
    id: str
    image: str
    name: str


@dataclass
class TVState:
    input: str


@dataclass
class Template:
    image: str
    label: str
    name: str
    templates: list[Template] | None
    text: str
    type: str
    uuid: str
    x_size: int
    y_size: int


Time: TypeAlias = str


@dataclass
class TvdbRowLayout:
    buttons: list[str] | None
    type: str


@dataclass
class UserDeviceResponse:
    id: str
    nickname: str
    superuser: bool


@dataclass
class UserResponse:
    id: str
    nickname: str
    country: str | None = None
    distance_unit: str | None = None
    temp_unit: str | None = None
    updated_privacy_policy: PrivacyPolicyRevisionOutline | None = None


@dataclass
class ValueUpdatedAtEVCCRelayState:
    updated_at: Time
    value: str


@dataclass
class ValueUpdatedAtBool:
    updated_at: Time
    value: bool


VehicleBodyColor: TypeAlias = Literal[
    "black", "grey", "white", "red", "blue", "light_blue", "green", "beige"
]


VehicleBodyType: TypeAlias = Literal[
    "kei", "compact", "hatchback", "minivan", "sedan", "suv", "coupe"
]


@dataclass
class VehicleDetail:
    body_color: VehicleBodyColor
    body_type: VehicleBodyType
    battery_capacity: float | None = None
    model: str | None = None
    model_year: int | None = None


@dataclass
class AirconSEMResponse:
    adjusting: bool
    area: Area
    campaign_slug: CampaignSlug
    enabled: bool


@dataclass
class AirconSettingsResponse:
    button: str
    dir: str
    dirh: str
    mode: str
    temp: str
    temp_unit: str
    updated_at: Time
    vol: str
    extra: dict[str, str] | None = None


ApplianceModelUnion: TypeAlias = (
    ApplianceModel
    | ApplianceTVModel
    | ApplianceLightModel
    | ApplianceELModel
    | ApplianceLightProjectorModel
    | ApplianceFloorHeaterModel
    | BLEModel
    | None
)


@dataclass
class BLEControlItem:
    addr: str
    addr_type: str
    bonded: bool
    hue: BLEHueLightControlItem | None = None
    macros: dict[str, BLEPrivateMacroResponse] | None = None
    sesame: BLESesameControlItem | None = None


@dataclass
class CoreSensorValue:
    created_at: Time
    val: float


@dataclass
class Device:
    created_at: Time
    firmware_version: str
    humidity_offset: float
    id: str
    mac_address: str
    name: str
    serial_number: CoreSerialNumber
    temperature_offset: float
    updated_at: Time
    bt_mac_address: str | None = None


@dataclass
class DeviceResponse:
    created_at: Time
    firmware_version: str
    humidity_offset: float
    id: str
    mac_address: str
    name: str
    newest_events: dict[str, CoreSensorValue] | None
    serial_number: CoreSerialNumber
    temperature_offset: float
    updated_at: Time
    bridged_devices_limit: int | None = None
    bt_mac_address: str | None = None
    commissionee_fabrics: list[DeviceCommissioneeFabricResponse] | None = None
    commissionee_fabrics_limit: int | None = None
    online: bool | None = None
    users: list[UserDeviceResponse] | None = None


DeviceResponses: TypeAlias = list[DeviceResponse] | None


@dataclass
class ELPropertyResponse:
    epc: int
    name: str
    updated_at: Time
    val: str


EVCCAutoRecoveringValueUnion: TypeAlias = (
    EVCCStateErrorValueAbnormalTemperature | EVCCStateErrorValueWarnings
)


EVCCSelfTestValueUnion: TypeAlias = (
    EVCCStateErrorValueRelay
    | EVCCStateErrorValueMeter
    | EVCCStateErrorValueMeterCommunication
    | EVCCStateErrorValueMemory
    | EVCCStateErrorValueUnrecoverable
)


@dataclass
class ExtraOption:
    text: ExtraOptionText
    value: str
    default: bool | None = None


@dataclass
class LightProjectordbLayout:
    image: str
    label: str
    name: str
    templates: list[Template] | None
    text: str
    type: str
    uuid: str
    x_size: int
    y_size: int


@dataclass
class LightResponse:
    buttons: list[ButtonDBButton] | None
    state: LightState | None = None


@dataclass
class SmartMeterResponse:
    echonetlite_properties: list[ELPropertyResponse] | None


@dataclass
class TVResponse:
    buttons: list[ButtonDBButton] | None
    layout: list[TvdbRowLayout] | None = None
    state: TVState | None = None


@dataclass
class ValueUpdatedAtEVCCAutoRecoveringValueUnion:
    updated_at: Time
    value: EVCCAutoRecoveringValueUnion


@dataclass
class ValueUpdatedAtEVCCSelfTestValueUnion:
    updated_at: Time
    value: EVCCSelfTestValueUnion


@dataclass
class Vehicle:
    detail: VehicleDetail
    manufacturer: str


@dataclass
class AirConExtraResponse:
    availability: str
    description: str
    id: str
    text: str
    type: str
    defaultTime: str | None = None
    options: list[ExtraOption] | None = None


@dataclass
class AirConRangeResponse:
    fixedButtons: list[str] | None
    modes: dict[str, RangeResponseMode] | None
    extras: list[AirConExtraResponse] | None = None


@dataclass
class AirConResponse:
    range: AirConRangeResponse
    tempUnit: str


@dataclass
class EVCCStateErrorsResponse:
    auto_recovering: list[ValueUpdatedAtEVCCAutoRecoveringValueUnion] | None
    require_self_test: list[ValueUpdatedAtEVCCSelfTestValueUnion] | None


@dataclass
class FloorHeaterResponse:
    range: AirConRangeResponse
    tempUnit: str


@dataclass
class LightProjectorResponse:
    layout: LightProjectordbLayout


@dataclass
class EVCCResponse:
    last_operated_remotely: bool
    online: ValueUpdatedAtBool
    relay_state: ValueUpdatedAtEVCCRelayState
    vehicle: Vehicle
    connected_device: Device | None = None
    current_charging_amount: float | None = None
    errors: EVCCStateErrorsResponse | None = None


@dataclass
class ApplianceResponse:
    id: str
    image: str
    model: ApplianceModelUnion | None
    nickname: str
    signals: list[Signal] | None
    type: str
    aircon: AirConResponse | None = None
    aircon_smart_eco_mode: AirconSEMResponse | None = None
    ble: BLEControlItem | None = None
    device: Device | None = None
    echonetlite: ELResponse | None = None
    evcc: EVCCResponse | None = None
    floor_heater: FloorHeaterResponse | None = None
    light: LightResponse | None = None
    light_projector: LightProjectorResponse | None = None
    matter_bridged_device_state: str | None = None
    mornin_plus: MorninPlusResponse | None = None
    qrio_lock: QrioLockResponse | None = None
    settings: AirconSettingsResponse | None = None
    smart_meter: SmartMeterResponse | None = None
    tv: TVResponse | None = None


ApplianceResponses: TypeAlias = list[ApplianceResponse] | None
