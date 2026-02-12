use bevy::prelude::*;

#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, States, Default)]
pub enum AppPhase {
    #[default]
    Boot,
    InGame,
}

#[derive(Debug, Clone, Copy, Eq, PartialEq, Hash, States, Default)]
pub enum SimRunState {
    #[default]
    Running,
    Paused,
}
