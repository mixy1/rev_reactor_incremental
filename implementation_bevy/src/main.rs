use bevy::prelude::*;
use bevy::window::{PresentMode, Window};

mod app;

fn main() {
    App::new()
        .insert_resource(ClearColor(Color::srgb(0.02, 0.02, 0.03)))
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Rev Reactor (Bevy)".to_string(),
                resolution: (1280.0, 720.0).into(),
                present_mode: PresentMode::AutoVsync,
                resizable: true,
                ..default()
            }),
            ..default()
        }))
        .add_plugins(app::ReactorAppPlugin)
        .run();
}
