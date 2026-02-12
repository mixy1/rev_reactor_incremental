use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
#[serde(default)]
pub struct SaveStore {
    pub money: f64,
    pub total_money: f64,
    pub money_earned_this_game: f64,
    pub power: f64,
    pub total_power_produced: f64,
    pub power_produced_this_game: f64,
    pub heat: f64,
    pub total_heat_dissipated: f64,
    pub heat_dissipated_this_game: f64,
    pub exotic_particles: f64,
    pub total_exotic_particles: f64,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
#[serde(default)]
pub struct SaveComponent {
    pub name: String,
    pub heat: f64,
    pub durability: f64,
    pub depleted: bool,
    pub x: i32,
    pub y: i32,
    pub z: i32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(default)]
pub struct SaveData {
    pub version: u32,
    pub store: SaveStore,
    pub upgrade_levels: Vec<u32>,
    pub reactor_heat: f64,
    pub stored_power: f64,
    pub depleted_protium_count: u32,
    pub paused: bool,
    pub replace_mode: bool,
    pub total_ticks: u64,
    pub prestige_level: u32,
    pub shop_page: i32,
    pub selected_component_index: i32,
    pub components: Vec<SaveComponent>,
}

impl Default for SaveData {
    fn default() -> Self {
        Self {
            version: 1,
            store: SaveStore::default(),
            upgrade_levels: Vec::new(),
            reactor_heat: 0.0,
            stored_power: 0.0,
            depleted_protium_count: 0,
            paused: false,
            replace_mode: true,
            total_ticks: 0,
            prestige_level: 0,
            shop_page: 0,
            selected_component_index: -1,
            components: Vec::new(),
        }
    }
}
