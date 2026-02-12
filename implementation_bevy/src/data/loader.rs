use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::de::DeserializeOwned;

use super::{ComponentTypesFile, UpgradeDataFile};

const COMPONENT_TYPES_RELATIVE_PATH: &str = "../implementation/src/game/component_types.json";
const UPGRADE_DATA_RELATIVE_PATH: &str = "../implementation/src/game/upgrade_data.json";

pub fn component_types_path() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(COMPONENT_TYPES_RELATIVE_PATH)
}

pub fn upgrade_data_path() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(UPGRADE_DATA_RELATIVE_PATH)
}

pub fn load_component_types() -> Result<ComponentTypesFile> {
    load_component_types_from_path(component_types_path())
}

pub fn load_component_types_from_path(path: impl AsRef<Path>) -> Result<ComponentTypesFile> {
    read_json(path.as_ref(), "component types")
}

pub fn load_upgrade_data() -> Result<UpgradeDataFile> {
    load_upgrade_data_from_path(upgrade_data_path())
}

pub fn load_upgrade_data_from_path(path: impl AsRef<Path>) -> Result<UpgradeDataFile> {
    read_json(path.as_ref(), "upgrade data")
}

fn read_json<T>(path: &Path, label: &str) -> Result<T>
where
    T: DeserializeOwned,
{
    let raw = fs::read_to_string(path)
        .with_context(|| format!("failed reading {label} file: {}", path.display()))?;

    serde_json::from_str(&raw)
        .with_context(|| format!("failed parsing {label} file as JSON: {}", path.display()))
}
