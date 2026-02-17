use pyo3::prelude::*;

mod coordinator;
mod fba;
mod ode;
mod ssa;
mod state;
mod utils;

/// CellForge native engine module.
#[pymodule]
mod _engine {
    use pyo3::prelude::*;

    #[pymodule_export]
    const __version__: &str = "0.1.0";
}
