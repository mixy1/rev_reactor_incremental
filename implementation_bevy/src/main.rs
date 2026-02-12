use bevy::prelude::*;
use bevy::window::{PresentMode, Window};

fn main() {
    App::new()
        .init_state::<app_state::AppState>()
        .insert_resource(resources::RuntimeConfig::default())
        .insert_resource(ClearColor(Color::srgb(0.02, 0.02, 0.03)))
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Rev Reactor (Bevy Scaffold)".to_string(),
                resolution: (1280.0, 720.0).into(),
                present_mode: PresentMode::AutoVsync,
                resizable: true,
                ..default()
            }),
            ..default()
        }))
        .add_plugins(app_shell::AppShellPlugin)
        .run();
}

mod app_state {
    use bevy::prelude::*;

    #[allow(dead_code)]
    #[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, States, Default)]
    pub enum AppState {
        #[default]
        Boot,
        MainMenu,
        InGame,
        Paused,
    }
}

mod resources {
    use bevy::prelude::*;

    #[derive(Resource, Debug, Clone)]
    pub struct RuntimeConfig {
        pub fixed_update_hz: u16,
        pub rng_seed: u64,
    }

    impl Default for RuntimeConfig {
        fn default() -> Self {
            Self {
                fixed_update_hz: 60,
                rng_seed: 0,
            }
        }
    }

    #[derive(Resource, Debug, Default)]
    pub struct SessionState {
        pub placeholder_loaded: bool,
    }
}

mod app_shell {
    use bevy::prelude::*;

    use crate::app_state::AppState;
    use crate::resources::{RuntimeConfig, SessionState};

    pub struct AppShellPlugin;

    impl Plugin for AppShellPlugin {
        fn build(&self, app: &mut App) {
            app.add_systems(Startup, setup_camera)
                .add_systems(OnEnter(AppState::Boot), bootstrap_session)
                .add_systems(Update, advance_from_boot.run_if(in_state(AppState::Boot)))
                .add_systems(Update, menu_stub.run_if(in_state(AppState::MainMenu)))
                .add_systems(Update, gameplay_stub.run_if(in_state(AppState::InGame)));
        }
    }

    fn setup_camera(mut commands: Commands) {
        commands.spawn((Name::new("PrimaryCamera"), Camera2d));
    }

    fn bootstrap_session(mut commands: Commands) {
        commands.insert_resource(SessionState {
            placeholder_loaded: true,
        });
    }

    fn advance_from_boot(mut next_state: ResMut<NextState<AppState>>) {
        next_state.set(AppState::MainMenu);
    }

    fn menu_stub(config: Res<RuntimeConfig>, session: Res<SessionState>) {
        let _ = (config.fixed_update_hz, config.rng_seed, session.placeholder_loaded);
    }

    fn gameplay_stub(config: Res<RuntimeConfig>) {
        let _ = config.fixed_update_hz;
    }
}
