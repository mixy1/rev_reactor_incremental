use bevy::prelude::*;

use super::resources::{
    ComponentCatalog, GridAction, GridLayout, HoveredCell, RuntimeConfig, SelectionState,
};
use super::state::SimRunState;

pub fn handle_keyboard_controls(
    keys: Res<ButtonInput<KeyCode>>,
    catalog: Res<ComponentCatalog>,
    mut selection: ResMut<SelectionState>,
    run_state: Res<State<SimRunState>>,
    mut next_run_state: ResMut<NextState<SimRunState>>,
) {
    if keys.just_pressed(KeyCode::Digit1) {
        catalog.set_selection_index(&mut selection, 0);
    }
    if keys.just_pressed(KeyCode::Digit2) {
        catalog.set_selection_index(&mut selection, 1);
    }
    if keys.just_pressed(KeyCode::Digit3) {
        catalog.set_selection_index(&mut selection, 2);
    }
    if keys.just_pressed(KeyCode::Digit4) {
        catalog.set_selection_index(&mut selection, 3);
    }
    if keys.just_pressed(KeyCode::Digit5) {
        catalog.set_selection_index(&mut selection, 4);
    }
    if keys.just_pressed(KeyCode::Digit6) {
        catalog.set_selection_index(&mut selection, 5);
    }
    if keys.just_pressed(KeyCode::Digit7) {
        catalog.set_selection_index(&mut selection, 6);
    }
    if keys.just_pressed(KeyCode::Digit8) {
        catalog.set_selection_index(&mut selection, 7);
    }
    if keys.just_pressed(KeyCode::Digit9) {
        catalog.set_selection_index(&mut selection, 8);
    }

    if keys.just_pressed(KeyCode::KeyQ) {
        catalog.step_selection(&mut selection, -1);
    }
    if keys.just_pressed(KeyCode::KeyE) {
        catalog.step_selection(&mut selection, 1);
    }

    if keys.just_pressed(KeyCode::Space) || keys.just_pressed(KeyCode::KeyP) {
        let next = match run_state.get() {
            SimRunState::Running => SimRunState::Paused,
            SimRunState::Paused => SimRunState::Running,
        };
        next_run_state.set(next);
    }
}

pub fn update_hovered_cell(
    windows: Query<&Window>,
    camera_query: Query<(&Camera, &GlobalTransform), With<Camera2d>>,
    layout: Res<GridLayout>,
    config: Res<RuntimeConfig>,
    mut hovered: ResMut<HoveredCell>,
) {
    let Ok(window) = windows.get_single() else {
        hovered.0 = None;
        return;
    };

    let Some(cursor_position) = window.cursor_position() else {
        hovered.0 = None;
        return;
    };

    let Ok((camera, camera_transform)) = camera_query.get_single() else {
        hovered.0 = None;
        return;
    };

    let Ok(world) = camera.viewport_to_world_2d(camera_transform, cursor_position) else {
        hovered.0 = None;
        return;
    };

    hovered.0 = layout.world_to_coord(
        world,
        config.grid_width,
        config.grid_height,
        config.grid_layers.saturating_sub(1),
    );
}

pub fn emit_mouse_actions(
    buttons: Res<ButtonInput<MouseButton>>,
    hovered: Res<HoveredCell>,
    mut actions: EventWriter<GridAction>,
) {
    let Some(coord) = hovered.0 else {
        return;
    };

    if buttons.just_pressed(MouseButton::Left) {
        actions.send(GridAction::Place(coord));
    }

    if buttons.just_pressed(MouseButton::Right) {
        actions.send(GridAction::Remove(coord));
    }
}
