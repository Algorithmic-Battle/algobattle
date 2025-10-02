"""Tests for all util functions."""
import unittest
from math import inf

from algobattle.battle import Averaged, Battle, Iterated
from algobattle.problem import InstanceModel, SolutionModel, default_score
from algobattle.util import Role


class DummyInstance(InstanceModel):
    @property
    def size(self) -> int:
        return 1


class DummySolution(SolutionModel[DummyInstance]):
    val: float

    def score(self, instance: DummyInstance, role: Role) -> float:
        return self.val


class Utiltests(unittest.TestCase):
    """Tests for the util functions."""

    def test_default_battle_types(self):
        """Initializing an existing battle type works as expected."""
        self.assertEqual(Battle.all()["Iterated"], Iterated)
        self.assertEqual(Battle.all()["Averaged"], Averaged)

    def test_default_fight_score(self):
        """Tests the default fight scoring function."""
        instance = DummyInstance()
        scores = [
            (0, 0, 1),
            (0, 2, 1),
            (0, 4, 1),
            (0, inf, 1),
            (2, 0, 0),
            (2, 2, 1),
            (2, 4, 1),
            (2, inf, 1),
            (4, 0, 0),
            (4, 2, 0.5),
            (4, 4, 1),
            (4, inf, 1),
            (inf, 0, 0),
            (inf, 2, 0),
            (inf, 4, 0),
            (inf, inf, 1),
        ]
        for gen, sol, score in scores:
            self.assertEqual(
                default_score(
                    instance, generator_solution=DummySolution(val=gen), solver_solution=DummySolution(val=sol)
                ),
                score,
            )


if __name__ == "__main__":
    unittest.main()
