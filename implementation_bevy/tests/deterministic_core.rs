use implementation_bevy::{ComponentKind, FuelKind, GridCoord, Simulation};

const EPSILON: f64 = 1e-9;

fn assert_close(actual: f64, expected: f64) {
    assert!(
        (actual - expected).abs() <= EPSILON,
        "expected {expected}, got {actual}"
    );
}

#[test]
fn repeated_ticks_are_deterministic() {
    let mut a = Simulation::new(5, 5, 1);
    a.auto_sell_rate_per_tick = 1.25;
    a.passive_heat_dissipation_per_tick = 0.2;
    a.place_component(
        GridCoord::new(2, 2, 0),
        ComponentKind::Fuel(FuelKind::Uranium),
    )
    .expect("place fuel");
    a.place_component(
        GridCoord::new(2, 1, 0),
        ComponentKind::Reflector { tier: 1 },
    )
    .expect("place reflector");
    a.place_component(GridCoord::new(1, 2, 0), ComponentKind::Vent { tier: 1 })
        .expect("place vent");
    a.resources.power = 8.0;
    a.resources.heat = 4.0;

    let mut b = a.clone();
    for _ in 0..64 {
        a.tick();
        b.tick();
        assert_eq!(a, b);
    }
}

#[test]
fn placement_replacement_and_removal_update_state() {
    let mut sim = Simulation::new(3, 3, 1);
    let coord = GridCoord::new(1, 1, 0);

    sim.place_component(coord, ComponentKind::Fuel(FuelKind::Uranium))
        .expect("initial place");
    let first = sim.component_at(coord).expect("component after place");
    let first_id = first.id;
    assert_eq!(first.placed_at_tick, 0);
    let first_cell = sim.grid.get_cell(coord).expect("grid cell after place");
    assert_eq!(first_cell.component_id, first_id);
    assert_eq!(first_cell.placed_tick, 0);

    sim.place_component(coord, ComponentKind::Vent { tier: 2 })
        .expect("replace at same coord");
    assert_eq!(sim.components.len(), 1);
    let second = sim.component_at(coord).expect("component after replace");
    assert_ne!(second.id, first_id);
    assert!(matches!(second.kind, ComponentKind::Vent { tier: 2 }));
    let second_cell = sim.grid.get_cell(coord).expect("grid cell after replace");
    assert_eq!(second_cell.component_id, second.id);

    sim.tick();
    sim.remove_component(coord).expect("remove");
    assert!(sim.component_at(coord).is_none());
    assert!(sim.grid.get(coord).is_none());
    assert!(sim.grid.get_cell(coord).is_none());
}

#[test]
fn fuel_cell_generates_power_heat_and_loses_durability() {
    let mut sim = Simulation::new(3, 3, 1);
    let fuel_coord = GridCoord::new(1, 1, 0);
    sim.place_component(fuel_coord, ComponentKind::Fuel(FuelKind::Uranium))
        .expect("place fuel");

    sim.tick();

    let fuel = sim.component_at(fuel_coord).expect("fuel component");
    assert_eq!(fuel.pulse_count, 1);
    assert_close(fuel.durability, 119.0);
    assert_close(fuel.last_power, 1.0);
    assert_close(fuel.last_heat, 1.0);
    assert_close(sim.resources.power, 1.0);
    assert_close(sim.resources.heat, 1.0);
}

#[test]
fn reflector_neighbor_increases_fuel_power_output() {
    let fuel_coord = GridCoord::new(1, 1, 0);
    let reflector_coord = GridCoord::new(1, 0, 0);

    let mut without_reflector = Simulation::new(3, 3, 1);
    without_reflector
        .place_component(fuel_coord, ComponentKind::Fuel(FuelKind::Uranium))
        .expect("place fuel without reflector");
    without_reflector.tick();

    let mut with_reflector = Simulation::new(3, 3, 1);
    with_reflector
        .place_component(fuel_coord, ComponentKind::Fuel(FuelKind::Uranium))
        .expect("place fuel with reflector");
    with_reflector
        .place_component(reflector_coord, ComponentKind::Reflector { tier: 1 })
        .expect("place reflector");
    with_reflector.tick();

    assert!(with_reflector.resources.power > without_reflector.resources.power);
    assert_close(with_reflector.resources.power, 1.1);
    assert_close(without_reflector.resources.power, 1.0);
    let reflector = with_reflector
        .component_at(reflector_coord)
        .expect("reflector exists");
    assert_close(reflector.durability, 99.0);
}

#[test]
fn vent_and_auto_sell_paths_apply_each_tick() {
    let mut sim = Simulation::new(3, 3, 1);
    sim.place_component(GridCoord::new(1, 1, 0), ComponentKind::Vent { tier: 2 })
        .expect("place vent");
    sim.resources.heat = 10.0;
    sim.resources.power = 5.0;
    sim.auto_sell_rate_per_tick = 2.0;

    sim.tick();

    assert_close(sim.resources.money, 2.0);
    assert_close(sim.resources.power, 3.0);
    assert_close(sim.resources.heat, 8.8);
    assert!(sim.resources.total_heat_dissipated >= 1.2);
}

#[test]
fn coolant_absorbs_neighbor_heat_before_venting() {
    let coolant_coord = GridCoord::new(1, 1, 0);
    let vent_coord = GridCoord::new(1, 2, 0);
    let mut sim = Simulation::new(4, 4, 1);
    sim.place_component(coolant_coord, ComponentKind::Coolant { tier: 1 })
        .expect("place coolant");
    sim.place_component(vent_coord, ComponentKind::Vent { tier: 1 })
        .expect("place vent");

    let vent_index = sim
        .components
        .iter()
        .position(|component| component.coord == vent_coord)
        .expect("vent index");
    sim.components[vent_index].heat = 8.0;

    sim.tick();

    let coolant = sim.component_at(coolant_coord).expect("coolant exists");
    let vent = sim.component_at(vent_coord).expect("vent exists");
    assert!(coolant.heat > 0.0);
    assert!(vent.heat < 6.8);
}
