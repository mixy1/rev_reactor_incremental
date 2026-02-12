use crate::model::{ComponentKind, GridCoord, PlacedComponent, ReactorGrid};

use super::resource_store::ResourceStore;

#[derive(Debug, Clone, PartialEq)]
pub struct Simulation {
    pub resources: ResourceStore,
    pub grid: ReactorGrid,
    pub components: Vec<PlacedComponent>,
    pub paused: bool,
    pub tick_index: u64,
    pub base_power_generation_per_tick: f64,
    pub base_heat_generation_per_tick: f64,
    pub auto_sell_rate_per_tick: f64,
    pub passive_heat_dissipation_per_tick: f64,
}

impl Default for Simulation {
    fn default() -> Self {
        Self::new(19, 16, 1)
    }
}

impl Simulation {
    pub fn new(width: usize, height: usize, layers: usize) -> Self {
        Self {
            resources: ResourceStore::default(),
            grid: ReactorGrid::new(width, height, layers),
            components: Vec::new(),
            paused: false,
            tick_index: 0,
            base_power_generation_per_tick: 0.0,
            base_heat_generation_per_tick: 0.0,
            auto_sell_rate_per_tick: 0.0,
            passive_heat_dissipation_per_tick: 0.0,
        }
    }

    pub fn place_component(
        &mut self,
        coord: GridCoord,
        kind: ComponentKind,
    ) -> Result<(), crate::model::GridError> {
        self.grid.set(coord, Some(kind))?;
        self.components.retain(|entry| entry.coord != coord);
        self.components.push(PlacedComponent::new(kind, coord));
        Ok(())
    }

    pub fn remove_component(&mut self, coord: GridCoord) -> Result<(), crate::model::GridError> {
        self.grid.clear(coord)?;
        self.components.retain(|entry| entry.coord != coord);
        Ok(())
    }

    pub fn tick(&mut self) {
        self.resources.begin_tick();
        if self.paused {
            return;
        }

        self.tick_index += 1;

        // Tick skeleton, intentionally separated into discrete phases so
        // subsequent parity work can map each phase to decompiled behavior.
        self.prepare_multipliers();
        self.distribute_pulses();
        self.drain_durability();
        self.generate_power_and_heat();
        self.exchange_heat();
        self.exchange_with_hull();
        self.passive_sell_power();
        self.passive_dissipate_heat();
    }

    fn prepare_multipliers(&mut self) {}

    fn distribute_pulses(&mut self) {}

    fn drain_durability(&mut self) {}

    fn generate_power_and_heat(&mut self) {
        self.resources.add_power(self.base_power_generation_per_tick);
        self.resources.add_heat(self.base_heat_generation_per_tick);
    }

    fn exchange_heat(&mut self) {}

    fn exchange_with_hull(&mut self) {}

    fn passive_sell_power(&mut self) {
        let sold = self
            .resources
            .drain_power(self.auto_sell_rate_per_tick.max(0.0));
        if sold > 0.0 {
            self.resources.add_money(sold);
        }
    }

    fn passive_dissipate_heat(&mut self) {
        self.resources
            .dissipate_heat(self.passive_heat_dissipation_per_tick.max(0.0));
    }
}

#[cfg(test)]
mod tests {
    use super::Simulation;

    const EPSILON: f64 = 1e-9;

    fn assert_close(actual: f64, expected: f64) {
        assert!(
            (actual - expected).abs() <= EPSILON,
            "expected {expected}, got {actual}"
        );
    }

    fn assert_same_state(lhs: &Simulation, rhs: &Simulation) {
        assert_eq!(lhs.tick_index, rhs.tick_index);
        assert_close(lhs.resources.money, rhs.resources.money);
        assert_close(lhs.resources.power, rhs.resources.power);
        assert_close(lhs.resources.heat, rhs.resources.heat);
        assert_close(lhs.resources.total_money, rhs.resources.total_money);
        assert_close(
            lhs.resources.total_power_produced,
            rhs.resources.total_power_produced,
        );
        assert_close(
            lhs.resources.total_heat_dissipated,
            rhs.resources.total_heat_dissipated,
        );
        assert_close(lhs.resources.tick_deltas.money, rhs.resources.tick_deltas.money);
        assert_close(lhs.resources.tick_deltas.power, rhs.resources.tick_deltas.power);
        assert_close(lhs.resources.tick_deltas.heat, rhs.resources.tick_deltas.heat);
    }

    #[test]
    fn tick_applies_generation_sell_and_heat_dissipation_in_order() {
        let mut sim = Simulation::default();
        sim.base_power_generation_per_tick = 2.0;
        sim.base_heat_generation_per_tick = 1.5;
        sim.auto_sell_rate_per_tick = 1.0;
        sim.passive_heat_dissipation_per_tick = 0.25;

        sim.tick();

        assert_eq!(sim.tick_index, 1);
        assert_close(sim.resources.money, 1.0);
        assert_close(sim.resources.power, 1.0);
        assert_close(sim.resources.heat, 1.25);
        assert_close(sim.resources.total_money, 1.0);
        assert_close(sim.resources.total_power_produced, 2.0);
        assert_close(sim.resources.total_heat_dissipated, 0.25);
        assert_close(sim.resources.tick_deltas.money, 1.0);
        assert_close(sim.resources.tick_deltas.power, 1.0);
        assert_close(sim.resources.tick_deltas.heat, 1.25);
    }

    #[test]
    fn repeated_ticks_are_deterministic() {
        let mut a = Simulation::default();
        a.resources.power = 9.0;
        a.resources.heat = 4.0;
        a.base_power_generation_per_tick = 1.25;
        a.base_heat_generation_per_tick = 0.75;
        a.auto_sell_rate_per_tick = 1.5;
        a.passive_heat_dissipation_per_tick = 0.5;

        let mut b = a.clone();

        for _ in 0..64 {
            a.tick();
            b.tick();
            assert_same_state(&a, &b);
        }
    }
}
