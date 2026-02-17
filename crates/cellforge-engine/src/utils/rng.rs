use rand::rngs::StdRng;
use rand::SeedableRng;

/// Create a seeded random number generator for reproducible simulations.
pub fn seeded_rng(seed: u64) -> StdRng {
    StdRng::seed_from_u64(seed)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_seeded_rng_deterministic() {
        use rand::Rng;
        let mut rng1 = seeded_rng(42);
        let mut rng2 = seeded_rng(42);
        let v1: f64 = rng1.gen();
        let v2: f64 = rng2.gen();
        assert_eq!(v1, v2);
    }
}
