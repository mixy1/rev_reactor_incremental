use bevy::asset::AssetPlugin;
use bevy::prelude::*;
use bevy::render::{
    RenderPlugin,
    settings::{WgpuFeatures, WgpuSettings, WgpuSettingsPriority},
};
use bevy::window::{PresentMode, Window};

mod app;

fn main() {
    let asset_root = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../decompilation/recovered/recovered_assets");

    App::new()
        .insert_resource(ClearColor(Color::srgb(0.02, 0.02, 0.03)))
        .add_plugins(
            DefaultPlugins
                .set(WindowPlugin {
                    primary_window: Some(Window {
                        title: "Rev Reactor (Bevy)".to_string(),
                        resolution: (1280.0, 720.0).into(),
                        present_mode: PresentMode::AutoVsync,
                        resizable: true,
                        ..default()
                    }),
                    ..default()
                })
                .set(AssetPlugin {
                    file_path: asset_root.display().to_string(),
                    ..default()
                })
                .set(RenderPlugin {
                    render_creation: WgpuSettings {
                        priority: WgpuSettingsPriority::Compatibility,
                        features: WgpuFeatures::empty(),
                        ..default()
                    }
                    .into(),
                    ..default()
                }),
        )
        .add_plugins(app::ReactorAppPlugin)
        .run();
}
