from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ComponentTypeStats:
    name: str
    sprite_name: str
    energy_per_pulse: float
    heat_per_pulse: float
    pulses_produced: float
    max_durability: float
    heat_capacity: float
    cost: float = 0.0
    display_name: str = ""
    description: str = ""
    self_vent_rate: float = 0.0
    reactor_vent_rate: float = 0.0
    neighbor_affects: bool = False
    reactor_heat_capacity_increase: float = 0.0
    reactor_power_capacity_increase: float = 0.0
    reflects_pulses: float = 0.0
    reflector_bonus_pct: float = 0.0
    type_of_component: str = ""
    number_of_cores: int = 1
    cell_width: int = 1
    cell_height: int = 1
    stats_known: bool = False
    shop_page: int = 0
    shop_order: int = 0
    shop_row: int = 0
    shop_col: int = 0
    cant_lose_heat: bool = False  # Binary +0xCA flag: thermally isolated (heat cannot be removed by exchangers/inlets)
    component_type_id: int = 0  # Integer ID for upgrade bonus lookup (2-7=fuel tiers, 8=Vent, etc.)
    required_upgrade: int = -1  # Upgrade index that must be purchased for this component to appear (-1 = always visible)
