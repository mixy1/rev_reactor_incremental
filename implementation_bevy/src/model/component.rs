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
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct PlacedComponent {
    pub kind: ComponentKind,
    pub coord: GridCoord,
}

impl PlacedComponent {
    pub fn new(kind: ComponentKind, coord: GridCoord) -> Self {
        Self { kind, coord }
    }
}
