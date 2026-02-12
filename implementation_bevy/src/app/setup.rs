use bevy::prelude::*;
use implementation_bevy::Simulation;

use super::resources::{GridLayout, RuntimeConfig, SessionState};
use super::state::AppPhase;

pub fn spawn_camera(mut commands: Commands) {
    commands.spawn((Name::new("PrimaryCamera"), Camera2d));
}

pub fn bootstrap_session(
    mut commands: Commands,
    config: Res<RuntimeConfig>,
    mut next_phase: ResMut<NextState<AppPhase>>,
) {
    let mut simulation = Simulation::new(config.grid_width, config.grid_height, config.grid_layers);
    simulation.resources.money = config.start_money;

    commands.insert_resource(GridLayout::new(
        config.grid_width,
        config.grid_height,
        config.cell_size,
        config.cell_gap,
    ));

    commands.insert_resource(SessionState {
        simulation,
        tick_timer: Timer::from_seconds((1.0 / config.tick_hz).max(0.01), TimerMode::Repeating),
    });

    next_phase.set(AppPhase::InGame);
}
