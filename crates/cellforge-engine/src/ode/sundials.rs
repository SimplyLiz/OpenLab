/// SUNDIALS CVODE wrapper for stiff ODE systems.
pub struct SundialsSolver {
    _private: (),
}

impl SundialsSolver {
    pub fn new() -> Self {
        Self { _private: () }
    }
}
