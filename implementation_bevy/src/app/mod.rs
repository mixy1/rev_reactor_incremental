mod input;
mod resources;
mod setup;
mod simulation;
mod state;
mod view;

use bevy::prelude::*;

use resources::{ComponentCatalog, GridAction, HoveredCell, RuntimeConfig, SelectionState};
use state::{AppPhase, SimRunState};

pub struct ReactorAppPlugin;

impl Plugin for ReactorAppPlugin {
    fn build(&self, app: &mut App) {
        app.init_state::<AppPhase>()
            .init_state::<SimRunState>()
            .init_resource::<RuntimeConfig>()
            .init_resource::<SelectionState>()
            .init_resource::<HoveredCell>()
            .init_resource::<ComponentCatalog>()
            .add_event::<GridAction>()
            .add_systems(Startup, setup::spawn_camera)
            .add_systems(OnEnter(AppPhase::Boot), setup::bootstrap_session)
            .add_systems(
                OnEnter(AppPhase::InGame),
                (view::spawn_grid, view::spawn_hud),
            )
            .add_systems(OnEnter(SimRunState::Running), simulation::mark_sim_running)
            .add_systems(OnEnter(SimRunState::Paused), simulation::mark_sim_paused)
            .add_systems(
                Update,
                (
                    input::handle_keyboard_controls,
                    input::update_hovered_cell,
                    input::emit_mouse_actions,
                    simulation::handle_save_hotkeys,
                    simulation::apply_grid_actions,
                    simulation::tick_simulation.run_if(in_state(SimRunState::Running)),
                    simulation::autosave_session,
                    view::refresh_grid_visuals,
                    view::refresh_hud,
                )
                    .chain()
                    .run_if(in_state(AppPhase::InGame)),
            );
    }
}
