use std::fs;

use bevy::prelude::*;
use implementation_bevy::{Simulation, apply_save_data, load_from_json_string};

use super::resources::{
    ComponentCatalog, GridLayout, RuntimeConfig, SelectionState, SessionState, SpriteCatalog,
};
use super::state::{AppPhase, SimRunState};

pub fn spawn_camera(mut commands: Commands) {
    commands.spawn((Name::new("PrimaryCamera"), Camera2d));
}

pub fn bootstrap_session(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    config: Res<RuntimeConfig>,
    catalog: Res<ComponentCatalog>,
    mut selection: ResMut<SelectionState>,
    mut next_phase: ResMut<NextState<AppPhase>>,
    mut next_run_state: ResMut<NextState<SimRunState>>,
) {
    let mut simulation = Simulation::new(config.grid_width, config.grid_height, config.grid_layers);
    simulation.resources.money = config.start_money;

    let mut loaded_from_save = false;
    if let Ok(text) = fs::read_to_string(&config.save_path)
        && let Ok(save_data) = load_from_json_string(&text)
        && apply_save_data(&mut simulation, &save_data).is_ok()
    {
        loaded_from_save = true;
        if save_data.selected_component_index >= 0 {
            selection.index = save_data.selected_component_index as usize;
        }
        next_run_state.set(if save_data.paused {
            SimRunState::Paused
        } else {
            SimRunState::Running
        });
    }

    if !loaded_from_save {
        next_run_state.set(SimRunState::Running);
    }

    let selection_index = selection.index;
    catalog.set_selection_index(&mut selection, selection_index);

    let mut sprite_catalog = SpriteCatalog::default();
    for spec in catalog.all_specs() {
        let path = format!("sprites/{}.png", spec.sprite_name);
        let handle: Handle<Image> = asset_server.load(path);
        sprite_catalog.insert(spec.slot, handle);
    }
    commands.insert_resource(sprite_catalog);

    let mut placed_spec_by_coord = std::collections::HashMap::new();
    for component in &mut simulation.components {
        if let Some((slot, spec)) = catalog
            .all_specs()
            .iter()
            .enumerate()
            .find(|(_, spec)| spec.name == component.source_name)
        {
            component.stats_override = Some(spec.stats);
            component.source_name = spec.name.clone();
            placed_spec_by_coord.insert(component.coord, slot);
            continue;
        }
        if let Some((slot, spec)) = catalog
            .all_specs()
            .iter()
            .enumerate()
            .find(|(_, spec)| spec.kind == component.kind)
        {
            component.stats_override = Some(spec.stats);
            component.source_name = spec.name.clone();
            placed_spec_by_coord.insert(component.coord, slot);
        }
    }

    commands.insert_resource(GridLayout::new(
        config.grid_width,
        config.grid_height,
        config.cell_size,
        config.cell_gap,
    ));

    commands.insert_resource(SessionState {
        simulation,
        tick_timer: Timer::from_seconds((1.0 / config.tick_hz).max(0.01), TimerMode::Repeating),
        autosave_timer: Timer::from_seconds(
            config.auto_save_interval_seconds.max(1.0),
            TimerMode::Repeating,
        ),
        last_save_error: None,
        placed_spec_by_coord,
    });

    next_phase.set(AppPhase::InGame);
}
