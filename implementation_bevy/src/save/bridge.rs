use anyhow::{Result, anyhow};

use crate::{GridCoord, Simulation, model::ComponentKind};

use super::{SaveComponent, SaveData, SaveStore};

pub fn save_data_from_simulation(
    sim: &Simulation,
    selected_component_index: i32,
    shop_page: i32,
) -> SaveData {
    let mut components = sim
        .components
        .iter()
        .map(|component| SaveComponent {
            name: component.kind.canonical_name(),
            heat: component.heat,
            durability: component.durability,
            depleted: component.depleted,
            x: component.coord.x as i32,
            y: component.coord.y as i32,
            z: component.coord.z as i32,
        })
        .collect::<Vec<_>>();
    components.sort_by(|a, b| (a.z, a.y, a.x).cmp(&(b.z, b.y, b.x)));

    SaveData {
        version: 1,
        store: SaveStore {
            money: sim.resources.money,
            total_money: sim.resources.total_money,
            money_earned_this_game: sim.resources.money_earned_this_game,
            power: sim.resources.power,
            total_power_produced: sim.resources.total_power_produced,
            power_produced_this_game: sim.resources.power_produced_this_game,
            heat: sim.resources.heat,
            total_heat_dissipated: sim.resources.total_heat_dissipated,
            heat_dissipated_this_game: sim.resources.heat_dissipated_this_game,
            exotic_particles: sim.resources.exotic_particles,
            total_exotic_particles: sim.resources.total_exotic_particles,
        },
        upgrade_levels: Vec::new(),
        reactor_heat: sim.resources.heat,
        stored_power: sim.resources.power,
        depleted_protium_count: 0,
        paused: sim.paused,
        replace_mode: true,
        total_ticks: sim.tick_index,
        prestige_level: 0,
        shop_page,
        selected_component_index,
        components,
    }
}

pub fn apply_save_data(sim: &mut Simulation, save: &SaveData) -> Result<()> {
    sim.resources.money = save.store.money;
    sim.resources.total_money = save.store.total_money;
    sim.resources.money_earned_this_game = save.store.money_earned_this_game;
    sim.resources.power = save.store.power;
    sim.resources.total_power_produced = save.store.total_power_produced;
    sim.resources.power_produced_this_game = save.store.power_produced_this_game;
    sim.resources.heat = save.store.heat;
    sim.resources.total_heat_dissipated = save.store.total_heat_dissipated;
    sim.resources.heat_dissipated_this_game = save.store.heat_dissipated_this_game;
    sim.resources.exotic_particles = save.store.exotic_particles;
    sim.resources.total_exotic_particles = save.store.total_exotic_particles;
    sim.tick_index = save.total_ticks;
    sim.paused = save.paused;

    sim.clear_all_components();

    for entry in &save.components {
        if entry.x < 0 || entry.y < 0 || entry.z < 0 {
            continue;
        }
        let Some(kind) = ComponentKind::from_name(&entry.name) else {
            continue;
        };
        let coord = GridCoord::new(entry.x as usize, entry.y as usize, entry.z as usize);
        if !sim.grid.in_bounds(coord) {
            continue;
        }
        sim.place_component(coord, kind).map_err(|err| {
            anyhow!(
                "failed placing component at ({},{},{}): {err:?}",
                entry.x,
                entry.y,
                entry.z
            )
        })?;
        if let Some(component) = sim.component_at_mut(coord) {
            component.heat = entry.heat.max(0.0);
            component.durability = entry.durability.max(0.0);
            component.depleted = entry.depleted || component.durability <= 0.0;
            if component.depleted {
                component.pulse_count = 0;
                component.last_power = 0.0;
                component.last_heat = 0.0;
            }
        }
    }

    Ok(())
}
