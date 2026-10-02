"""Main module, will be run as the generator."""
import json
from pathlib import Path
from random import randrange


max_size = int(Path("/input/max_size.txt").read_text())

numbers = [randrange(2**63 - 1) for _ in range(max_size)]  # (1)!
instance = {
    "numbers": numbers,  # (2)!
}
solution = ...


Path("/output/instance.json").write_text(json.dumps(instance))
Path("/output/solution.json").write_text(json.dumps(solution))
