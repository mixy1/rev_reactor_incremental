"""Save/load and export/import system for game state.

Auto-save: JSON to local file, auto-saves on exit, auto-loads on startup.
Export/Import: Base64-encoded text file for sharing saves.
Import also supports the original Reactor Idle encrypted format
(AES-256-CBC via .NET PasswordDeriveBytes).
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.simulation import Simulation

# ── Original game encryption parameters (RE: RijndaelSimple / Persistence) ──
_PASS_PHRASE = b"nucLERR8CTRzR4n"
_SALT_VALUE = b"superSPP#ci1lZlt"
_INIT_VECTOR = b"@x0B2!3D4ezF607m"
_KEY_SIZE = 256  # bits
_PASSWORD_ITERATIONS = 2

# Original game component type index → our catalog name (sprite-based).
# RE: component_types.json field_index ordering.
_ORIG_INDEX_TO_NAME = {
    0: "Fuel1-1", 1: "Fuel1-2", 2: "Fuel1-4",
    3: "Fuel2-1", 4: "Fuel2-2", 5: "Fuel2-4",
    6: "Fuel3-1", 7: "Fuel3-2", 8: "Fuel3-4",
    9: "Fuel4-1", 10: "Fuel4-2", 11: "Fuel4-4",
    12: "Fuel5-1", 13: "Fuel5-2", 14: "Fuel5-4",
    15: "Fuel6-1", 16: "Fuel6-2", 17: "Fuel6-4",
    18: "Fuel7-1", 19: "Fuel7-2", 20: "Fuel7-4",
    21: "Fuel8-1", 22: "Fuel8-2", 23: "Fuel8-4",
    24: "Fuel9-1", 25: "Fuel9-2", 26: "Fuel9-4",
    27: "Fuel10-1", 28: "Fuel10-2", 29: "Fuel10-4",
    30: "Fuel11-1", 31: "Fuel11-2", 32: "Fuel11-4",
    33: "Vent1", 34: "Vent2", 35: "Vent3", 36: "Vent4", 37: "Vent5",
    38: "Exchanger1", 39: "Exchanger2", 40: "Exchanger3",
    41: "Exchanger4", 42: "Exchanger5",
    43: "Inlet1", 44: "Inlet2", 45: "Inlet3", 46: "Inlet4", 47: "Inlet5",
    48: "Outlet1", 49: "Outlet2", 50: "Outlet3", 51: "Outlet4", 52: "Outlet5",
    53: "Reflector1", 54: "Reflector2", 55: "Reflector3",
    56: "Reflector4", 57: "Reflector5",
    58: "Capacitor1", 59: "Capacitor2", 60: "Capacitor3",
    61: "Capacitor4", 62: "Capacitor5",
    63: "Plate1", 64: "Plate2", 65: "Plate3", 66: "Plate4", 67: "Plate5",
    68: "Coolant1", 69: "Coolant2", 70: "Coolant3",
    71: "Coolant4", 72: "Coolant5", 73: "Coolant6",
    74: "Capacitor6",
}


def _ms_password_derive_bytes(password: bytes, salt: bytes,
                              iterations: int, key_len: int) -> bytes:
    """Replicate .NET PasswordDeriveBytes.GetBytes (SHA1).

    RE: Microsoft reference source — PasswordDeriveBytes.cs.
    ComputeBaseValue: SHA1(password + salt), then iterate (iterations-2) times.
    ComputeBytes: HashPrefix writes counter as ASCII digits (skipped when prefix=0),
    then hashes prefix + baseValue.
    """
    # ComputeBaseValue
    base_value = hashlib.sha1(password + salt).digest()
    for _ in range(1, iterations - 1):
        base_value = hashlib.sha1(base_value).digest()

    # ComputeBytes with HashPrefix
    result = bytearray()
    prefix = 0
    while len(result) < key_len:
        h = hashlib.sha1()
        if prefix > 0:
            # HashPrefix: write counter digits as ASCII bytes
            digits = str(prefix).encode("ascii")
            h.update(digits)
        prefix += 1
        h.update(base_value)
        result.extend(h.digest())

    return bytes(result[:key_len])


def _decrypt_original(ciphertext: bytes) -> str | None:
    """Decrypt an original Reactor Idle save (AES-256-CBC, PKCS7 padding)."""
    try:
        from Crypto.Cipher import AES
    except ImportError:
        try:
            from Cryptodome.Cipher import AES
        except ImportError:
            print("[save] pycryptodome not installed, cannot decrypt original saves")
            return None

    key = _ms_password_derive_bytes(
        _PASS_PHRASE, _SALT_VALUE, _PASSWORD_ITERATIONS, _KEY_SIZE // 8
    )
    try:
        cipher = AES.new(key, AES.MODE_CBC, _INIT_VECTOR)
        decrypted = cipher.decrypt(ciphertext)
    except ValueError as e:
        print(f"[save] AES decryption failed: {e}")
        return None

    # Validate and strip PKCS7 padding
    if not decrypted:
        return None
    pad = decrypted[-1]
    if pad < 1 or pad > 16:
        return None
    if not all(b == pad for b in decrypted[-pad:]):
        return None

    return decrypted[:-pad].decode("utf-8", errors="replace")


def _parse_original_save(text: str) -> dict | None:
    """Parse original game pipe-delimited save format into our dict format.

    Format: Key:Value|Key:Value|...|
    Components: x,y,z,typeIndex,heat,durability;...;
    Upgrades: level;level;...;
    """
    fields: dict[str, str] = {}
    for field in text.split("|"):
        if ":" in field:
            key, value = field.split(":", 1)
            fields[key] = value

    if not fields:
        return None

    # Map fields to our internal dict format
    store = {
        "money": float(fields.get("Money", "0")),
        "total_money": float(fields.get("TotalMoney", "0")),
        "money_earned_this_game": float(fields.get("MoneyThisGame", "0")),
        "power": float(fields.get("Power", "0")),
        "total_power_produced": float(fields.get("TotalPower", "0")),
        "power_produced_this_game": float(fields.get("PowerThisGame", "0")),
        "heat": float(fields.get("Heat", "0")),
        "total_heat_dissipated": float(fields.get("TotalHeat", "0")),
        "heat_dissipated_this_game": float(fields.get("HeatThisGame", "0")),
        "exotic_particles": float(fields.get("CurrentExoticParticles", "0")),
        "total_exotic_particles": float(fields.get("TotalExoticParticles", "0")),
    }

    # Parse upgrade levels
    upgrade_levels = []
    upgrades_str = fields.get("Upgrades", "")
    for part in upgrades_str.split(";"):
        part = part.strip()
        if part:
            upgrade_levels.append(int(part))

    # Parse components: x,y,z,typeIndex,heat,durability;
    components = []
    comps_str = fields.get("Components", "")
    for entry in comps_str.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split(",")
        if len(parts) < 4:
            continue
        x, y, z, type_idx = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
        heat = float(parts[4]) if len(parts) > 4 else 0.0
        durability = float(parts[5]) if len(parts) > 5 else 0.0
        name = _ORIG_INDEX_TO_NAME.get(type_idx)
        if name is None:
            print(f"[save] Warning: unknown original component index {type_idx}")
            continue
        components.append({
            "name": name,
            "x": x, "y": y, "z": z,
            "heat": heat, "durability": durability,
            "depleted": False,
        })

    paused = fields.get("Paused", "0") != "0"
    replace = fields.get("CellsReplace", "1") != "0"

    return {
        "version": 1,
        "store": store,
        "upgrade_levels": upgrade_levels,
        "reactor_heat": float(fields.get("Heat", "0")),
        "stored_power": float(fields.get("Power", "0")),
        "paused": paused,
        "replace_mode": replace,
        "total_ticks": 0,
        "prestige_level": 0,
        "shop_page": 0,
        "selected_component_index": -1,
        "components": components,
    }


def _build_save_dict(sim: Simulation) -> dict:
    """Build a JSON-serializable dict from simulation state."""
    components = []
    for comp in sim.components:
        components.append({
            "name": comp.stats.name,
            "heat": comp.heat,
            "durability": comp.durability,
            "depleted": comp.depleted,
            "x": comp.grid_x,
            "y": comp.grid_y,
            "z": comp.grid_z,
        })

    upgrade_levels = [u.level for u in sim.upgrade_manager.upgrades]

    return {
        "version": 1,
        "store": {
            "money": sim.store.money,
            "total_money": sim.store.total_money,
            "money_earned_this_game": sim.store.money_earned_this_game,
            "power": sim.store.power,
            "total_power_produced": sim.store.total_power_produced,
            "power_produced_this_game": sim.store.power_produced_this_game,
            "heat": sim.store.heat,
            "total_heat_dissipated": sim.store.total_heat_dissipated,
            "heat_dissipated_this_game": sim.store.heat_dissipated_this_game,
            "exotic_particles": sim.store.exotic_particles,
            "total_exotic_particles": sim.store.total_exotic_particles,
        },
        "upgrade_levels": upgrade_levels,
        "reactor_heat": sim.reactor_heat,
        "stored_power": sim.stored_power,
        "depleted_protium_count": sim.depleted_protium_count,
        "paused": sim.paused,
        "replace_mode": sim.replace_mode,
        "total_ticks": sim.total_ticks,
        "prestige_level": sim.prestige_level,
        "shop_page": sim.shop_page,
        "selected_component_index": sim.selected_component_index,
        "components": components,
    }


def _restore_from_dict(sim: Simulation, data: dict) -> bool:
    """Restore simulation state from a save dict. Returns True on success."""
    from game.simulation import ReactorComponent

    try:
        # 1. Restore ResourceStore fields
        store_data = data.get("store", {})
        sim.store.money = float(store_data.get("money", 0.0))
        sim.store.total_money = float(store_data.get("total_money", 0.0))
        sim.store.money_earned_this_game = float(store_data.get("money_earned_this_game", 0.0))
        sim.store.power = float(store_data.get("power", 0.0))
        sim.store.total_power_produced = float(store_data.get("total_power_produced", 0.0))
        sim.store.power_produced_this_game = float(store_data.get("power_produced_this_game", 0.0))
        sim.store.heat = float(store_data.get("heat", 0.0))
        sim.store.total_heat_dissipated = float(store_data.get("total_heat_dissipated", 0.0))
        sim.store.heat_dissipated_this_game = float(store_data.get("heat_dissipated_this_game", 0.0))
        sim.store.exotic_particles = float(store_data.get("exotic_particles", 0.0))
        sim.store.total_exotic_particles = float(store_data.get("total_exotic_particles", 0.0))

        # 2. Restore upgrade levels
        upgrade_levels = data.get("upgrade_levels", [])
        for i, level in enumerate(upgrade_levels):
            if i < len(sim.upgrade_manager.upgrades):
                sim.upgrade_manager.upgrades[i].level = int(level)

        # 2b. Resize grid for Subspace Expansion (upgrade 50) before placing components
        sim.resize_grid_for_subspace()

        # 3. Restore sim scalars
        sim.reactor_heat = float(data.get("reactor_heat", 0.0))
        sim.stored_power = float(data.get("stored_power", 0.0))
        sim.depleted_protium_count = int(data.get("depleted_protium_count", 0))
        sim.paused = bool(data.get("paused", False))
        sim.replace_mode = bool(data.get("replace_mode", True))
        sim.total_ticks = int(data.get("total_ticks", 0))
        sim.prestige_level = int(data.get("prestige_level", 0))
        sim.shop_page = int(data.get("shop_page", 0))
        sim.selected_component_index = int(data.get("selected_component_index", -1))

        # 4. Clear existing grid/components, reconstruct from saved components
        if sim.grid is not None:
            for x, y, z, comp in list(sim.grid.iter_cells()):
                if comp is not None:
                    sim.grid.set(x, y, z, None)
        sim.components.clear()

        # Build name -> stats lookup from shop catalog
        stats_by_name = {comp.name: comp for comp in sim.shop_components}

        for comp_data in data.get("components", []):
            name = comp_data.get("name", "")
            stats = stats_by_name.get(name)
            if stats is None:
                print(f"[save] Warning: unknown component '{name}', skipping")
                continue

            rc = ReactorComponent(
                stats=stats,
                heat=float(comp_data.get("heat", 0.0)),
                durability=float(comp_data.get("durability", 0.0)),
                depleted=bool(comp_data.get("depleted", False)),
                grid_x=int(comp_data.get("x", 0)),
                grid_y=int(comp_data.get("y", 0)),
                grid_z=int(comp_data.get("z", 0)),
            )

            if sim.grid is not None and sim.grid.in_bounds(rc.grid_x, rc.grid_y, rc.grid_z):
                sim.grid.set(rc.grid_x, rc.grid_y, rc.grid_z, rc)
                sim.components.append(rc)
            else:
                print(f"[save] Warning: component '{name}' at ({rc.grid_x},{rc.grid_y}) out of bounds, skipping")

        # 5. Mark pulses dirty and recompute capacities
        sim._pulses_dirty = True
        sim.recompute_max_capacities()

        # 6. Sync store with reactor state
        sim.store.power = sim.stored_power
        sim.store.heat = sim.reactor_heat

        return True

    except (KeyError, TypeError, ValueError) as e:
        print(f"[save] Error restoring save data: {e}")
        return False


_LOCALSTORAGE_KEY = "rev_reactor_save"


def save_game(sim: Simulation, path=None) -> None:
    """Auto-save to localStorage."""
    data = _build_save_dict(sim)
    json_str = json.dumps(data, separators=(",", ":"))
    try:
        from js import window  # type: ignore
        window.localStorage.setItem(_LOCALSTORAGE_KEY, json_str)
    except Exception as e:
        print(f"[save] Error saving to localStorage: {e}")


def load_game(sim: Simulation, path=None) -> bool:
    """Auto-load from localStorage. Returns False on missing/corrupt data."""
    try:
        from js import window  # type: ignore
        text = window.localStorage.getItem(_LOCALSTORAGE_KEY)
        if text is None:
            return False
        # Convert JsProxy string to Python string if needed
        text = str(text)
    except Exception as e:
        print(f"[save] Error reading localStorage: {e}")
        return False
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[save] Error parsing save data: {e}")
        return False
    return _restore_from_dict(sim, data)


def export_save(sim: Simulation, path=None) -> None:
    """Export: build save dict -> JSON -> base64 -> trigger browser download."""
    data = _build_save_dict(sim)
    json_str = json.dumps(data, separators=(",", ":"))
    encoded = base64.b64encode(json_str.encode("utf-8")).decode("ascii")
    try:
        from js import document, window, Blob, URL  # type: ignore
        blob = Blob.new([encoded], {"type": "text/plain"})
        url = URL.createObjectURL(blob)
        a = document.createElement("a")
        a.href = url
        a.download = "rev_reactor_save.txt"
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    except Exception as e:
        print(f"[save] Error exporting save: {e}")


def _try_import_data(encoded: str) -> dict | None:
    """Try to parse import data, handling both our format and original game format.

    Our format: base64 → JSON dict.
    Original format: base64 → AES-256-CBC ciphertext → pipe-delimited text.
    """
    try:
        raw = base64.b64decode(encoded)
    except Exception:
        return None

    # Try our format first: base64 → JSON
    try:
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict) and "version" in data:
            return data
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass

    # Try original game format: base64 → AES ciphertext → pipe-delimited
    if len(raw) % 16 == 0 and len(raw) >= 16:
        plaintext = _decrypt_original(raw)
        if plaintext and "|" in plaintext:
            data = _parse_original_save(plaintext)
            if data is not None:
                return data

    return None


_pending_import_sim: Simulation | None = None


def import_save_from_file(sim: Simulation) -> bool:
    """Trigger the browser file input element to import a save.

    The actual import happens via _handle_file_import called from the
    frame-based polling system when the file is read.
    """
    global _pending_import_sim
    _pending_import_sim = sim
    try:
        from js import document  # type: ignore
        file_input = document.getElementById("file-input")
        if file_input is not None:
            file_input.value = ""  # Reset so same file can be re-selected
            file_input.click()
    except Exception as e:
        print(f"[save] File input error: {e}")
    return False


def _handle_file_import(encoded: str) -> bool:
    """Called from JS when the file input has been read."""
    sim = _pending_import_sim
    if sim is None:
        return False

    encoded = str(encoded).strip()
    data = _try_import_data(encoded)
    if data is None:
        print("[save] Could not parse import file (not a valid save)")
        return False

    return _restore_from_dict(sim, data)
