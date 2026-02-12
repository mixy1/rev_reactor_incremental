use super::component::ComponentKind;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
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
pub enum GridError {
    OutOfBounds(GridCoord),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReactorGrid {
    pub width: usize,
    pub height: usize,
    pub layers: usize,
    cells: Vec<Option<ComponentKind>>,
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
        let index = self.index(coord)?;
        self.cells[index]
    }

    pub fn set(&mut self, coord: GridCoord, kind: Option<ComponentKind>) -> Result<(), GridError> {
        let index = self.index(coord).ok_or(GridError::OutOfBounds(coord))?;
        self.cells[index] = kind;
        Ok(())
    }

    pub fn clear(&mut self, coord: GridCoord) -> Result<(), GridError> {
        self.set(coord, None)
    }

    fn index(&self, coord: GridCoord) -> Option<usize> {
        if !self.in_bounds(coord) {
            return None;
        }
        Some((coord.z * self.height + coord.y) * self.width + coord.x)
    }
}
