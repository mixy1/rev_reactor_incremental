use super::grid::GridCoord;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum FuelKind {
    Uranium,
    Plutonium,
    Thorium,
    Seaborgium,
    Dolorium,
    Nefastium,
    Protium,
    Monastium,
    Kymium,
    Discurrium,
    Stavrium,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ComponentCategory {
    Fuel,
    Vent,
    Coolant,
    Capacitor,
    Reflector,
    Plating,
    Inlet,
    Outlet,
    Exchanger,
    Clock,
    GenericHeat,
    GenericPower,
    GenericInfinity,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ComponentKind {
    Fuel(FuelKind),
    Vent { tier: u8 },
    Coolant { tier: u8 },
    Capacitor { tier: u8 },
    Reflector { tier: u8 },
    Plating { tier: u8 },
    Inlet { tier: u8 },
    Outlet { tier: u8 },
    Exchanger { tier: u8 },
    Clock,
    GenericHeat,
    GenericPower,
    GenericInfinity,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ComponentStats {
    pub energy_per_pulse: f64,
    pub heat_per_pulse: f64,
    pub pulses_produced: u32,
    pub max_durability: f64,
    pub heat_capacity: f64,
    pub self_vent_rate: f64,
    pub reactor_vent_rate: f64,
    pub coolant_absorb_rate: f64,
    pub reflector_bonus_pct: f64,
    pub reactor_power_capacity_increase: f64,
    pub reactor_heat_capacity_increase: f64,
}

impl ComponentStats {
    pub const fn zero() -> Self {
        Self {
            energy_per_pulse: 0.0,
            heat_per_pulse: 0.0,
            pulses_produced: 0,
            max_durability: 0.0,
            heat_capacity: 0.0,
            self_vent_rate: 0.0,
            reactor_vent_rate: 0.0,
            coolant_absorb_rate: 0.0,
            reflector_bonus_pct: 0.0,
            reactor_power_capacity_increase: 0.0,
            reactor_heat_capacity_increase: 0.0,
        }
    }
}

impl ComponentKind {
    pub fn category(self) -> ComponentCategory {
        match self {
            Self::Fuel(_) => ComponentCategory::Fuel,
            Self::Vent { .. } => ComponentCategory::Vent,
            Self::Coolant { .. } => ComponentCategory::Coolant,
            Self::Capacitor { .. } => ComponentCategory::Capacitor,
            Self::Reflector { .. } => ComponentCategory::Reflector,
            Self::Plating { .. } => ComponentCategory::Plating,
            Self::Inlet { .. } => ComponentCategory::Inlet,
            Self::Outlet { .. } => ComponentCategory::Outlet,
            Self::Exchanger { .. } => ComponentCategory::Exchanger,
            Self::Clock => ComponentCategory::Clock,
            Self::GenericHeat => ComponentCategory::GenericHeat,
            Self::GenericPower => ComponentCategory::GenericPower,
            Self::GenericInfinity => ComponentCategory::GenericInfinity,
        }
    }

    pub fn stats(self) -> ComponentStats {
        match self {
            Self::Fuel(fuel) => fuel.stats(),
            Self::Vent { tier } => ComponentStats {
                heat_capacity: 20.0 * f64::from(tier),
                self_vent_rate: 1.2 * f64::from(tier),
                reactor_vent_rate: 0.6 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Coolant { tier } => ComponentStats {
                heat_capacity: 45.0 * f64::from(tier),
                coolant_absorb_rate: 0.75 * f64::from(tier),
                reactor_heat_capacity_increase: 120.0 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Capacitor { tier } => ComponentStats {
                heat_capacity: 30.0 * f64::from(tier),
                reactor_power_capacity_increase: 60.0 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Reflector { tier } => ComponentStats {
                max_durability: 100.0 * f64::from(tier),
                reflector_bonus_pct: 0.1 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Plating { tier } => ComponentStats {
                reactor_heat_capacity_increase: 250.0 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Inlet { tier } => ComponentStats {
                heat_capacity: 10.0 * f64::from(tier),
                reactor_vent_rate: 0.8 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Outlet { tier } => ComponentStats {
                heat_capacity: 10.0 * f64::from(tier),
                reactor_vent_rate: 0.8 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Exchanger { tier } => ComponentStats {
                heat_capacity: 15.0 * f64::from(tier),
                coolant_absorb_rate: 0.6 * f64::from(tier),
                ..ComponentStats::zero()
            },
            Self::Clock => ComponentStats::zero(),
            Self::GenericHeat => ComponentStats {
                heat_capacity: 10.0,
                self_vent_rate: 0.5,
                ..ComponentStats::zero()
            },
            Self::GenericPower => ComponentStats {
                reactor_power_capacity_increase: 25.0,
                ..ComponentStats::zero()
            },
            Self::GenericInfinity => ComponentStats::zero(),
        }
    }

    pub fn canonical_name(self) -> String {
        match self {
            Self::Fuel(fuel) => fuel.canonical_name().to_string(),
            Self::Vent { tier } => format!("Vent{tier}"),
            Self::Coolant { tier } => format!("Coolant{tier}"),
            Self::Capacitor { tier } => format!("Capacitor{tier}"),
            Self::Reflector { tier } => format!("Reflector{tier}"),
            Self::Plating { tier } => format!("Plate{tier}"),
            Self::Inlet { tier } => format!("Inlet{tier}"),
            Self::Outlet { tier } => format!("Outlet{tier}"),
            Self::Exchanger { tier } => format!("Exchanger{tier}"),
            Self::Clock => "Clock".to_string(),
            Self::GenericHeat => "GenericHeat".to_string(),
            Self::GenericPower => "GenericPower".to_string(),
            Self::GenericInfinity => "GenericInfinity".to_string(),
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        let trimmed = name.trim();
        if trimmed.is_empty() {
            return None;
        }

        if let Some(fuel_kind) = FuelKind::from_name(trimmed) {
            return Some(Self::Fuel(fuel_kind));
        }

        parse_tier_component(trimmed, "Vent", |tier| Self::Vent { tier })
            .or_else(|| parse_tier_component(trimmed, "Coolant", |tier| Self::Coolant { tier }))
            .or_else(|| parse_tier_component(trimmed, "Capacitor", |tier| Self::Capacitor { tier }))
            .or_else(|| parse_tier_component(trimmed, "Reflector", |tier| Self::Reflector { tier }))
            .or_else(|| parse_tier_component(trimmed, "Plate", |tier| Self::Plating { tier }))
            .or_else(|| parse_tier_component(trimmed, "Plating", |tier| Self::Plating { tier }))
            .or_else(|| parse_tier_component(trimmed, "Inlet", |tier| Self::Inlet { tier }))
            .or_else(|| parse_tier_component(trimmed, "Outlet", |tier| Self::Outlet { tier }))
            .or_else(|| parse_tier_component(trimmed, "Exchanger", |tier| Self::Exchanger { tier }))
            .or_else(|| match trimmed {
                "Clock" => Some(Self::Clock),
                "GenericHeat" => Some(Self::GenericHeat),
                "GenericPower" => Some(Self::GenericPower),
                "GenericInfinity" => Some(Self::GenericInfinity),
                _ => None,
            })
    }
}

impl FuelKind {
    pub fn stats(self) -> ComponentStats {
        let (energy_per_pulse, heat_per_pulse, max_durability, pulses_produced) = match self {
            Self::Uranium => (1.0, 1.0, 120.0, 1),
            Self::Plutonium => (1.5, 1.6, 180.0, 1),
            Self::Thorium => (2.2, 2.4, 240.0, 1),
            Self::Seaborgium => (3.5, 3.8, 300.0, 1),
            Self::Dolorium => (5.0, 5.5, 360.0, 1),
            Self::Nefastium => (8.0, 8.8, 420.0, 1),
            Self::Protium => (9.0, 9.0, 500.0, 1),
            Self::Monastium => (12.0, 10.0, 600.0, 1),
            Self::Kymium => (16.0, 16.0, 700.0, 1),
            Self::Discurrium => (24.0, 26.0, 800.0, 4),
            Self::Stavrium => (32.0, 34.0, 900.0, 1),
        };
        ComponentStats {
            energy_per_pulse,
            heat_per_pulse,
            pulses_produced,
            max_durability,
            ..ComponentStats::zero()
        }
    }

    pub const fn canonical_name(self) -> &'static str {
        match self {
            Self::Uranium => "Fuel1-1",
            Self::Plutonium => "Fuel2-1",
            Self::Thorium => "Fuel3-1",
            Self::Seaborgium => "Fuel4-1",
            Self::Dolorium => "Fuel5-1",
            Self::Nefastium => "Fuel6-1",
            Self::Protium => "Fuel7-1",
            Self::Monastium => "Fuel8-1",
            Self::Kymium => "Fuel9-1",
            Self::Discurrium => "Fuel10-1",
            Self::Stavrium => "Fuel11-1",
        }
    }

    pub fn from_name(name: &str) -> Option<Self> {
        let Some(rest) = name.strip_prefix("Fuel") else {
            return None;
        };
        let tier_str = rest.split('-').next()?;
        let tier = tier_str.parse::<u8>().ok()?;
        Some(match tier {
            1 => Self::Uranium,
            2 => Self::Plutonium,
            3 => Self::Thorium,
            4 => Self::Seaborgium,
            5 => Self::Dolorium,
            6 => Self::Nefastium,
            7 => Self::Protium,
            8 => Self::Monastium,
            9 => Self::Kymium,
            10 => Self::Discurrium,
            11 => Self::Stavrium,
            _ => return None,
        })
    }
}

fn parse_tier_component(
    value: &str,
    prefix: &str,
    builder: impl FnOnce(u8) -> ComponentKind,
) -> Option<ComponentKind> {
    let tier_str = value.strip_prefix(prefix)?;
    let tier = tier_str.parse::<u8>().ok()?;
    Some(builder(tier))
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlacedComponent {
    pub id: u64,
    pub kind: ComponentKind,
    pub coord: GridCoord,
    pub placed_at_tick: u64,
    pub heat: f64,
    pub durability: f64,
    pub last_power: f64,
    pub last_heat: f64,
    pub pulse_count: u32,
    pub depleted: bool,
}

impl PlacedComponent {
    pub fn new(kind: ComponentKind, coord: GridCoord) -> Self {
        Self::new_with_metadata(kind, coord, 0, 0)
    }

    pub fn new_with_metadata(
        kind: ComponentKind,
        coord: GridCoord,
        id: u64,
        placed_at_tick: u64,
    ) -> Self {
        let stats = kind.stats();
        Self {
            id,
            kind,
            coord,
            placed_at_tick,
            heat: 0.0,
            durability: stats.max_durability,
            last_power: 0.0,
            last_heat: 0.0,
            pulse_count: 0,
            depleted: false,
        }
    }

    pub fn stats(&self) -> ComponentStats {
        self.kind.stats()
    }

    pub fn is_fuel(&self) -> bool {
        self.stats().energy_per_pulse > 0.0
    }

    pub fn is_active(&self) -> bool {
        !self.depleted
    }
}
