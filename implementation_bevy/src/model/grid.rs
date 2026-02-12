use super::component::ComponentKind;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub struct GridCoord {
    pub x: usize,
    pub y: usize,
    pub z: usize,
}

impl GridCoord {
    pub fn new(x: usize, y: usize, z: usize) -> Self {
        Self { x, y, z }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GridCell {
    pub kind: ComponentKind,
    pub component_id: u64,
    pub placed_tick: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GridError {
    OutOfBounds(GridCoord),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReactorGrid {
    pub width: usize,
    pub height: usize,
    pub layers: usize,
    cells: Vec<Option<GridCell>>,
}

impl ReactorGrid {
    pub fn new(width: usize, height: usize, layers: usize) -> Self {
        let width = width.max(1);
        let height = height.max(1);
        let layers = layers.max(1);
        Self {
            width,
            height,
            layers,
            cells: vec![None; width * height * layers],
        }
    }

    pub fn in_bounds(&self, coord: GridCoord) -> bool {
        coord.x < self.width && coord.y < self.height && coord.z < self.layers
    }

    pub fn get(&self, coord: GridCoord) -> Option<ComponentKind> {
        self.get_cell(coord).map(|cell| cell.kind)
    }

    pub fn get_cell(&self, coord: GridCoord) -> Option<GridCell> {
        let index = self.index(coord)?;
        self.cells[index]
    }

    pub fn set(&mut self, coord: GridCoord, kind: Option<ComponentKind>) -> Result<(), GridError> {
        match kind {
            Some(kind) => self.place(
                coord,
                GridCell {
                    kind,
                    component_id: 0,
                    placed_tick: 0,
                },
            ),
            None => self.clear(coord),
        }
    }

    pub fn place(&mut self, coord: GridCoord, cell: GridCell) -> Result<(), GridError> {
        let index = self.index(coord).ok_or(GridError::OutOfBounds(coord))?;
        self.cells[index] = Some(cell);
        Ok(())
    }

    pub fn clear(&mut self, coord: GridCoord) -> Result<(), GridError> {
        let index = self.index(coord).ok_or(GridError::OutOfBounds(coord))?;
        self.cells[index] = None;
        Ok(())
    }

    fn index(&self, coord: GridCoord) -> Option<usize> {
        if !self.in_bounds(coord) {
            return None;
        }
        Some((coord.z * self.height + coord.y) * self.width + coord.x)
    }
}
