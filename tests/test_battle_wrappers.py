"""Tests for all util functions."""
from dataclasses import dataclass
from unittest import TestCase, main
import logging

from algobattle.battle_wrappers.averaged import Averaged
from algobattle.battle_wrappers.iterated import Iterated
from algobattle.matchups import BattleMatchups, Matchup
from algobattle.team import Team

logging.disable(logging.CRITICAL)


@dataclass
class TestTeam(Team):
    """Team class that doesn't build containers to make tests that don't need them run faster."""
    name: str

def team(name: str) -> Team:
    """Aliasing function to deal with invariance issues."""
    return TestTeam(name)

class PointsCalculationTests(TestCase):
    """Tests for the points calculation functions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.teams = [team("0"), team("1")]
        cls.matchups = BattleMatchups(cls.teams)

    def test_calculate_points_iterated_zero_rounds(self):
        self.assertEqual(Iterated.MatchResult(self.matchups, rounds=0).calculate_points(100), {})

    def test_calculate_points_iterated_no_successful_round(self):
        results = Iterated.MatchResult(self.matchups, rounds=2)
        for m in self.matchups:
            results[m] = [Iterated.Result(solved=0), Iterated.Result(solved=0)]
        self.assertEqual(results.calculate_points(100), {self.teams[0]: 50, self.teams[1]: 50})

    def test_calculate_points_iterated_draw(self):
        results = Iterated.MatchResult(self.matchups, rounds=2)
        results[self.matchups[0]] = [Iterated.Result(solved=20), Iterated.Result(solved=10)]
        results[self.matchups[1]] = [Iterated.Result(solved=10), Iterated.Result(solved=20)]
        self.assertEqual(results.calculate_points(100), {self.teams[0]: 50, self.teams[1]: 50})

    def test_calculate_points_iterated_domination(self):
        results = Iterated.MatchResult(self.matchups, rounds=2)
        results[self.matchups[0]] = [Iterated.Result(solved=10), Iterated.Result(solved=10)]
        results[self.matchups[1]] = [Iterated.Result(solved=0), Iterated.Result(solved=0)]
        self.assertEqual(results.calculate_points(100), {self.teams[0]: 0, self.teams[1]: 100})

    def test_calculate_points_averaged_zero_rounds(self):
        self.assertEqual(Averaged.MatchResult(self.matchups, rounds=0).calculate_points(100), {})

    def test_calculate_points_averaged_draw(self):
        results = Averaged.MatchResult(self.matchups, rounds=2)
        results[self.matchups[0]] = [Averaged.Result([1.5, 1.5, 1.5]), Averaged.Result([1.5, 1.5, 1.5])]
        results[self.matchups[1]] = [Averaged.Result([1.5, 1.5, 1.5]), Averaged.Result([1.5, 1.5, 1.5])]
        self.assertEqual(results.calculate_points(100), {self.teams[0]: 50, self.teams[1]: 50})

    def test_calculate_points_averaged_domination(self):
        results = Averaged.MatchResult(self.matchups, rounds=2)
        results[self.matchups[0]] = [Averaged.Result([1.5, 1.5, 1.5]), Averaged.Result([1.5, 1.5, 1.5])]
        results[self.matchups[1]] = [Averaged.Result([1.0, 1.0, 1.0]), Averaged.Result([1.0, 1.0, 1.0])]
        self.assertEqual(results.calculate_points(100), {self.teams[0]: 60, self.teams[1]: 40})

    def test_calculate_points_averaged_no_successful_round(self):
        results = Averaged.MatchResult(self.matchups, rounds=2)
        results[self.matchups[0]] = [Averaged.Result([0, 0, 0]), Averaged.Result([0, 0, 0])]
        results[self.matchups[1]] = [Averaged.Result([0, 0, 0]), Averaged.Result([0, 0, 0])]
        self.assertEqual(results.calculate_points(100), {self.teams[0]: 50, self.teams[1]: 50})

class MatchupsTests(TestCase):
    """Tests for the matchup generators."""
    
    def test_all_battle_pairs(self):
        team0 = team("0")
        team1 = team("1")
        teams = [team0, team1]
        self.assertEqual(list(BattleMatchups(teams)), [Matchup(team0, team1), Matchup(team1, team0)])

    def test_all_battle_pairs_solo_battle(self):
        team0 = team("0")
        self.assertEqual(list(BattleMatchups([team0])), [Matchup(team0, team0)])

if __name__ == '__main__':
    main()
