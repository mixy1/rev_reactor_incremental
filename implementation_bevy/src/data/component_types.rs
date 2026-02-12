use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ComponentTypesFile {
    #[serde(rename = "_source", default)]
    pub source: String,
    #[serde(default)]
    pub components: Vec<ComponentTypeDefinition>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ComponentTypeDefinition {
    #[serde(rename = "Name")]
    pub name: String,
    #[serde(rename = "Sprite")]
    pub sprite: String,
    #[serde(rename = "Cost")]
    pub cost: f64,
    #[serde(rename = "Description", default)]
    pub description: String,
    #[serde(rename = "CellData")]
    pub cell_data: Option<CellData>,
    #[serde(rename = "HeatData")]
    pub heat_data: Option<HeatData>,
    #[serde(rename = "MaxDurability")]
    pub max_durability: Option<f64>,
    #[serde(rename = "HeatCapacity")]
    pub heat_capacity: Option<f64>,
    #[serde(rename = "ReactorHeatCapacityIncrease")]
    pub reactor_heat_capacity_increase: Option<f64>,
    #[serde(rename = "ReactorPowerCapacityIncrease")]
    pub reactor_power_capacity_increase: Option<f64>,
    #[serde(rename = "ReflectsPulses")]
    pub reflects_pulses: Option<f64>,
    #[serde(rename = "_meta", default)]
    pub meta: ComponentMetadata,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct CellData {
    #[serde(rename = "EnergyPerPulse")]
    pub energy_per_pulse: f64,
    #[serde(rename = "HeatPerPulse")]
    pub heat_per_pulse: f64,
    #[serde(rename = "PulsesPerCore")]
    pub pulses_per_core: f64,
    #[serde(rename = "NumberOfCores")]
    pub number_of_cores: u32,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct HeatData {
    #[serde(rename = "SelfVentRate")]
    #[serde(default)]
    pub self_vent_rate: f64,
    #[serde(rename = "NeighborAffects")]
    #[serde(default)]
    pub neighbor_affects: bool,
    #[serde(rename = "ReactorVentRate")]
    #[serde(default)]
    pub reactor_vent_rate: f64,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct ComponentMetadata {
    #[serde(default)]
    pub field_index: u32,
    #[serde(default)]
    pub offset: String,
    #[serde(default)]
    pub factory: String,
    #[serde(default)]
    pub type_of_component: String,
    #[serde(default)]
    pub tier: u32,
    pub variant: Option<u32>,
    pub type_of_component_id: Option<u32>,
    pub type_of_heat_exchange: Option<u32>,
    pub cant_lose_heat: Option<bool>,
    pub requires_upgrade: Option<bool>,
}
