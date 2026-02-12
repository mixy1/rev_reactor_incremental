#[derive(Debug, Clone, Copy, Default, PartialEq)]
pub struct TickDeltas {
    pub money: f64,
    pub power: f64,
    pub heat: f64,
    pub exotic_particles: f64,
}

impl TickDeltas {
    pub fn reset(&mut self) {
        *self = Self::default();
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct ResourceStore {
    pub money: f64,
    pub total_money: f64,
    pub money_earned_this_game: f64,
    pub power: f64,
    pub total_power_produced: f64,
    pub power_produced_this_game: f64,
    pub heat: f64,
    pub total_heat_dissipated: f64,
    pub heat_dissipated_this_game: f64,
    pub exotic_particles: f64,
    pub total_exotic_particles: f64,
    pub tick_deltas: TickDeltas,
}

impl Default for ResourceStore {
    fn default() -> Self {
        Self {
            money: 0.0,
            total_money: 0.0,
            money_earned_this_game: 0.0,
            power: 0.0,
            total_power_produced: 0.0,
            power_produced_this_game: 0.0,
            heat: 0.0,
            total_heat_dissipated: 0.0,
            heat_dissipated_this_game: 0.0,
            exotic_particles: 0.0,
            total_exotic_particles: 0.0,
            tick_deltas: TickDeltas::default(),
        }
    }
}

impl ResourceStore {
    pub fn begin_tick(&mut self) {
        self.tick_deltas.reset();
    }

    pub fn add_money(&mut self, amount: f64) {
        if amount <= 0.0 {
            return;
        }
        self.money += amount;
        self.total_money += amount;
        self.money_earned_this_game += amount;
        self.tick_deltas.money += amount;
    }

    pub fn add_power(&mut self, amount: f64) {
        if amount == 0.0 {
            return;
        }
        let previous = self.power;
        self.power = (self.power + amount).max(0.0);
        let applied = self.power - previous;
        if applied == 0.0 {
            return;
        }
        self.tick_deltas.power += applied;
        if applied > 0.0 {
            self.total_power_produced += applied;
            self.power_produced_this_game += applied;
        }
    }

    pub fn add_heat(&mut self, amount: f64) {
        if amount == 0.0 {
            return;
        }
        let previous = self.heat;
        self.heat = (self.heat + amount).max(0.0);
        let applied = self.heat - previous;
        if applied == 0.0 {
            return;
        }
        self.tick_deltas.heat += applied;
        if applied < 0.0 {
            let dissipated = -applied;
            self.total_heat_dissipated += dissipated;
            self.heat_dissipated_this_game += dissipated;
        }
    }

    pub fn add_exotic_particles(&mut self, amount: f64) {
        if amount <= 0.0 {
            return;
        }
        self.exotic_particles += amount;
        self.total_exotic_particles += amount;
        self.tick_deltas.exotic_particles += amount;
    }

    pub fn drain_power(&mut self, amount: f64) -> f64 {
        if amount <= 0.0 {
            return 0.0;
        }
        let drained = self.power.min(amount);
        if drained > 0.0 {
            self.power -= drained;
            self.tick_deltas.power -= drained;
        }
        drained
    }

    pub fn dissipate_heat(&mut self, amount: f64) -> f64 {
        if amount <= 0.0 {
            return 0.0;
        }
        let dissipated = self.heat.min(amount);
        if dissipated > 0.0 {
            self.heat -= dissipated;
            self.tick_deltas.heat -= dissipated;
            self.total_heat_dissipated += dissipated;
            self.heat_dissipated_this_game += dissipated;
        }
        dissipated
    }
}
