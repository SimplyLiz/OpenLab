use std::collections::HashMap;

/// Central state store holding all simulation variables.
pub struct StateStore {
    arrays: HashMap<String, Vec<f64>>,
}

impl StateStore {
    pub fn new() -> Self {
        Self {
            arrays: HashMap::new(),
        }
    }
}
