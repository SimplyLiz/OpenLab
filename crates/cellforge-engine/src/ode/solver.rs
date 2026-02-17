/// Generic ODE solver trait and RK45 implementation.
pub struct OdeSolver {
    _private: (),
}

impl OdeSolver {
    pub fn new() -> Self {
        Self { _private: () }
    }
}
