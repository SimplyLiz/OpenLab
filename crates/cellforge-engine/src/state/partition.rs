/// State partitioning for parallel process execution.
pub struct Partition {
    _private: (),
}

impl Partition {
    pub fn new() -> Self {
        Self { _private: () }
    }
}
