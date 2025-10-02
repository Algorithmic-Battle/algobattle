"""Tests for the Match class."""
# pyright: reportMissingSuperCall=false
from pathlib import Path
from typing import Any
from unittest import IsolatedAsyncioTestCase, TestCase, main

from pydantic import ByteSize, ValidationError

from algobattle.battle import Averaged, Fight, Iterated, ProgramRunInfo
from algobattle.match import (
    AlgobattleConfig,
    DynamicProblemConfig,
    Match,
    MatchConfig,
    MatchupStr,
    ProjectConfig,
    RunConfig,
    TeamInfo,
)
from algobattle.program import Matchup, Team, TeamHandler

from .testsproblem.problem import TestProblem


class TestTeam(Team):
    """Team that doesn't rely on actual docker images."""

    def __init__(self, team_name: str) -> None:
        object.__setattr__(self, "name", team_name)


def dummy_result(*score: float) -> list[Fight]:
    """Creates a list of dummy results for testing."""
    return [
        Fight(
            score=s,
            max_size=0,
            generator=ProgramRunInfo(),
            solver=ProgramRunInfo(),
        )
        for s in score
    ]


class Matchtests(TestCase):
    """Tests for the match object."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up a match object."""
        cls.team0 = TestTeam("0")
        cls.team1 = TestTeam("1")
        cls.matchup0 = Matchup(cls.team0, cls.team1)
        cls.matchup0_str = MatchupStr.make(cls.matchup0)
        cls.matchup1 = Matchup(cls.team1, cls.team0)
        cls.matchup1_str = MatchupStr.make(cls.matchup1)
        team_dict: dict[str, Any] = {
            "active_teams": [cls.team0.name, cls.team1.name],
            "excluded_teams": {},
        }
        cls.iterated_kwargs = team_dict | {
            "config": AlgobattleConfig(match=MatchConfig(problem="TestProblem", battle=Iterated.Config())),
        }
        cls.averated_kwargs = team_dict | {
            "config": AlgobattleConfig(match=MatchConfig(problem="TestProblem", battle=Averaged.Config())),
        }
        cls.teams = TeamHandler([cls.team0, cls.team1])

    def test_all_battle_pairs_two_teams(self):
        """Two teams both generate and solve one time each."""
        self.assertEqual(self.teams.matchups, [self.matchup0, self.matchup1])

    def test_all_battle_pairs_single_player(self):
        """A team playing against itself is the only battle pair in single player."""
        teams = TeamHandler([self.team0])
        self.assertEqual(teams.matchups, [Matchup(self.team0, self.team0)])

    def test_calculate_points_zero_rounds(self):
        """All teams get 0 points if no rounds have been fought."""
        match = Match(**self.iterated_kwargs)
        self.assertEqual(match.calculate_points(), {self.team0.name: 0, self.team1.name: 0})

    def test_calculate_points_iterated_no_successful_round(self):
        """Two teams should get an equal amount of points if nobody solved anything."""
        match = Match(**self.iterated_kwargs)
        battle = Iterated()
        battle.results = [0]
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle
        self.assertEqual(match.calculate_points(), {self.team0.name: 50, self.team1.name: 50})

    def test_calculate_points_iterated_draw(self):
        """Two teams should get an equal amount of points if both solved a problem equally well."""
        match = Match(**self.iterated_kwargs)
        battle = Iterated()
        battle.results = [20]
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle
        self.assertEqual(match.calculate_points(), {self.team0.name: 50, self.team1.name: 50})

    def test_calculate_points_iterated_domination(self):
        """One team should get all points if it solved anything and the other team nothing."""
        match = Match(**self.iterated_kwargs)
        battle = Iterated()
        battle.results = [10]
        battle2 = Iterated()
        battle2.results = [0]
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle2
        self.assertEqual(match.calculate_points(), {self.team0.name: 0, self.team1.name: 100})

    def test_calculate_points_iterated_one_team_better(self):
        """One team should get more points than the other if it performed better."""
        match = Match(**self.iterated_kwargs)
        battle = Iterated()
        battle.results = [10]
        battle2 = Iterated()
        battle2.results = [20]
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle2
        self.assertEqual(match.calculate_points(), {self.team0.name: 66.7, self.team1.name: 33.3})

    def test_calculate_points_averaged_no_successful_round(self):
        """Two teams should get an equal amount of points if nobody solved anything."""
        match = Match(**self.averated_kwargs)
        battle = Averaged()
        battle.fights = dummy_result(0, 0, 0)
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle
        self.assertEqual(match.calculate_points(), {self.team0.name: 50, self.team1.name: 50})

    def test_calculate_points_averaged_draw(self):
        """Two teams should get an equal amount of points if both solved a problem equally well."""
        match = Match(**self.averated_kwargs)
        battle = Averaged()
        battle.fights = dummy_result(0.5, 0.5, 0.5)
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle
        self.assertEqual(match.calculate_points(), {self.team0.name: 50, self.team1.name: 50})

    def test_calculate_points_averaged_domination(self):
        """One team should get all points if it solved anything and the other team nothing."""
        match = Match(**self.averated_kwargs)
        battle = Averaged()
        battle.fights = dummy_result(0, 0, 0)
        battle2 = Averaged()
        battle2.fights = dummy_result(1, 1, 1)
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle2
        self.assertEqual(match.calculate_points(), {self.team0.name: 100, self.team1.name: 0})

    def test_calculate_points_averaged_one_team_better(self):
        """One team should get more points than the other if it performed better."""
        match = Match(**self.averated_kwargs)
        battle = Averaged()
        battle.fights = dummy_result(0.6, 0.6, 0.6)
        battle2 = Averaged()
        battle2.fights = dummy_result(0.4, 0.4, 0.4)
        match.battles[self.matchup0_str] = battle
        match.battles[self.matchup1_str] = battle2
        self.assertEqual(match.calculate_points(), {self.team0.name: 40, self.team1.name: 60})

    # TODO: Add tests for remaining functions


class Execution(IsolatedAsyncioTestCase):
    """Some basic tests for the execution of the battles."""

    @classmethod
    def setUpClass(cls) -> None:
        problem_path = Path(__file__).parent / "testsproblem"
        cls.problem = TestProblem
        run_params = RunConfig(timeout=2)
        cls.config_iter = AlgobattleConfig(
            match=MatchConfig(
                generator=run_params,
                solver=run_params,
                problem="Test Problem",
                battle=Iterated.Config(maximum_size=10, rounds=2),
            ),
        )
        cls.config_avg = AlgobattleConfig(
            match=MatchConfig(
                generator=run_params,
                solver=run_params,
                problem="Test Problem",
                battle=Averaged.Config(instance_size=5, num_fights=3),
            ),
        )
        cls.generator = problem_path / "generator"
        cls.solver = problem_path / "solver"

    async def test_basic(self):
        self.config_iter.teams = {"team_0": TeamInfo(generator=self.generator, solver=self.solver)}
        res = await Match(config=self.config_iter).run()
        for result in res.battles.values():
            self.assertIsNone(result.runtime_error)
            for fight in result.fights:
                self.assertIsNone(fight.generator.error)
                assert fight.solver is not None
                self.assertIsNone(fight.solver.error)

    async def test_multi_team(self):
        team0 = TeamInfo(generator=self.generator, solver=self.solver)
        team1 = TeamInfo(generator=self.generator, solver=self.solver)
        self.config_iter.teams = {"team_0": team0, "team_1": team1}
        res = await Match(config=self.config_iter).run()
        for result in res.battles.values():
            self.assertIsNone(result.runtime_error)
            for fight in result.fights:
                self.assertIsNone(fight.generator.error)
                assert fight.solver is not None
                self.assertIsNone(fight.solver.error)

    async def test_averaged(self):
        self.config_avg.teams = {"team_0": TeamInfo(generator=self.generator, solver=self.solver)}
        res = await Match(config=self.config_avg).run()
        for result in res.battles.values():
            self.assertIsNone(result.runtime_error)
            for fight in result.fights:
                self.assertIsNone(fight.generator.error)
                assert fight.solver is not None
                self.assertIsNone(fight.solver.error)


class Parsing(TestCase):
    """Testing the parsing of CLI and config files."""

    @classmethod
    def setUpClass(cls) -> None:
        path = Path(__file__).parent
        cls.problem_path = path / "testsproblem"
        cls.configs_path = path / "configs"
        cls.teams = {"team_0": TeamInfo(generator=cls.problem_path / "generator", solver=cls.problem_path / "solver")}

    def test_no_cfg_default(self):
        with self.assertRaises(FileNotFoundError):
            AlgobattleConfig.from_file(self.problem_path)

    def test_empty_cfg(self):
        with self.assertRaises(ValidationError):
            AlgobattleConfig.from_file(self.configs_path / "empty.toml")

    def test_cfg(self):
        cfg = AlgobattleConfig.from_file(self.configs_path / "test.toml")
        self.assertEqual(
            cfg,
            AlgobattleConfig(
                match=MatchConfig(
                    generator=RunConfig(space=ByteSize(10)),
                    problem="Test Problem",
                    battle=Averaged.Config(num_fights=1),
                ),
                project=ProjectConfig(points=10, results=self.configs_path / "results"),
                problem=DynamicProblemConfig(location=self.configs_path / "problem.py"),
            ),
        )

    def test_cfg_team(self):
        cfg = AlgobattleConfig.from_file(self.configs_path / "teams.toml")
        self.assertEqual(
            cfg,
            AlgobattleConfig(
                teams={
                    "team 1": TeamInfo(generator=self.configs_path, solver=self.configs_path),
                    "team 2": TeamInfo(generator=self.configs_path, solver=self.configs_path),
                },
                match=MatchConfig(
                    problem="Test Problem",
                ),
                project=ProjectConfig(results=self.configs_path / "results"),
                problem=DynamicProblemConfig(location=self.configs_path / "problem.py"),
            ),
        )

    def test_cfg_team_no_name(self):
        with self.assertRaises(ValueError):
            AlgobattleConfig.from_file(self.configs_path / "teams_incorrect.toml")


if __name__ == "__main__":
    main()
