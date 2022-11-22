"""Tests for the Match class."""
# pyright: reportMissingSuperCall=false
import unittest
import logging

from configparser import ConfigParser
from pathlib import Path

import algobattle
from algobattle.battle import setup_logging
from algobattle.battle_wrappers.iterated import Iterated
from algobattle.battle_wrappers.averaged import Averaged
from algobattle.fight_handler import FightHandler
from algobattle.match import MatchInfo, MatchResult
from algobattle.team import Team, Matchup, TeamInfo
from algobattle.docker_util import Image, get_os_type
from . import testsproblem

logging.disable(logging.CRITICAL)


class TestImage(Image):
    """Docker image that doesn't rely on an actual docker daemon image."""

    def __init__(self, image_name: str) -> None:
        self.name = image_name
        self.id = image_name
        self.description = image_name

    def run(self, input: str = "", timeout: float | None = None, memory: int | None = None, cpus: int | None = None) -> str:
        return input

    def remove(self) -> None:
        return


class TestTeam(Team):
    """Team that doesn't rely on actual docker images."""

    def __init__(self, team_name: str) -> None:
        self.name = team_name
        self.generator = TestImage(f"TestImage-{self.name}-generator")
        self.solver = TestImage(f"TestImage-{self.name}-solver")


class Matchtests(unittest.TestCase):
    """Tests for the match object."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up a match object."""
        cls.team0 = TestTeam("0")
        cls.team1 = TestTeam("1")
        cls.matchup0 = Matchup(cls.team0, cls.team1)
        cls.matchup1 = Matchup(cls.team1, cls.team0)

        config_path = Path(algobattle.__file__).parent / "config.ini"
        cls.config = ConfigParser()
        cls.config.read(config_path)

        cls.fight_handler = FightHandler(testsproblem.Problem(), cls.config)

        cls.wrapper_iter = Iterated(cls.fight_handler, cls.config)
        cls.wrapper_avg = Averaged(cls.fight_handler, cls.config)
        cls.match_iter = MatchInfo(cls.wrapper_iter, [cls.team0, cls.team1])
        cls.match_avg = MatchInfo(cls.wrapper_avg, [cls.team0, cls.team1])

    def test_all_battle_pairs_two_teams(self):
        """Two teams both generate and solve one time each."""
        self.assertEqual(self.match_iter.matchups, [self.matchup0, self.matchup1])

    def test_all_battle_pairs_single_player(self):
        """A team playing against itself is the only battle pair in single player."""
        match = MatchInfo(self.wrapper_iter, [self.team0])
        self.assertEqual(match.matchups, [Matchup(self.team0, self.team0)])

    def test_calculate_points_zero_rounds(self):
        """All teams get 0 points if no rounds have been fought."""
        self.match_iter.rounds = 0
        result = self.match_iter.run_match()
        self.assertEqual(result.calculate_points(100), {self.team0: 0, self.team1: 0})

    def test_calculate_points_iterated_no_successful_round(self):
        """Two teams should get an equal amount of points if nobody solved anything."""
        self.match_iter.rounds = 2
        result = MatchResult(self.match_iter)
        result[self.matchup0] = [Iterated.Result(0, 0, 0), Iterated.Result(0, 0, 0)]
        result[self.matchup1] = [Iterated.Result(0, 0, 0), Iterated.Result(0, 0, 0)]
        self.assertEqual(result.calculate_points(100), {self.team0: 50, self.team1: 50})

    def test_calculate_points_iterated_draw(self):
        """Two teams should get an equal amount of points if both solved a problem equally well."""
        self.match_iter.rounds = 2
        result = MatchResult(self.match_iter)
        result[self.matchup0] = [Iterated.Result(20, 0, 0), Iterated.Result(10, 0, 0)]
        result[self.matchup1] = [Iterated.Result(10, 0, 0), Iterated.Result(20, 0, 0)]
        self.assertEqual(result.calculate_points(100), {self.team0: 50, self.team1: 50})

    def test_calculate_points_iterated_domination(self):
        """One team should get all points if it solved anything and the other team nothing."""
        self.match_iter.rounds = 2
        result = MatchResult(self.match_iter)
        result[self.matchup0] = [Iterated.Result(10, 0, 0), Iterated.Result(10, 0, 0)]
        result[self.matchup1] = [Iterated.Result(0, 0, 0), Iterated.Result(0, 0, 0)]
        self.assertEqual(result.calculate_points(100), {self.team0: 0, self.team1: 100})

    def test_calculate_points_iterated_one_team_better(self):
        """One team should get more points than the other if it performed better."""
        self.match_iter.rounds = 2
        result = MatchResult(self.match_iter)
        result[self.matchup0] = [Iterated.Result(10, 0, 0), Iterated.Result(10, 0, 0)]
        result[self.matchup1] = [Iterated.Result(20, 0, 0), Iterated.Result(20, 0, 0)]
        self.assertEqual(result.calculate_points(100), {self.team0: 66.6, self.team1: 33.4})

    def test_calculate_points_averaged_no_successful_round(self):
        """Two teams should get an equal amount of points if nobody solved anything."""
        self.match_avg.rounds = 2
        result = MatchResult(self.match_avg)
        result[self.matchup0] = [Averaged.Result(1, 1, 1, [0, 0, 0]), Averaged.Result(1, 1, 1, [0, 0, 0])]
        result[self.matchup1] = [Averaged.Result(1, 1, 1, [0, 0, 0]), Averaged.Result(1, 1, 1, [0, 0, 0])]
        self.assertEqual(result.calculate_points(100), {self.team0: 50, self.team1: 50})

    def test_calculate_points_averaged_draw(self):
        """Two teams should get an equal amount of points if both solved a problem equally well."""
        self.match_avg.rounds = 2
        result = MatchResult(self.match_avg)
        result[self.matchup0] = [Averaged.Result(1, 1, 1, [1.5, 1.5, 1.5]), Averaged.Result(1, 1, 1, [1.5, 1.5, 1.5])]
        result[self.matchup1] = [Averaged.Result(1, 1, 1, [1.5, 1.5, 1.5]), Averaged.Result(1, 1, 1, [1.5, 1.5, 1.5])]
        self.assertEqual(result.calculate_points(100), {self.team0: 50, self.team1: 50})

    def test_calculate_points_averaged_domination(self):
        """One team should get all points if it solved anything and the other team nothing."""
        self.match_avg.rounds = 2
        result = MatchResult(self.match_avg)
        result[self.matchup0] = [Averaged.Result(1, 1, 1, [0, 0, 0]), Averaged.Result(1, 1, 1, [0, 0, 0])]
        result[self.matchup1] = [Averaged.Result(1, 1, 1, [1, 1, 1]), Averaged.Result(1, 1, 1, [1, 1, 1])]
        self.assertEqual(result.calculate_points(100), {self.team0: 100, self.team1: 0})

    def test_calculate_points_averaged_one_team_better(self):
        """One team should get more points than the other if it performed better."""
        self.match_avg.rounds = 2
        result = MatchResult(self.match_avg)
        result[self.matchup0] = [Averaged.Result(1, 1, 1, [1.5, 1.5, 1.5]), Averaged.Result(1, 1, 1, [1.5, 1.5, 1.5])]
        result[self.matchup1] = [Averaged.Result(1, 1, 1, [1, 1, 1]), Averaged.Result(1, 1, 1, [1, 1, 1])]
        self.assertEqual(result.calculate_points(100), {self.team0: 60, self.team1: 40})

    # TODO: Add tests for remaining functions


class Execution(unittest.TestCase):
    """Some basic tests for the execution of the battles."""

    @classmethod
    def setUpClass(cls) -> None:
        logging.disable(logging.NOTSET)     # reenable logging
        setup_logging(Path.home() / ".algobattle_logs", verbose_logging=True, silent=False)
        cls.problem = Path(__file__).parent / "testsproblem"
        cls.config = cls.problem / "config_short_run_timeout.ini"
        cls.generator = cls.problem / "generator"
        cls.solver = cls.problem / "solver"
        if get_os_type() == "windows":
            cls.generator /= "Dockerfile_windows"
            cls.solver /= "Dockerfile_windows"

    @classmethod
    def tearDownClass(cls) -> None:
        logging.disable(logging.CRITICAL)
        return super().tearDownClass()

    def test_basic(self):
        team = TeamInfo("team0", self.generator, self.solver)
        match_info = MatchInfo.build(
            problem_path=self.problem, config_path=self.config, team_infos=[team], battle_type="iterated", rounds=2
        )
        with match_info:
            match_info.run_match()

    def test_multi_team(self):
        team0 = TeamInfo("team0", self.generator, self.solver)
        team1 = TeamInfo("team1", self.generator, self.solver)
        match_info = MatchInfo.build(
            problem_path=self.problem, config_path=self.config, team_infos=[team0, team1], battle_type="iterated", rounds=2
        )
        with match_info:
            match_info.run_match()

    def test_averaged(self):
        team = TeamInfo("team0", self.generator, self.solver)
        match_info = MatchInfo.build(
            problem_path=self.problem, config_path=self.config, team_infos=[team], battle_type="averaged", rounds=2
        )
        with match_info:
            match_info.run_match()


if __name__ == "__main__":
    unittest.main()
