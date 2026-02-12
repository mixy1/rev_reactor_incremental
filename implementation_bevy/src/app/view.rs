use bevy::prelude::*;

use super::resources::{
    ComponentCatalog, GridLayout, GridTile, HoveredCell, HudText, RuntimeConfig, SelectionState,
    SessionState, SpriteCatalog,
};
use super::state::SimRunState;

const EMPTY_TILE_COLOR: Color = Color::srgb(0.11, 0.13, 0.16);
const HOVER_TILE_COLOR: Color = Color::srgb(0.24, 0.27, 0.31);
const HOVER_OCCUPIED_TINT: Color = Color::srgba(1.0, 1.0, 1.0, 0.9);

pub fn spawn_grid(mut commands: Commands, config: Res<RuntimeConfig>, layout: Res<GridLayout>) {
    for y in 0..config.grid_height {
        for x in 0..config.grid_width {
            let coord = implementation_bevy::GridCoord::new(x, y, 0);
            commands.spawn((
                Name::new(format!("Tile({x},{y})")),
                Sprite::from_color(EMPTY_TILE_COLOR, Vec2::splat(layout.cell_size)),
                Transform::from_translation(layout.cell_center(coord)),
                GridTile { coord },
            ));
        }
    }
}

pub fn refresh_grid_visuals(
    session: Res<SessionState>,
    catalog: Res<ComponentCatalog>,
    sprites: Res<SpriteCatalog>,
    layout: Res<GridLayout>,
    hovered: Res<HoveredCell>,
    mut tiles: Query<(&GridTile, &mut Sprite)>,
) {
    for (tile, mut sprite) in &mut tiles {
        let is_hovered = hovered.0 == Some(tile.coord);

        if let Some(slot) = session.placed_spec_by_coord.get(&tile.coord).copied() {
            if let Some(handle) = sprites.get(slot) {
                sprite.image = handle.clone();
                sprite.custom_size = Some(Vec2::new(layout.cell_size, layout.cell_size));
                sprite.color = if is_hovered {
                    HOVER_OCCUPIED_TINT
                } else {
                    Color::WHITE
                };
                continue;
            }

            sprite.image = Handle::default();
            sprite.custom_size = Some(Vec2::new(layout.cell_size, layout.cell_size));
            sprite.color = catalog
                .spec_for_slot(slot)
                .map(|entry| entry.color)
                .unwrap_or(Color::srgb(0.48, 0.48, 0.48));
            continue;
        }

        sprite.image = Handle::default();
        sprite.custom_size = Some(Vec2::new(layout.cell_size, layout.cell_size));
        sprite.color = if is_hovered {
            HOVER_TILE_COLOR
        } else {
            EMPTY_TILE_COLOR
        };
    }
}

pub fn spawn_hud(mut commands: Commands) {
    commands.spawn((
        Name::new("HudText"),
        HudText,
        Text::new("Initializing..."),
        TextFont {
            font_size: 18.0,
            ..default()
        },
        TextColor(Color::srgb(0.94, 0.97, 0.99)),
        Node {
            position_type: PositionType::Absolute,
            left: Val::Px(12.0),
            top: Val::Px(10.0),
            ..default()
        },
    ));
}

pub fn refresh_hud(
    session: Res<SessionState>,
    catalog: Res<ComponentCatalog>,
    selection: Res<SelectionState>,
    hovered: Res<HoveredCell>,
    run_state: Res<State<SimRunState>>,
    mut hud_query: Query<&mut Text, With<HudText>>,
) {
    let Ok(mut hud) = hud_query.get_single_mut() else {
        return;
    };

    let selected = catalog
        .selected(&selection)
        .map(|spec| spec.name.as_str())
        .unwrap_or("None");

    let run_label = match run_state.get() {
        SimRunState::Running => "RUNNING",
        SimRunState::Paused => "PAUSED",
    };

    let hovered_label = hovered
        .0
        .map(|coord| format!("{},{}", coord.x, coord.y))
        .unwrap_or_else(|| "-".to_string());

    let save_line = session
        .last_save_error
        .as_deref()
        .map(|msg| format!("Save: {msg}"))
        .unwrap_or_else(|| "Save: OK (F5 save, F9 load, autosave on)".to_string());

    *hud = Text::new(format!(
        "Money: ${:.1}  Power: {:.1}  Heat: {:.1}  Tick: {}\nMode: {}  Selected: {} ({}/{})  Hover: {}\n1-9 quick select, Q/E cycle, Left place, Right sell, Space/P pause\n{}",
        session.simulation.resources.money,
        session.simulation.resources.power,
        session.simulation.resources.heat,
        session.simulation.tick_index,
        run_label,
        selected,
        selection.index.saturating_add(1),
        catalog.len(),
        hovered_label,
        save_line,
    ));
}
