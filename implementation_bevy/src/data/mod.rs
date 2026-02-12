mod component_types;
mod loader;
mod upgrade_data;

pub use component_types::{
    CellData, ComponentMetadata, ComponentTypeDefinition, ComponentTypesFile, HeatData,
};
pub use loader::{
    component_types_path, load_component_types, load_component_types_from_path, load_upgrade_data,
    load_upgrade_data_from_path, upgrade_data_path,
};
pub use upgrade_data::{UpgradeBonus, UpgradeDataFile, UpgradeDefinition};

#[cfg(test)]
mod tests {
    use super::{load_component_types, load_upgrade_data};

    #[test]
    fn bundled_data_files_have_entries() {
        let component_types = load_component_types().expect("component types should load");
        let upgrade_data = load_upgrade_data().expect("upgrade data should load");

        assert!(
            !component_types.components.is_empty(),
            "component_types.json should include at least one component"
        );
        assert!(
            !upgrade_data.upgrades.is_empty(),
            "upgrade_data.json should include at least one upgrade"
        );
    }
}
