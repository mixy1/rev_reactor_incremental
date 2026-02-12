use anyhow::{Context, Result};
use base64::{Engine as _, engine::general_purpose::STANDARD};

use super::SaveData;

pub fn save_to_json_string(save_data: &SaveData) -> Result<String> {
    serde_json::to_string(save_data).context("failed to serialize save data to JSON")
}

pub fn load_from_json_string(json: &str) -> Result<SaveData> {
    serde_json::from_str(json).context("failed to parse save JSON")
}

pub fn export_to_base64(save_data: &SaveData) -> Result<String> {
    let json = save_to_json_string(save_data)?;
    Ok(STANDARD.encode(json.as_bytes()))
}

pub fn import_from_base64(encoded: &str) -> Result<SaveData> {
    let trimmed = encoded.trim();
    let raw = STANDARD
        .decode(trimmed)
        .context("failed to decode base64 save payload")?;
    let json = String::from_utf8(raw).context("decoded base64 payload is not UTF-8")?;
    load_from_json_string(&json)
}
