"""Upgrade system — data model, loading, and stat bonus computation.

RE: unnamed_function_10398 (UpgradeTypes.Initialize) — 51 upgrade objects.
RE: unnamed_function_10371 (GetUpgradeStatBonus) — bonus accumulation.
Formula: multiplicative_product * (additive_sum + 1.0)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import List, Optional


class StatCategory(IntEnum):
    NONE = 0
    MAX_DURABILITY = 1
    HEAT_CAPACITY = 2
    ENERGY_PER_PULSE = 3
    HEAT_PER_PULSE = 4
    PULSES_PRODUCED = 5
    SELF_VENT_RATE = 6
    ADJACENT_VENT_RATE = 7
    REACTOR_VENT_RATE = 8
    ADJACENT_TRANSFER_RATE = 9
    REACTOR_TRANSFER_RATE = 10
    REACTOR_HEAT_CAP_INCREASE = 11
    REACTOR_POWER_CAP_INCREASE = 12
    MANUAL_SELL = 13
    MANUAL_VENT = 14
    AUTO_SELL_RATE = 15
    AUTO_VENT_RATE = 16
    VENT_EFFECTIVENESS = 17
    REPLACES_SELF = 18
    TICKS_PER_SECOND = 19
    CELL_EFFECTIVENESS = 20
    VENT_CAPACITY = 21
    EXCHANGER_EFFECTIVENESS = 22
    EXCHANGER_CAPACITY = 23
    REFLECTOR_EFFECTIVENESS = 24
    COMPONENT_DISCOUNT = 25
    UPGRADE_DISCOUNT = 26


@dataclass
class Bonus:
    """A single stat modifier within an upgrade.

    RE: unnamed_function_10371 iterates these per upgrade.
    Each bonus has:
      +0x08 = component_type (which component category this targets)
      +0x0c = stat_category (which stat this modifies)
      +0x10 = additive value (accumulated as sum)
      +0x18 = multiplicative value (accumulated as product)
    """
    component_type: int
    stat_category: int
    additive: float = 0.0
    multiplicative: float = 1.0


@dataclass
class UpgradeType:
    """One of 51 upgrade definitions.

    RE: UpgradeType object layout:
      +0x08 = name string ptr
      +0x0c = description string ptr
      +0x10 = icon sprite
      +0x14 = category sprite
      +0x18 = base_cost (double)
      +0x20 = cost_multiplier (double) — 0 = one-time purchase
      +0x28 = is_prestige flag
      +0x29 = purchasable flag
      +0x2c = prerequisite ptr
      +0x30 = bonuses list
    """
    index: int
    name: str
    description: str
    base_cost: float
    cost_multiplier: float
    purchasable: bool
    is_prestige: bool
    prerequisite: int  # index of required upgrade, -1 = none
    bonuses: List[Bonus] = field(default_factory=list)
    level_names: List[str] = field(default_factory=list)
    icon: str = ""
    category: str = ""
    level: int = 0


class UpgradeManager:
    """Manages upgrade state and computes stat bonuses.

    RE: unnamed_function_10371 (GetUpgradeStatBonus)
    For a given (component_type, stat_category) pair:
      additive_sum = 0.0
      multiplicative_product = 1.0
      for each upgrade with level > 0:
          for each bonus matching (component_type, stat_category):
              additive_sum += bonus.additive * upgrade.level
              multiplicative_product *= bonus.multiplicative ** upgrade.level
      return multiplicative_product * (additive_sum + 1.0)
    """

    def __init__(self) -> None:
        self.upgrades: List[UpgradeType] = []

    def load(self, path: Optional[Path] = None) -> None:
        if path is None:
            path = Path(__file__).resolve().parent / "upgrade_data.json"
        if not path.exists():
            return
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("upgrades", [])
        self.upgrades = []
        for entry in items:
            bonuses = []
            for b in entry.get("bonuses", []):
                bonuses.append(Bonus(
                    component_type=b["component_type"],
                    stat_category=b["stat_category"],
                    additive=b.get("additive", 0.0),
                    multiplicative=b.get("multiplicative", 1.0),
                ))
            self.upgrades.append(UpgradeType(
                index=entry["index"],
                name=entry["name"],
                description=entry.get("description", ""),
                base_cost=entry["base_cost"],
                cost_multiplier=entry.get("cost_multiplier", 0.0),
                purchasable=entry.get("purchasable", True),
                is_prestige=entry.get("is_prestige", False),
                prerequisite=entry.get("prerequisite", -1),
                bonuses=bonuses,
                level_names=entry.get("level_names", []),
                icon=entry.get("icon", ""),
                category=entry.get("category", ""),
                level=0,
            ))

    def get_upgrade_stat_bonus(self, component_type: int, stat_category: int) -> float:
        """RE: unnamed_function_10371 — compute cumulative bonus for a stat.

        Returns multiplicative_product * (additive_sum + 1.0).
        With no upgrades purchased, returns 1.0.
        """
        additive_sum = 0.0
        multiplicative_product = 1.0
        for upgrade in self.upgrades:
            if upgrade.level == 0:
                continue
            for bonus in upgrade.bonuses:
                if bonus.component_type == component_type and bonus.stat_category == stat_category:
                    additive_sum += bonus.additive * upgrade.level
                    multiplicative_product *= bonus.multiplicative ** upgrade.level
        return multiplicative_product * (additive_sum + 1.0)

    def get_cost(self, upgrade_idx: int, level: Optional[int] = None) -> float:
        """Compute cost for purchasing the next level of an upgrade.

        RE: cost = base_cost * (cost_multiplier ^ level) * discount
        For one-time purchases (cost_multiplier == 0): cost = base_cost
        """
        if upgrade_idx < 0 or upgrade_idx >= len(self.upgrades):
            return 0.0
        u = self.upgrades[upgrade_idx]
        lvl = level if level is not None else u.level
        if u.cost_multiplier == 0.0:
            return u.base_cost
        discount = self.get_upgrade_discount()
        return u.base_cost * (u.cost_multiplier ** lvl) * discount

    def can_purchase(self, upgrade_idx: int, money: float, exotic_particles: float) -> bool:
        if upgrade_idx < 0 or upgrade_idx >= len(self.upgrades):
            return False
        u = self.upgrades[upgrade_idx]
        # One-time purchases: already owned if level > 0
        if u.cost_multiplier == 0.0 and u.level > 0:
            return False
        # Prerequisite check
        if u.prerequisite >= 0:
            prereq = self.upgrades[u.prerequisite]
            if prereq.level == 0:
                return False
        cost = self.get_cost(upgrade_idx)
        if u.is_prestige:
            return exotic_particles >= cost
        return money >= cost

    def purchase(self, upgrade_idx: int, money: float, exotic_particles: float) -> tuple[float, float]:
        """Attempt to purchase an upgrade. Returns (new_money, new_ep) after deduction.

        Returns unchanged values if purchase fails.
        """
        if not self.can_purchase(upgrade_idx, money, exotic_particles):
            return money, exotic_particles
        u = self.upgrades[upgrade_idx]
        cost = self.get_cost(upgrade_idx)
        if u.is_prestige:
            exotic_particles -= cost
        else:
            money -= cost
        u.level += 1
        return money, exotic_particles

    def get_upgrade_discount(self) -> float:
        """RE: stat 26 (UpgradeDiscount) — reduces money-cost of upgrades.

        Aggressive Bartering (index 40): additive=1.0 per level → (level + 1.0) base.
        Actual discount = 0.99^level (1% reduction per level, multiplicative stacking).
        """
        bonus = self.get_upgrade_stat_bonus(1, StatCategory.UPGRADE_DISCOUNT)
        # bonus = 1.0 * (additive_sum + 1.0) where additive_sum = 1.0 * level
        # Convert to discount: 0.99^level
        # Since bonus = level + 1, discount = 0.99^(bonus - 1)
        if bonus <= 1.0:
            return 1.0
        return 0.99 ** (bonus - 1.0)

    def get_component_discount(self) -> float:
        """RE: stat 25 (ComponentDiscount) — reduces component shop costs."""
        bonus = self.get_upgrade_stat_bonus(1, StatCategory.COMPONENT_DISCOUNT)
        if bonus <= 1.0:
            return 1.0
        return 0.99 ** (bonus - 1.0)

    def display_name(self, upgrade_idx: int) -> str:
        """Get level-dependent display name for an upgrade."""
        if upgrade_idx < 0 or upgrade_idx >= len(self.upgrades):
            return ""
        u = self.upgrades[upgrade_idx]
        if not u.level_names:
            return u.name
        name_idx = min(u.level, len(u.level_names) - 1)
        return u.level_names[name_idx]

    def has_replaces_self(self, component_type: int) -> bool:
        """Check if auto-replace (Perpetual) is purchased for a component type."""
        bonus = self.get_upgrade_stat_bonus(component_type, StatCategory.REPLACES_SELF)
        return bonus > 1.0

    def prepare_multipliers(self, sim: "Simulation") -> None:  # noqa: F821
        """RE: unnamed_function_10422 (PrepareMultipliers) — tick step 1.

        Computes global multipliers from component tier sums + upgrades.
        Binary uses unnamed_function_10447 which sums ComponentType.Tier
        (offset 0x10) for all components matching a TypeOfComponent (0x14).
        """
        # RE: unnamed_function_10447(param1, 0xd, 0) — sums Tier for TypeOfComponent=0xd
        # Binary checks TypeOfComponent=13 but description says "Each capacitor".
        # The Tier field weights higher-tier components more (tier 1=1, tier 5=5).
        capacitor_tier_sum = sim.sum_component_tiers("Capacitor")

        # RE: unnamed_function_10447(param1, 0xc, 0) — sums Tier for TypeOfComponent=0xc
        plating_tier_sum = sim.sum_component_tiers("Plating")

        # Vent effectiveness: Active Venting upgrade (index 27)
        # RE: self_vent_mult = (bonus(0xD,0x11) - 1) * tier_sum * 0.01 + 1
        vent_eff = self.get_upgrade_stat_bonus(13, StatCategory.VENT_EFFECTIVENESS)
        sim.self_vent_mult = (vent_eff - 1.0) * capacitor_tier_sum * 0.01 + 1.0

        # Heat exchange effectiveness: Active Exchangers upgrade (index 30)
        # RE: heat_exchange_mult = (bonus(0xD,0x16) - 1) * tier_sum * 0.01 + 1
        exch_eff = self.get_upgrade_stat_bonus(13, StatCategory.EXCHANGER_EFFECTIVENESS)
        sim.heat_exchange_mult = (exch_eff - 1.0) * capacitor_tier_sum * 0.01 + 1.0

        # Power cap: each plating tier adds (bonus-1)*0.01
        # RE: power_cap_mult = (bonus(0xC,0x15) - 1) * tier_sum * 0.01 + 1
        pwr_cap = self.get_upgrade_stat_bonus(12, StatCategory.VENT_CAPACITY)
        sim.power_cap_mult = (pwr_cap - 1.0) * plating_tier_sum * 0.01 + 1.0

        # Heat cap: each plating tier adds (bonus-1)*0.01
        # RE: heat_cap_mult = (bonus(0xC,0x17) - 1) * tier_sum * 0.01 + 1
        heat_cap = self.get_upgrade_stat_bonus(12, StatCategory.EXCHANGER_CAPACITY)
        sim.heat_cap_mult = (heat_cap - 1.0) * plating_tier_sum * 0.01 + 1.0

        # Ticks per second: additive (base 1 + upgrade bonus)
        tps_bonus = self.get_upgrade_stat_bonus(1, StatCategory.TICKS_PER_SECOND)
        sim.ticks_per_second = tps_bonus  # bonus returns (additive_sum + 1.0) = level + 1

        # Manual vent amount: base 1.0 * bonus
        sim.manual_vent_amount = self.get_upgrade_stat_bonus(1, StatCategory.MANUAL_VENT)

        # Manual sell multiplier
        sim.manual_sell_mult = self.get_upgrade_stat_bonus(1, StatCategory.MANUAL_SELL)
