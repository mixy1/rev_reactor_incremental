use bevy::prelude::*;

use super::resources::{ComponentCatalog, GridAction, RuntimeConfig, SelectionState, SessionState};

pub fn apply_grid_actions(
    mut actions: EventReader<GridAction>,
    mut session: ResMut<SessionState>,
    selection: Res<SelectionState>,
    catalog: Res<ComponentCatalog>,
    config: Res<RuntimeConfig>,
) {
    let Some(selected_spec) = catalog.selected(&selection).copied() else {
        return;
    };

    let mut grid_changed = false;

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
                    spend_money(&mut session, selected_spec.cost);
                    grid_changed = true;
                }
            }
            GridAction::Remove(coord) => {
                let Some(existing_kind) = session.simulation.grid.get(coord) else {
                    continue;
                };
                if session.simulation.remove_component(coord).is_ok() {
                    let refund = catalog.sell_value(existing_kind, config.sell_refund_ratio);
                    session.simulation.resources.add_money(refund);
                    grid_changed = true;
                }
            }
        }
    }

    if grid_changed {
        recalculate_rates(&mut session, &catalog);
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

pub fn mark_sim_running(session: Option<ResMut<SessionState>>) {
    if let Some(mut session) = session {
        session.simulation.paused = false;
    }
}

pub fn mark_sim_paused(session: Option<ResMut<SessionState>>) {
    if let Some(mut session) = session {
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

fn recalculate_rates(session: &mut SessionState, catalog: &ComponentCatalog) {
    let mut power_rate = 0.0;
    let mut heat_rate = 0.0;

    for component in &session.simulation.components {
        if let Some(spec) = catalog.spec_for_kind(component.kind) {
            power_rate += spec.power_per_tick;
            heat_rate += spec.heat_per_tick;
        }
    }

    session.simulation.base_power_generation_per_tick = power_rate;
    session.simulation.base_heat_generation_per_tick = heat_rate;
}
