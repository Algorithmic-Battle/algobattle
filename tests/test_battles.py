"""Tests for the Battle types."""

from collections.abc import Iterable
from enum import Enum
from itertools import chain, cycle
from pathlib import Path
from types import EllipsisType
from typing import Any, TypeVar, Unpack, cast
from unittest import IsolatedAsyncioTestCase, TestCase, main
from uuid import uuid4

from algobattle.battle import Battle, Fight, FightHandler, FightHistory, Improving, Iterated, ProgramRunInfo, RunKwargs
from algobattle.match import BattleObserver, EmptyUi
from algobattle.program import GeneratorResult, Matchup, SolverResult, Team
from algobattle.util import Encodable, ExceptionInfo, Role, TempDir
from tests.testsproblem.problem import TestInstance, TestSolution

T = TypeVar("T")


def always(val: T) -> "cycle[T]":
    """Shorthand for an iterator always yielding a single value."""
    return cycle([val])


class TestTeam(Team):
    """Team that doesn't rely on actual docker images."""

    def __init__(self, team_name: str) -> None:
        object.__setattr__(self, "name", team_name)


class Result(Enum):
    """Fight result types."""

    success = 1
    fail = 0
    generator_err = "generator error"
    solver_err = "solver error"


succ = Result.success
fail = Result.fail
gen_err = Result.generator_err
sol_err = Result.solver_err


class TestHandler(FightHandler):
    """Test fight handler that just repeats a predefined sequence of results."""

    def __init__(self, battle: Battle, results: Iterable[Result]) -> None:
        self.results = iter(results)
        self.battle = battle

    async def run(
        self,
        max_size: int,
        *,
        timeout_generator: float | None | EllipsisType = ...,
        space_generator: int | None | EllipsisType = ...,
        cpus_generator: int | EllipsisType = ...,
        timeout_solver: float | None | EllipsisType = ...,
        space_solver: int | None | EllipsisType = ...,
        cpus_solver: int | EllipsisType = ...,
        generator_battle_input: Encodable | None = None,
        solver_battle_input: Encodable | None = None,
        generator_battle_output: type[Encodable] | None = None,
        solver_battle_output: type[Encodable] | None = None,
        with_results: bool = False,
    ) -> Any:
        f = None
        match next(self.results):
            case Result.generator_err:
                f = Fight(
                    score=1,
                    max_size=max_size,
                    generator=ProgramRunInfo(error=ExceptionInfo.from_exception(RuntimeError())),
                    solver=ProgramRunInfo(),
                )
            case Result.solver_err:
                f = Fight(
                    score=1,
                    max_size=max_size,
                    generator=ProgramRunInfo(),
                    solver=ProgramRunInfo(error=ExceptionInfo.from_exception(RuntimeError())),
                )
            case r:
                f = Fight(score=r.value, max_size=max_size, generator=ProgramRunInfo(), solver=ProgramRunInfo())
        self.battle.fights.append(f)
        return f


class ConstantHandler(FightHandler):
    """Test fight handler that always succeeds."""

    def __init__(self, battle: Battle, size: int) -> None:
        self.size = size
        self.battle = battle

    async def run(
        self,
        max_size: int,
        *,
        timeout_generator: float | None | EllipsisType = ...,
        space_generator: int | None | EllipsisType = ...,
        cpus_generator: int | EllipsisType = ...,
        timeout_solver: float | None | EllipsisType = ...,
        space_solver: int | None | EllipsisType = ...,
        cpus_solver: int | EllipsisType = ...,
        generator_battle_input: Encodable | None = None,
        solver_battle_input: Encodable | None = None,
        generator_battle_output: type[Encodable] | None = None,
        solver_battle_output: type[Encodable] | None = None,
        with_results: bool = False,
    ) -> Any:
        f = Fight(
            score=float(max_size <= self.size), max_size=max_size, generator=ProgramRunInfo(), solver=ProgramRunInfo()
        )
        self.battle.fights.append(f)
        return f


class IteratedTests(IsolatedAsyncioTestCase):
    """Tests the Iterated type."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = Iterated.Config(rounds=1)
        cls.ui = BattleObserver(EmptyUi(), Matchup(TestTeam("Test"), TestTeam("Test")))

    async def _expect_size(self, size: int) -> Iterated:
        battle = Iterated()
        handler = ConstantHandler(battle, size)
        await battle.run_battle(handler, self.config, 1, self.ui)
        self.assertEqual(size, battle.score(self.config))
        return battle

    async def test_sizes(self) -> None:
        await self._expect_size(1)
        await self._expect_size(17)
        await self._expect_size(128)
        await self._expect_size(17_000)

    async def _expect_fights(
        self, results: Iterable[Result], sizes: list[int], *, score: int | None = None, total: bool = False
    ) -> Iterated:
        battle = Iterated()
        if not total:
            results = chain(results, always(fail))
        handler = TestHandler(battle, results)
        await battle.run_battle(handler, Iterated.Config(rounds=1, maximum_size=1000), 1, self.ui)
        fought_sizes = [f.max_size for f in battle.fights]
        if not total:
            fought_sizes = fought_sizes[: len(sizes)]
        self.assertEqual(sizes, fought_sizes)
        if score is not None:
            self.assertEqual(battle.score(self.config), score)
        return battle

    async def test_full_battle(self) -> None:
        await self._expect_fights(always(fail), [1])
        await self._expect_fights(
            always(succ),
            [1, 2, 6, 15, 31, 56, 92, 141, 205, 286, 386, 507, 651, 820, 1000],
            score=1000,
            total=True,
        )

    async def test_reset_max_size(self) -> None:
        await self._expect_fights([succ, succ, succ, fail], [1, 2, 6, 15, 7])

    async def test_rest_step_size(self) -> None:
        await self._expect_fights([succ, succ, succ, fail, succ], [1, 2, 6, 15, 7, 8])

    async def test_exit_before_cap_success(self) -> None:
        await self._expect_fights([succ, succ, fail, succ, succ, succ], [1, 2, 6, 3, 4, 5], score=5, total=True)

    async def test_exit_before_cap_fail(self) -> None:
        await self._expect_fights([succ, succ, fail, succ, succ, fail], [1, 2, 6, 3, 4, 5], score=4, total=True)

    async def test_exit_solver_fail(self) -> None:
        await self._expect_fights([succ, succ, succ, fail, fail], [1, 2, 6, 15, 7], score=6, total=True)

    async def test_exit_fail_fast(self) -> None:
        await self._expect_fights([succ, fail], [1, 2], score=1, total=True)

    async def test_exit_fail_immedietly(self) -> None:
        await self._expect_fights([fail], [1], score=0, total=True)

    async def test_exit_repeated_gen_fails(self) -> None:
        e = gen_err
        await self._expect_fights(
            [succ, succ, succ, e, e, e, e, e], [1, 2, 6, 15, 31, 56, 92, 141], score=1000, total=True
        )

    async def test_noexit_disconnected_gen_fails(self) -> None:
        e = gen_err
        await self._expect_fights(
            [succ, succ, succ, e, e, succ, e, e, e], [1, 2, 6, 15, 31, 56, 92, 141, 205], score=205
        )


class TrackingHandler(FightHandler):
    """Fight handler that tracks the passed battle data."""

    def __init__(
        self, battle: Improving, gen_res: Iterable[GeneratorResult], sol_res: Iterable[SolverResult | None]
    ) -> None:
        self.battle = battle
        self.gen_res = iter(gen_res)
        self.sol_res = iter(sol_res)
        self.data: list[list[FightHistory.Fight]] = []

    async def run(self, max_size: int, *, with_results: bool = False, **kwargs: Unpack[RunKwargs]) -> Any:
        gen = kwargs.get("generator_battle_input")
        sol = kwargs.get("solver_battle_input")
        assert isinstance(gen, FightHistory)
        assert gen == sol
        self.data.append(list(gen.history))
        return (
            Fight(score=1, max_size=max_size, generator=ProgramRunInfo(), solver=ProgramRunInfo()),
            next(self.gen_res),
            next(self.sol_res),
        )


class ImprovingTests(IsolatedAsyncioTestCase):
    """Tests for the Improving battle type itself."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.config = Improving.Config(num_fights=3)
        cls.ui = BattleObserver(EmptyUi(), Matchup(TestTeam("Test"), TestTeam("Test")))
        cls.history = FightHistory(scores=set(), instances=set(), gen_sols=set(), sol_sols=set())
        cls.history.history = [
            FightHistory.Fight(0.5, cls.gen_res(), cls.sol_res()),
            FightHistory.Fight(1, cls.gen_res(), cls.sol_res()),
        ]

    async def run_battle(
        self,
        gen_res: Iterable[GeneratorResult],
        sol_res: Iterable[SolverResult | None],
        config: Improving.Config | None = None,
    ) -> TrackingHandler:
        battle = Improving()
        handler = TrackingHandler(battle, gen_res, sol_res)
        await battle.run_battle(handler, config=config or self.config, min_size=5, ui=self.ui)
        return handler

    @staticmethod
    def gen_res(instance: bool = True, solution: bool = True) -> GeneratorResult:
        return GeneratorResult(
            instance=TestInstance(semantics=True, extra=str(uuid4())) if instance else None,
            solution=cast(Any, TestSolution(semantics=True, quality=True, extra=str(uuid4()))) if solution else None,
        )

    @staticmethod
    def sol_res(solution: bool = True) -> SolverResult:
        return SolverResult(
            solution=cast(Any, TestSolution(semantics=True, quality=True, extra=str(uuid4()))) if solution else None,
        )

    async def test_first_fight_empty(self) -> None:
        handler = await self.run_battle([self.gen_res()], [self.sol_res()], Improving.Config(num_fights=1))
        self.assertEqual(len(handler.data), 1)
        self.assertEqual(len(handler.data[0]), 0)

    async def test_fights_tracked(self) -> None:
        gen_res = [self.gen_res() for _ in range(3)]
        sol_res = [self.sol_res() for _ in range(3)]
        handler = await self.run_battle(gen_res, sol_res)
        self.assertEqual(len(handler.data), 3)
        for i, history in enumerate(handler.data):
            self.assertEqual(
                history, [FightHistory.Fight(1, g, s) for (g, s) in zip(gen_res[:i], sol_res[:i], strict=True)]
            )

    async def test_sol_none(self) -> None:
        gen_res = [self.gen_res() for _ in range(3)]
        sol_res = [self.sol_res(False), self.sol_res(), self.sol_res()]
        handler = await self.run_battle(gen_res, sol_res)
        sol = handler.data[-1][0].solver
        self.assertIsNotNone(sol)
        assert sol is not None
        self.assertIsNone(sol.solution)

    async def test_no_sol(self) -> None:
        gen_res = [self.gen_res() for _ in range(3)]
        sol_res = [None, self.sol_res(), self.sol_res()]
        handler = await self.run_battle(gen_res, sol_res)
        sol = handler.data[-1][0].solver
        self.assertIsNone(sol)

    async def test_no_witness(self) -> None:
        gen_res = [self.gen_res(solution=False) for _ in range(3)]
        sol_res = [self.sol_res(), self.sol_res(), self.sol_res()]
        handler = await self.run_battle(gen_res, sol_res)
        self.assertIsNotNone(handler.data[-1][0].generator.instance)
        self.assertIsNone(handler.data[-1][0].generator.solution)

    async def test_no_instance(self) -> None:
        gen_res = [self.gen_res(instance=False) for _ in range(3)]
        sol_res = [self.sol_res(), self.sol_res(), self.sol_res()]
        handler = await self.run_battle(gen_res, sol_res)
        self.assertIsNone(handler.data[-1][0].generator.instance)
        self.assertIsNotNone(handler.data[-1][0].generator.solution)


class FightHistoryEncoding(TestCase):
    """Tests the encoding of the FightHistory class."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.history = FightHistory(scores=set(), instances=set(), gen_sols=set(), sol_sols=set())
        cls.history.history = [
            FightHistory.Fight(0.5, ImprovingTests.gen_res(), ImprovingTests.sol_res()),
            FightHistory.Fight(1, ImprovingTests.gen_res(), ImprovingTests.sol_res()),
        ]

    @staticmethod
    def role_sets() -> Iterable[set[Role]]:
        yield {Role.generator}
        yield {Role.solver}
        yield {Role.generator, Role.solver}
        yield set()

    def _encode_attr(self, target: Path, attr: str) -> Iterable[tuple[int, Path, bool]]:
        for roles in self.role_sets():
            setattr(self.history, attr, roles)
            yield from self._encode_role(target / str(uuid4()), Role.generator, roles)
            yield from self._encode_role(target / str(uuid4()), Role.solver, roles)

    def _encode_role(self, target: Path, role: Role, roles: set[Role]) -> Iterable[tuple[int, Path, bool]]:
        self.history.encode(target, role)
        for f in target.iterdir():
            self.assertIn(f.name, {"0", "1"})
        for f in target.iterdir():
            yield int(f.name), f, role in roles

    def test_encode_size(self) -> None:
        with TempDir() as target:
            for num, folder, should_exist in self._encode_attr(target, "scores"):
                self.assertEqual(folder.joinpath("score.txt").exists(), should_exist)
                if should_exist:
                    self.assertEqual(float(folder.joinpath("score.txt").read_text()), 0.5 if num == 0 else 1)

    def test_encode_instance(self) -> None:
        first = self.history.history[0].generator.instance
        second = self.history.history[1].generator.instance
        with TempDir() as target:
            for num, folder, should_exist in self._encode_attr(target, "instances"):
                self.assertEqual(folder.joinpath("instance.json").exists(), should_exist)
                if should_exist:
                    decoded = TestInstance.decode(folder / "instance.json", 25, Role.generator)
                    self.assertEqual(decoded, first if num == 0 else second)

    def test_encode_witness(self) -> None:
        instance = self.history.history[0].generator.instance
        assert isinstance(instance, TestInstance)
        first = self.history.history[0].generator.solution
        second = self.history.history[1].generator.solution
        with TempDir() as target:
            for num, folder, should_exist in self._encode_attr(target, "gen_sols"):
                self.assertEqual(folder.joinpath("generator_solution.json").exists(), should_exist)
                if should_exist:
                    decoded = TestSolution.decode(folder / "generator_solution.json", 25, Role.generator, instance)
                    self.assertEqual(decoded, first if num == 0 else second)

    def test_encode_solution(self) -> None:
        instance = self.history.history[0].generator.instance
        assert isinstance(instance, TestInstance)
        first = cast(SolverResult, self.history.history[0].solver).solution
        second = cast(SolverResult, self.history.history[1].solver).solution
        with TempDir() as target:
            for num, folder, should_exist in self._encode_attr(target, "sol_sols"):
                self.assertEqual(folder.joinpath("solver_solution.json").exists(), should_exist)
                if should_exist:
                    decoded = TestSolution.decode(folder / "solver_solution.json", 25, Role.generator, instance)
                    self.assertEqual(decoded, first if num == 0 else second)


class ImprovingScoreTests(TestCase):
    """Tests the Improving battle score function."""

    @staticmethod
    def fight(score: float) -> Fight:
        return Fight(score=score, max_size=25, generator=ProgramRunInfo(), solver=ProgramRunInfo())

    def test_score_equal(self) -> None:
        battle = Improving(fights=[self.fight(0.7) for _ in range(17)])
        self.assertAlmostEqual(battle.score(Improving.Config()), 0.7)

    def test_score_cliff(self) -> None:
        battle = Improving(fights=[self.fight(0), self.fight(0), self.fight(1)])
        self.assertAlmostEqual(battle.score(Improving.Config()), 1.1**2 / (2.1 + 1.1**2))

    def test_score_increasing(self) -> None:
        battle = Improving(fights=[self.fight(0), self.fight(0.5), self.fight(1)])
        self.assertAlmostEqual(battle.score(Improving.Config()), (0.5 * 1.1 + 1.1**2) / (2.1 + 1.1**2))

    def test_score_dropoff(self) -> None:
        battle = Improving(fights=[self.fight(1), self.fight(0), self.fight(0)])
        self.assertAlmostEqual(battle.score(Improving.Config()), 1 / (2.1 + 1.1**2))


if __name__ == "__main__":
    main()
