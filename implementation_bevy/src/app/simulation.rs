use std::fs;

use bevy::prelude::*;
use implementation_bevy::{
    apply_save_data, load_from_json_string, save_data_from_simulation, save_to_json_string,
};

use super::resources::{ComponentCatalog, GridAction, RuntimeConfig, SelectionState, SessionState};
use super::state::SimRunState;

pub fn apply_grid_actions(
    mut actions: EventReader<GridAction>,
    mut session: ResMut<SessionState>,
    selection: Res<SelectionState>,
    catalog: Res<ComponentCatalog>,
    config: Res<RuntimeConfig>,
) {
    let Some(selected_spec) = catalog.selected(&selection).cloned() else {
        return;
    };

    for action in actions.read() {
        match *action {
            GridAction::Place(coord) => {
                if session.simulation.grid.get(coord).is_some() {
                    continue;
                }
                if session.simulation.resources.money + f64::EPSILON < selected_spec.cost {
                    continue;
                }
                if session
                    .simulation
                    .place_component(coord, selected_spec.kind)
                    .is_ok()
                {
                    if let Some(component) = session.simulation.component_at_mut(coord) {
                        component.stats_override = Some(selected_spec.stats);
                        component.source_name = selected_spec.name.clone();
                    }
                    session
                        .placed_spec_by_coord
                        .insert(coord, selected_spec.slot);
                    spend_money(&mut session, selected_spec.cost);
                }
            }
            GridAction::Remove(coord) => {
                let Some(slot) = session.placed_spec_by_coord.get(&coord).copied() else {
                    continue;
                };
                if session.simulation.remove_component(coord).is_ok() {
                    session.placed_spec_by_coord.remove(&coord);
                    let refund = catalog.sell_value_for_slot(slot, config.sell_refund_ratio);
                    session.simulation.resources.add_money(refund);
                }
            }
        }
    }
}

pub fn tick_simulation(time: Res<Time>, mut session: ResMut<SessionState>) {
    let steps = session
        .tick_timer
        .tick(time.delta())
        .times_finished_this_tick();

    for _ in 0..steps {
        session.simulation.tick();
    }
}

pub fn autosave_session(
    time: Res<Time>,
    config: Res<RuntimeConfig>,
    selection: Res<SelectionState>,
    mut session: ResMut<SessionState>,
) {
    if session.autosave_timer.tick(time.delta()).just_finished() {
        match save_session_to_disk(&session, &config, selection.index) {
            Ok(()) => session.last_save_error = None,
            Err(err) => session.last_save_error = Some(err),
        }
    }
}

pub fn handle_save_hotkeys(
    keys: Res<ButtonInput<KeyCode>>,
    config: Res<RuntimeConfig>,
    mut selection: ResMut<SelectionState>,
    catalog: Res<ComponentCatalog>,
    mut session: ResMut<SessionState>,
    mut next_run_state: ResMut<NextState<SimRunState>>,
) {
    if keys.just_pressed(KeyCode::F5) {
        match save_session_to_disk(&session, &config, selection.index) {
            Ok(()) => session.last_save_error = None,
            Err(err) => session.last_save_error = Some(err),
        }
    }

    if keys.just_pressed(KeyCode::F9) {
        match load_session_from_disk(&mut session, &catalog, &config) {
            Ok(selected_index) => {
                if selected_index >= 0 {
                    selection.index = selected_index as usize;
                }
                let state = if session.simulation.paused {
                    SimRunState::Paused
                } else {
                    SimRunState::Running
                };
                next_run_state.set(state);
                session.last_save_error = None;
            }
            Err(err) => session.last_save_error = Some(err),
        }
    }
}

pub fn mark_sim_running(mut session: Option<ResMut<SessionState>>) {
    if let Some(ref mut session) = session {
        session.simulation.paused = false;
    }
}

pub fn mark_sim_paused(mut session: Option<ResMut<SessionState>>) {
    if let Some(ref mut session) = session {
        session.simulation.paused = true;
    }
}

fn spend_money(session: &mut SessionState, amount: f64) {
    if amount <= 0.0 {
        return;
    }
    session.simulation.resources.money = (session.simulation.resources.money - amount).max(0.0);
    session.simulation.resources.tick_deltas.money -= amount;
}

fn save_session_to_disk(
    session: &SessionState,
    config: &RuntimeConfig,
    selected_index: usize,
) -> Result<(), String> {
    let save_data = save_data_from_simulation(&session.simulation, selected_index as i32, 0);
    let encoded = save_to_json_string(&save_data).map_err(|err| err.to_string())?;
    fs::write(&config.save_path, encoded).map_err(|err| {
        format!(
            "failed writing save to {}: {err}",
            config.save_path.display()
        )
    })
}

fn load_session_from_disk(
    session: &mut SessionState,
    catalog: &ComponentCatalog,
    config: &RuntimeConfig,
) -> Result<i32, String> {
    let raw = fs::read_to_string(&config.save_path)
        .map_err(|err| format!("failed reading save {}: {err}", config.save_path.display()))?;
    let save_data = load_from_json_string(&raw).map_err(|err| err.to_string())?;
    apply_save_data(&mut session.simulation, &save_data).map_err(|err| err.to_string())?;

    session.placed_spec_by_coord.clear();
    for component in &mut session.simulation.components {
        if let Some((slot, spec)) = catalog
            .all_specs()
            .iter()
            .enumerate()
            .find(|(_, spec)| spec.name == component.source_name)
        {
            component.stats_override = Some(spec.stats);
            component.source_name = spec.name.clone();
            session.placed_spec_by_coord.insert(component.coord, slot);
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
            session.placed_spec_by_coord.insert(component.coord, slot);
        }
    }

    Ok(save_data.selected_component_index)
}
