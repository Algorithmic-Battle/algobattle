"""Main module, will be run as the generator."""
import json
from pathlib import Path
from random import randrange, sample


max_size = int(Path("/input/max_size.txt").read_text())


numbers = [randrange(2**63 - 1) for _ in range(max_size - 4)]  # (1)!
instance = {
    "numbers": numbers,
}

a, b = randrange(2**63 - 1), randrange(2**63 - 1)  # (2)!
c = randrange(min(a + b, 2**63 - 1))
d = a + b - c

indices = sorted(sample(range(max_size), 4))  # (3)!
for index, number in zip(indices, [a, b, c, d]):
    numbers.insert(index, number)

solution = {
    "indices": indices,
}


Path("/output/instance.json").write_text(json.dumps(instance))
Path("/output/solution.json").write_text(json.dumps(solution))
