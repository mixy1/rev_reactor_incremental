# Prestige System — Reverse Engineering Notes

## Prestige Button State Machine (fn 10493, 10490, 10481, 10489)

The binary's prestige button uses a **3-phase state machine** controlled by two booleans on the Controller class:

| Offset | Field | Type |
|--------|-------|------|
| +0xA2 | `isConfirmingPrestige` | bool |
| +0xA4 | `canResetPrestigeUpgrade` | bool |

### Phase A — Normal (`isConfirmingPrestige=0, canResetPrestigeUpgrade=0`)
- Label: `"Prestige for X exotic particles."`
- Click sets `isConfirmingPrestige=1` → transitions to Phase B
- Button disabled (greyed out) if calculated EP gain is 0

### Phase B — Confirm (`isConfirmingPrestige=1`)
- Label: `"Click again to confirm (Will restart game)"`
- Click executes prestige (fn 10481), then:
  - Sets `canResetPrestigeUpgrade=1`
  - Clears `isConfirmingPrestige`
  - Sets replace mode (`Controller+0xA1 = true`)
  - Transitions to Phase C

### Phase C — Refund Window (`isConfirmingPrestige=0, canResetPrestigeUpgrade=1`)
- Label: `"Refund prestige upgrades?"`
- Click resets all prestige upgrade levels to 0, restores current EP to lifetime total
  - Binary: `CurrentExoticParticles(+0x10) = TotalExoticParticles(+0x48)`
  - Clears `canResetPrestigeUpgrade` → transitions back to Phase A
- **One-shot window**: navigating away from the options page clears `canResetPrestigeUpgrade`

### Navigation Clearing (fn 10489)
When the player navigates away from the options view, the binary clears ALL confirmation state:
- `isConfirmingPrestige = false`
- `canResetPrestigeUpgrade = false`
- Reset confirm timer is also cleared

## Prestige EP Calculation (fn 10380)

Formula: `floor(4^(log10(min(totalPower, totalHeat)) - 12))`

- Requires `min(totalPower, totalHeat) >= 1e12` to earn any EP
- Returns delta: `total_calculated - total_exotic_particles` (already-earned EP subtracted)

## Prestige Execution (fn 10481)

When prestige executes:
1. Awards EP delta to `exotic_particles` and updates `total_exotic_particles` highwater mark
2. Clears grid (all components removed)
3. Zeroes per-game resources: money, power, heat, per-game stats
4. Lifetime totals persist: `total_power_produced`, `total_heat_dissipated`, `total_money`
5. Resets all **non-prestige** upgrades to level 0
6. Sets `replace_mode = true`
7. Does NOT navigate away — stays on options page for refund window

## Hard Reset (fn 10330)

Hard reset clears everything including:
- All upgrades (both normal AND prestige)
- All lifetime stats (total_power_produced, total_heat_dissipated, total_money)
- Exotic particles (both current and total)
- All prestige confirmation state
