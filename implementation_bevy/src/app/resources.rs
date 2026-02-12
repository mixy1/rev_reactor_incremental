use bevy::prelude::*;
use implementation_bevy::{ComponentKind, FuelKind, GridCoord, Simulation};

#[derive(Resource, Debug, Clone)]
pub struct RuntimeConfig {
    pub grid_width: usize,
    pub grid_height: usize,
    pub grid_layers: usize,
    pub cell_size: f32,
    pub cell_gap: f32,
    pub tick_hz: f32,
    pub start_money: f64,
    pub sell_refund_ratio: f64,
}

impl Default for RuntimeConfig {
    fn default() -> Self {
        Self {
            grid_width: 19,
            grid_height: 16,
            grid_layers: 1,
            cell_size: 30.0,
            cell_gap: 2.0,
            tick_hz: 10.0,
            start_money: 180.0,
            sell_refund_ratio: 0.5,
        }
    }
}

#[derive(Resource, Debug)]
pub struct SessionState {
    pub simulation: Simulation,
    pub tick_timer: Timer,
}

#[derive(Debug, Clone, Copy)]
pub struct ComponentSpec {
    pub label: &'static str,
    pub kind: ComponentKind,
    pub cost: f64,
    pub power_per_tick: f64,
    pub heat_per_tick: f64,
    pub color: Color,
}

#[derive(Resource, Debug)]
pub struct ComponentCatalog {
    specs: Vec<ComponentSpec>,
}

impl Default for ComponentCatalog {
    fn default() -> Self {
        Self {
            specs: vec![
                ComponentSpec {
                    label: "Fuel (Uranium)",
                    kind: ComponentKind::Fuel(FuelKind::Uranium),
                    cost: 24.0,
                    power_per_tick: 2.6,
                    heat_per_tick: 1.4,
                    color: Color::srgb(0.95, 0.78, 0.22),
                },
                ComponentSpec {
                    label: "Vent T1",
                    kind: ComponentKind::Vent { tier: 1 },
                    cost: 14.0,
                    power_per_tick: 0.0,
                    heat_per_tick: -0.8,
                    color: Color::srgb(0.36, 0.76, 0.93),
                },
                ComponentSpec {
                    label: "Coolant T1",
                    kind: ComponentKind::Coolant { tier: 1 },
                    cost: 18.0,
                    power_per_tick: 0.0,
                    heat_per_tick: -1.1,
                    color: Color::srgb(0.27, 0.58, 0.88),
                },
                ComponentSpec {
                    label: "Capacitor T1",
                    kind: ComponentKind::Capacitor { tier: 1 },
                    cost: 20.0,
                    power_per_tick: 1.1,
                    heat_per_tick: 0.3,
                    color: Color::srgb(0.57, 0.89, 0.54),
                },
                ComponentSpec {
                    label: "Plating T1",
                    kind: ComponentKind::Plating { tier: 1 },
                    cost: 16.0,
                    power_per_tick: 0.2,
                    heat_per_tick: -0.2,
                    color: Color::srgb(0.84, 0.53, 0.87),
                },
            ],
        }
    }
}

impl ComponentCatalog {
    pub fn selected(&self, selection: &SelectionState) -> Option<&ComponentSpec> {
        self.specs.get(selection.index)
    }

    pub fn set_selection_index(&self, selection: &mut SelectionState, index: usize) {
        if self.specs.is_empty() {
            selection.index = 0;
            return;
        }
        selection.index = index.min(self.specs.len() - 1);
    }

    pub fn spec_for_kind(&self, kind: ComponentKind) -> Option<&ComponentSpec> {
        self.specs.iter().find(|entry| entry.kind == kind)
    }

    pub fn sell_value(&self, kind: ComponentKind, refund_ratio: f64) -> f64 {
        let ratio = refund_ratio.clamp(0.0, 1.0);
        self.spec_for_kind(kind)
            .map(|spec| spec.cost * ratio)
            .unwrap_or(0.0)
    }
}

#[derive(Resource, Debug, Default)]
pub struct SelectionState {
    pub index: usize,
}

#[derive(Resource, Debug, Default)]
pub struct HoveredCell(pub Option<GridCoord>);

#[derive(Resource, Debug, Clone, Copy)]
pub struct GridLayout {
    pub origin: Vec2,
    pub cell_size: f32,
    pub cell_gap: f32,
}

impl GridLayout {
    pub fn new(width: usize, height: usize, cell_size: f32, cell_gap: f32) -> Self {
        let total_width =
            (width as f32 * cell_size) + ((width.saturating_sub(1)) as f32 * cell_gap);
        let total_height =
            (height as f32 * cell_size) + ((height.saturating_sub(1)) as f32 * cell_gap);

        Self {
            origin: Vec2::new(-total_width * 0.5, -total_height * 0.5),
            cell_size,
            cell_gap,
        }
    }

    pub fn cell_center(&self, coord: GridCoord) -> Vec3 {
        let stride = self.cell_size + self.cell_gap;
        let x = self.origin.x + coord.x as f32 * stride + self.cell_size * 0.5;
        let y = self.origin.y + coord.y as f32 * stride + self.cell_size * 0.5;
        Vec3::new(x, y, 0.0)
    }

    pub fn world_to_coord(
        &self,
        world: Vec2,
        width: usize,
        height: usize,
        layer: usize,
    ) -> Option<GridCoord> {
        let stride = self.cell_size + self.cell_gap;
        let local = world - self.origin;
        if local.x < 0.0 || local.y < 0.0 {
            return None;
        }

        let x = (local.x / stride).floor() as usize;
        let y = (local.y / stride).floor() as usize;

        if x >= width || y >= height {
            return None;
        }

        let x_in_cell = local.x - x as f32 * stride;
        let y_in_cell = local.y - y as f32 * stride;
        if x_in_cell > self.cell_size || y_in_cell > self.cell_size {
            return None;
        }

        Some(GridCoord::new(x, y, layer))
    }
}

#[derive(Event, Debug, Clone, Copy)]
pub enum GridAction {
    Place(GridCoord),
    Remove(GridCoord),
}

#[derive(Component, Debug, Clone, Copy)]
pub struct GridTile {
    pub coord: GridCoord,
}

#[derive(Component)]
pub struct HudText;
