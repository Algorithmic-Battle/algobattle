// Main module, will be run as the solver

use std::fs;
use std::error::Error;
use serde_json::{to_string, from_str};
use itertools::Itertools;
use serde::{Deserialize, Serialize};

#[derive(Deserialize)] // (1)!
struct Instance {
    numbers: Vec<u64>,
}

#[derive(Serialize)] // (2)!
struct Solution {
    indices: Vec<usize>
}


fn main() -> Result<(), Box<dyn Error>> {
    let instance: Instance = from_str(&fs::read_to_string("/input/instance.json")?)?;
    let numbers = instance.numbers;

    for indices in (0..numbers.len()).combinations(4) { // (3)!
        let first = numbers[indices[0]] + numbers[indices[1]];
        let second = numbers[indices[2]] + numbers[indices[3]];

        if first == second { // (4)!
            let solution = Solution {indices: indices};
            fs::write("/output/solution.json", to_string(&solution)?)?;
            return Ok(());
        }
    }
    unreachable!()
}
