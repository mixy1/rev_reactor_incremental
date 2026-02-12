use std::collections::BTreeMap;

use crate::model::{ComponentKind, GridCell, GridCoord, PlacedComponent, ReactorGrid};

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
    pub base_power_capacity: f64,
    pub base_heat_capacity: f64,
    pub max_power_capacity: f64,
    pub max_heat_capacity: f64,
    next_component_id: u64,
}

impl Default for Simulation {
    fn default() -> Self {
        Self::new(19, 16, 1)
    }
}

impl Simulation {
    pub fn new(width: usize, height: usize, layers: usize) -> Self {
        let base_power_capacity = 100.0;
        let base_heat_capacity = 1_000.0;
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
            base_power_capacity,
            base_heat_capacity,
            max_power_capacity: base_power_capacity,
            max_heat_capacity: base_heat_capacity,
            next_component_id: 1,
        }
    }

    pub fn place_component(
        &mut self,
        coord: GridCoord,
        kind: ComponentKind,
    ) -> Result<(), crate::model::GridError> {
        if !self.grid.in_bounds(coord) {
            return Err(crate::model::GridError::OutOfBounds(coord));
        }
        self.components.retain(|entry| entry.coord != coord);
        let id = self.next_component_id;
        self.next_component_id = self.next_component_id.saturating_add(1);
        self.grid.place(
            coord,
            GridCell {
                kind,
                component_id: id,
                placed_tick: self.tick_index,
            },
        )?;
        self.components.push(PlacedComponent::new_with_metadata(
            kind,
            coord,
            id,
            self.tick_index,
        ));
        self.prepare_multipliers();
        Ok(())
    }

    pub fn remove_component(&mut self, coord: GridCoord) -> Result<(), crate::model::GridError> {
        self.grid.clear(coord)?;
        self.components.retain(|entry| entry.coord != coord);
        self.prepare_multipliers();
        Ok(())
    }

    pub fn component_at(&self, coord: GridCoord) -> Option<&PlacedComponent> {
        self.components
            .iter()
            .find(|component| component.coord == coord)
    }

    pub fn tick(&mut self) {
        self.resources.begin_tick();
        if self.paused {
            return;
        }

        self.tick_index = self.tick_index.saturating_add(1);

        // Phase order is fixed for deterministic behavior.
        self.prepare_multipliers();
        self.distribute_pulses();
        self.drain_durability();
        self.generate_power_and_heat();
        self.apply_coolant_effects();
        self.exchange_with_hull();
        self.passive_sell_power();
        self.passive_dissipate_heat();
        self.clamp_stores_to_capacity();
    }

    fn prepare_multipliers(&mut self) {
        let mut power_cap = self.base_power_capacity.max(0.0);
        let mut heat_cap = self.base_heat_capacity.max(0.0);
        for component in &self.components {
            if component.depleted {
                continue;
            }
            let stats = component.stats();
            power_cap += stats.reactor_power_capacity_increase;
            heat_cap += stats.reactor_heat_capacity_increase;
        }
        self.max_power_capacity = power_cap.max(0.0);
        self.max_heat_capacity = heat_cap.max(0.0);
        self.clamp_stores_to_capacity();
    }

    fn distribute_pulses(&mut self) {
        for component in &mut self.components {
            component.pulse_count = 0;
        }
        let coord_to_index = self.component_index_map();
        let snapshot = self.components.clone();
        for source in &snapshot {
            if source.depleted {
                continue;
            }
            let source_stats = source.stats();
            if source_stats.energy_per_pulse <= 0.0 {
                continue;
            }
            let pulses = source_stats.pulses_produced.max(1);
            if let Some(index) = coord_to_index.get(&source.coord) {
                self.components[*index].pulse_count =
                    self.components[*index].pulse_count.saturating_add(pulses);
            }
            for neighbor in self.cardinal_neighbors(source.coord) {
                if let Some(index) = coord_to_index.get(&neighbor) {
                    self.components[*index].pulse_count =
                        self.components[*index].pulse_count.saturating_add(pulses);
                }
            }
        }
    }

    fn drain_durability(&mut self) {
        let coord_to_index = self.component_index_map();
        let snapshot = self.components.clone();
        let width = self.grid.width;
        let height = self.grid.height;
        for (index, component) in self.components.iter_mut().enumerate() {
            if snapshot[index].depleted {
                continue;
            }
            let stats = snapshot[index].stats();
            if stats.max_durability <= 0.0 {
                continue;
            }

            let mut durability_drain = 0.0;
            if stats.energy_per_pulse > 0.0 {
                durability_drain = 1.0;
            } else if stats.reflector_bonus_pct > 0.0 {
                for neighbor in Self::cardinal_neighbors_for(snapshot[index].coord, width, height) {
                    if let Some(neighbor_index) = coord_to_index.get(&neighbor) {
                        let neighbor_component = &snapshot[*neighbor_index];
                        if neighbor_component.depleted || !neighbor_component.is_fuel() {
                            continue;
                        }
                        durability_drain += f64::from(neighbor_component.pulse_count);
                    }
                }
            }

            if durability_drain > 0.0 {
                component.durability = (component.durability - durability_drain).max(0.0);
                if component.durability <= 0.0 {
                    component.depleted = true;
                    component.pulse_count = 0;
                    component.last_power = 0.0;
                    component.last_heat = 0.0;
                }
            }
        }
    }

    fn generate_power_and_heat(&mut self) {
        let coord_to_index = self.component_index_map();
        let snapshot = self.components.clone();
        let mut pending_component_heat = vec![0.0; self.components.len()];
        let mut total_power = self.base_power_generation_per_tick;
        let mut hull_heat = self.base_heat_generation_per_tick;

        for (index, source) in snapshot.iter().enumerate() {
            if source.depleted {
                continue;
            }
            let source_stats = source.stats();
            if source_stats.energy_per_pulse <= 0.0 {
                continue;
            }

            let pulse_count = f64::from(source.pulse_count);
            if pulse_count <= 0.0 {
                self.components[index].last_power = 0.0;
                self.components[index].last_heat = 0.0;
                continue;
            }

            let mut reflector_multiplier = 1.0;
            let mut absorbers: Vec<usize> = Vec::new();
            for neighbor in self.cardinal_neighbors(source.coord) {
                if let Some(neighbor_index) = coord_to_index.get(&neighbor) {
                    let neighbor_component = &snapshot[*neighbor_index];
                    if neighbor_component.depleted {
                        continue;
                    }
                    let neighbor_stats = neighbor_component.stats();
                    if neighbor_stats.reflector_bonus_pct > 0.0 {
                        reflector_multiplier += neighbor_stats.reflector_bonus_pct;
                    }
                    if neighbor_stats.heat_capacity > 0.0 {
                        absorbers.push(*neighbor_index);
                    }
                }
            }

            let power = pulse_count * source_stats.energy_per_pulse * reflector_multiplier;
            let heat = pulse_count * pulse_count * source_stats.heat_per_pulse;
            self.components[index].last_power = power;
            self.components[index].last_heat = heat;
            total_power += power;

            if absorbers.is_empty() {
                hull_heat += heat;
            } else {
                let per_absorber = heat / absorbers.len() as f64;
                for absorber in absorbers {
                    pending_component_heat[absorber] += per_absorber;
                }
            }
        }

        for (index, added_heat) in pending_component_heat.into_iter().enumerate() {
            if added_heat <= 0.0 || self.components[index].depleted {
                continue;
            }
            hull_heat += self.add_heat_to_component(index, added_heat);
        }

        if total_power != 0.0 {
            self.resources.add_power(total_power);
        }
        if hull_heat != 0.0 {
            self.resources.add_heat(hull_heat);
        }
    }

    fn apply_coolant_effects(&mut self) {
        let coord_to_index = self.component_index_map();
        let snapshot = self.components.clone();
        let mut heat_delta = vec![0.0; self.components.len()];

        for source in &snapshot {
            if source.depleted {
                continue;
            }
            let source_stats = source.stats();
            if source_stats.coolant_absorb_rate <= 0.0 || source_stats.heat_capacity <= 0.0 {
                continue;
            }

            let source_index = match coord_to_index.get(&source.coord) {
                Some(index) => *index,
                None => continue,
            };

            for neighbor in self.cardinal_neighbors(source.coord) {
                let Some(neighbor_index) = coord_to_index.get(&neighbor).copied() else {
                    continue;
                };
                if snapshot[neighbor_index].depleted {
                    continue;
                }
                let neighbor_heat = snapshot[neighbor_index].heat;
                let source_heat = snapshot[source_index].heat;
                if neighbor_heat <= source_heat || neighbor_heat <= 0.0 {
                    continue;
                }
                let gradient = neighbor_heat - source_heat;
                let transfer = (gradient * 0.25)
                    .min(source_stats.coolant_absorb_rate)
                    .min(neighbor_heat);
                if transfer <= 0.0 {
                    continue;
                }
                heat_delta[source_index] += transfer;
                heat_delta[neighbor_index] -= transfer;
            }
        }

        let mut overflow_to_hull = 0.0;
        for (index, delta) in heat_delta.into_iter().enumerate() {
            if delta < 0.0 {
                let removed = (-delta).min(self.components[index].heat);
                self.components[index].heat -= removed;
            } else if delta > 0.0 {
                overflow_to_hull += self.add_heat_to_component(index, delta);
            }
        }
        if overflow_to_hull > 0.0 {
            self.resources.add_heat(overflow_to_hull);
        }
    }

    fn exchange_with_hull(&mut self) {
        let coord_to_index = self.component_index_map();
        let snapshot = self.components.clone();

        // Vent family: pull heat from hull into vent buffers.
        for source in &snapshot {
            if source.depleted {
                continue;
            }
            let stats = source.stats();
            if !matches!(source.kind, ComponentKind::Vent { .. }) || stats.reactor_vent_rate <= 0.0
            {
                continue;
            }
            let Some(index) = coord_to_index.get(&source.coord).copied() else {
                continue;
            };
            let transfer = self.resources.heat.min(stats.reactor_vent_rate);
            if transfer <= 0.0 {
                continue;
            }
            self.resources.add_heat(-transfer);
            let overflow = self.add_heat_to_component(index, transfer);
            if overflow > 0.0 {
                self.resources.add_heat(overflow);
            }
        }

        // Inlet family: pull adjacent component heat into reactor hull.
        for source in &snapshot {
            if source.depleted || !matches!(source.kind, ComponentKind::Inlet { .. }) {
                continue;
            }
            let rate = source.stats().reactor_vent_rate;
            if rate <= 0.0 {
                continue;
            }
            for neighbor in self.cardinal_neighbors(source.coord) {
                let Some(index) = coord_to_index.get(&neighbor).copied() else {
                    continue;
                };
                if self.components[index].depleted || self.components[index].heat <= 0.0 {
                    continue;
                }
                let pulled = self.components[index].heat.min(rate);
                if pulled <= 0.0 {
                    continue;
                }
                self.components[index].heat -= pulled;
                self.resources.add_heat(pulled);
            }
        }

        // Outlet family: push hull heat into neighboring heat buffers.
        for source in &snapshot {
            if source.depleted || !matches!(source.kind, ComponentKind::Outlet { .. }) {
                continue;
            }
            let rate = source.stats().reactor_vent_rate;
            if rate <= 0.0 || self.resources.heat <= 0.0 {
                continue;
            }
            let mut absorbers: Vec<usize> = Vec::new();
            for neighbor in self.cardinal_neighbors(source.coord) {
                let Some(index) = coord_to_index.get(&neighbor).copied() else {
                    continue;
                };
                if self.components[index].depleted {
                    continue;
                }
                if self.components[index].stats().heat_capacity > 0.0 {
                    absorbers.push(index);
                }
            }
            if absorbers.is_empty() {
                continue;
            }
            let total_transfer = self.resources.heat.min(rate * absorbers.len() as f64);
            if total_transfer <= 0.0 {
                continue;
            }
            self.resources.add_heat(-total_transfer);
            let per_absorber = total_transfer / absorbers.len() as f64;
            for absorber in absorbers {
                let overflow = self.add_heat_to_component(absorber, per_absorber);
                if overflow > 0.0 {
                    self.resources.add_heat(overflow);
                }
            }
        }

        // Self venting: components vent their own heat to environment.
        let mut total_component_vented = 0.0;
        for component in &mut self.components {
            if component.depleted {
                continue;
            }
            let self_vent_rate = component.stats().self_vent_rate;
            if self_vent_rate <= 0.0 || component.heat <= 0.0 {
                continue;
            }
            let vented = component.heat.min(self_vent_rate);
            component.heat -= vented;
            total_component_vented += vented;
        }
        if total_component_vented > 0.0 {
            self.resources.total_heat_dissipated += total_component_vented;
            self.resources.heat_dissipated_this_game += total_component_vented;
        }
    }

    fn passive_sell_power(&mut self) {
        let sold = self
            .resources
            .drain_power(self.auto_sell_rate_per_tick.max(0.0));
        if sold > 0.0 {
            self.resources.add_money(sold);
        }
    }

    fn passive_dissipate_heat(&mut self) {
        let mut vent_rate = self.passive_heat_dissipation_per_tick.max(0.0);
        if self.resources.heat > self.max_heat_capacity {
            vent_rate += (self.resources.heat - self.max_heat_capacity) * 0.05;
        }
        self.resources.dissipate_heat(vent_rate);
    }

    fn clamp_stores_to_capacity(&mut self) {
        if self.resources.power > self.max_power_capacity {
            let overflow = self.resources.power - self.max_power_capacity;
            self.resources.drain_power(overflow);
        }
        self.resources.heat = self.resources.heat.max(0.0);
    }

    fn add_heat_to_component(&mut self, component_index: usize, amount: f64) -> f64 {
        if amount <= 0.0 {
            return 0.0;
        }
        let capacity = self.components[component_index].stats().heat_capacity;
        if capacity <= 0.0 {
            return amount;
        }
        let target = self.components[component_index].heat + amount;
        if target <= capacity {
            self.components[component_index].heat = target;
            return 0.0;
        }
        self.components[component_index].heat = capacity;
        target - capacity
    }

    fn component_index_map(&self) -> BTreeMap<GridCoord, usize> {
        self.components
            .iter()
            .enumerate()
            .map(|(index, component)| (component.coord, index))
            .collect()
    }

    fn cardinal_neighbors(&self, coord: GridCoord) -> Vec<GridCoord> {
        Self::cardinal_neighbors_for(coord, self.grid.width, self.grid.height)
    }

    fn cardinal_neighbors_for(coord: GridCoord, width: usize, height: usize) -> Vec<GridCoord> {
        let mut neighbors = Vec::with_capacity(4);
        if coord.x > 0 {
            neighbors.push(GridCoord::new(coord.x - 1, coord.y, coord.z));
        }
        if coord.x + 1 < width {
            neighbors.push(GridCoord::new(coord.x + 1, coord.y, coord.z));
        }
        if coord.y > 0 {
            neighbors.push(GridCoord::new(coord.x, coord.y - 1, coord.z));
        }
        if coord.y + 1 < height {
            neighbors.push(GridCoord::new(coord.x, coord.y + 1, coord.z));
        }
        neighbors
    }
}
