use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UpgradeDataFile {
    #[serde(default)]
    pub upgrades: Vec<UpgradeDefinition>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UpgradeDefinition {
    pub index: u32,
    pub name: String,
    #[serde(default)]
    pub level_names: Vec<String>,
    #[serde(default)]
    pub description: String,
    pub base_cost: f64,
    pub cost_multiplier: f64,
    pub purchasable: bool,
    pub is_prestige: bool,
    pub prerequisite: i32,
    #[serde(default)]
    pub bonuses: Vec<UpgradeBonus>,
    #[serde(default)]
    pub icon: String,
    #[serde(default)]
    pub category: String,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct UpgradeBonus {
    pub component_type: i32,
    pub stat_category: i32,
    #[serde(default)]
    pub additive: f64,
    #[serde(default = "default_multiplicative")]
    pub multiplicative: f64,
}

const fn default_multiplicative() -> f64 {
    1.0
}
