mod bridge;
mod codec;
mod model;

pub use bridge::{apply_save_data, save_data_from_simulation};
pub use codec::{export_to_base64, import_from_base64, load_from_json_string, save_to_json_string};
pub use model::{SaveComponent, SaveData, SaveStore};

#[cfg(test)]
mod tests {
    use super::{
        SaveComponent, SaveData, SaveStore, apply_save_data, export_to_base64, import_from_base64,
        load_from_json_string, save_data_from_simulation, save_to_json_string,
    };
    use crate::{ComponentKind, FuelKind, GridCoord, Simulation};

    fn sample_save() -> SaveData {
        SaveData {
            version: 1,
            store: SaveStore {
                money: 1234.5,
                total_money: 3456.7,
                money_earned_this_game: 2222.2,
                power: 111.0,
                total_power_produced: 999.9,
                power_produced_this_game: 888.8,
                heat: 12.3,
                total_heat_dissipated: 45.6,
                heat_dissipated_this_game: 7.8,
                exotic_particles: 3.0,
                total_exotic_particles: 10.0,
            },
            upgrade_levels: vec![1, 0, 2, 4],
            reactor_heat: 12.0,
            stored_power: 77.0,
            depleted_protium_count: 5,
            paused: true,
            replace_mode: false,
            total_ticks: 42,
            prestige_level: 2,
            shop_page: 1,
            selected_component_index: 7,
            components: vec![
                SaveComponent {
                    name: "Fuel1-1".to_string(),
                    heat: 1.5,
                    durability: 13.0,
                    depleted: false,
                    x: 2,
                    y: 3,
                    z: 0,
                },
                SaveComponent {
                    name: "Vent1".to_string(),
                    heat: 0.1,
                    durability: 0.0,
                    depleted: false,
                    x: 1,
                    y: 0,
                    z: 0,
                },
            ],
        }
    }

    #[test]
    fn save_json_round_trip() {
        let original = sample_save();
        let json = save_to_json_string(&original).expect("save JSON should serialize");
        let restored = load_from_json_string(&json).expect("save JSON should deserialize");

        assert_eq!(restored, original);
    }

    #[test]
    fn save_base64_round_trip() {
        let original = sample_save();
        let encoded = export_to_base64(&original).expect("save should export to base64");
        let restored = import_from_base64(&encoded).expect("save should import from base64");

        assert_eq!(restored, original);
    }

    #[test]
    fn simulation_bridge_round_trip() {
        let mut sim = Simulation::default();
        sim.resources.money = 222.0;
        sim.resources.power = 10.0;
        sim.resources.heat = 4.5;
        sim.place_component(
            GridCoord::new(2, 3, 0),
            ComponentKind::Fuel(FuelKind::Uranium),
        )
        .expect("should place component");
        if let Some(component) = sim.component_at_mut(GridCoord::new(2, 3, 0)) {
            component.heat = 3.25;
            component.durability = 77.0;
        }

        let save = save_data_from_simulation(&sim, 4, 1);
        let mut restored = Simulation::default();
        apply_save_data(&mut restored, &save).expect("save apply should succeed");

        assert_eq!(restored.resources.money, 222.0);
        assert_eq!(restored.resources.power, 10.0);
        assert_eq!(restored.resources.heat, 4.5);
        let component = restored
            .component_at(GridCoord::new(2, 3, 0))
            .expect("component should exist");
        assert_eq!(component.kind, ComponentKind::Fuel(FuelKind::Uranium));
        assert!((component.heat - 3.25).abs() <= f64::EPSILON);
        assert!((component.durability - 77.0).abs() <= f64::EPSILON);
    }
}
