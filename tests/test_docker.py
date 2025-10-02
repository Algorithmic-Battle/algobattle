"""Tests for all docker functions."""
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, main as run_tests

from algobattle.match import AlgobattleConfig, MatchConfig, RunConfig
from algobattle.program import Generator, Solver
from algobattle.util import BuildError

from . import testsproblem
from .testsproblem.problem import TestInstance, TestProblem, TestSolution


class ProgramTests(IsolatedAsyncioTestCase):
    """Tests for the Program functions."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up the config and problem objects."""
        cls.problem_path = Path(testsproblem.__file__).parent
        cls.config = AlgobattleConfig(match=MatchConfig(problem="Test Problem")).as_prog_config()
        cls.config_short = AlgobattleConfig(
            match=MatchConfig(problem="Test Problem", generator=RunConfig(timeout=2), solver=RunConfig(timeout=2))
        ).as_prog_config()
        cls.config_strict = AlgobattleConfig(
            match=MatchConfig(
                problem="Test Problem",
                generator=RunConfig(timeout=2),
                solver=RunConfig(timeout=2),
                strict_timeouts=True,
            )
        ).as_prog_config()
        cls.instance = TestInstance(semantics=True)

    async def test_build_error(self):
        """A container's build step times out."""
        with self.assertRaises(BuildError, msg="Build did not complete successfully."):
            await Generator.build(path=self.problem_path / "build_error", problem=TestProblem, config=self.config)

    async def test_build_timeout(self):
        """A container's build step times out."""
        config = AlgobattleConfig(match=MatchConfig(problem="Test Problem", build_timeout=1.5)).as_prog_config()
        with self.assertRaises(BuildError, msg="Build ran into a timeout."):
            await Generator.build(path=self.problem_path / "build_timeout", problem=TestProblem, config=config)

    async def test_gen_lax_timeout(self):
        """The generator times out but still outputs a valid instance."""
        with await Generator.build(
            path=self.problem_path / "generator_timeout", problem=TestProblem, config=self.config_short
        ) as gen:
            res = await gen.run(5)
            self.assertIsNone(res.error)

    async def test_gen_strict_timeout(self):
        """The generator times out."""
        with await Generator.build(
            path=self.problem_path / "generator_timeout",
            problem=TestProblem,
            config=self.config_strict,
        ) as gen:
            res = await gen.run(5)
            assert res.error is not None
            self.assertEqual(res.error.type, "ExecutionTimeout")

    async def test_gen_exec_err(self):
        """The generator doesn't execute properly."""
        with await Generator.build(
            path=self.problem_path / "generator_execution_error", problem=TestProblem, config=self.config
        ) as gen:
            res = await gen.run(5)
            assert res.error is not None
            self.assertEqual(res.error.type, "ExecutionError")

    async def test_gen_syn_err(self):
        """The generator outputs a syntactically incorrect solution."""
        with await Generator.build(
            path=self.problem_path / "generator_syntax_error", problem=TestProblem, config=self.config
        ) as gen:
            res = await gen.run(5)
            assert res.error is not None
            self.assertEqual(res.error.type, "EncodingError")

    async def test_gen_sem_err(self):
        """The generator outputs a semantically incorrect solution."""
        with await Generator.build(
            path=self.problem_path / "generator_semantics_error", problem=TestProblem, config=self.config
        ) as gen:
            res = await gen.run(5)
            assert res.error is not None
            self.assertEqual(res.error.type, "ValidationError")

    async def test_gen_succ(self):
        """The generator returns the fixed instance."""
        with await Generator.build(
            path=self.problem_path / "generator", problem=TestProblem, config=self.config
        ) as gen:
            res = await gen.run(5)
            correct = TestInstance(semantics=True)
            self.assertEqual(res.instance, correct)

    async def test_sol_strict_timeout(self):
        """The solver times out."""
        with await Solver.build(
            path=self.problem_path / "solver_timeout", problem=TestProblem, config=self.config_strict
        ) as sol:
            res = await sol.run(self.instance, 5)
            assert res.error is not None
            self.assertEqual(res.error.type, "ExecutionTimeout")

    async def test_sol_lax_timeout(self):
        """The solver times out but still outputs a correct solution."""
        with await Solver.build(
            path=self.problem_path / "solver_timeout", problem=TestProblem, config=self.config_short
        ) as sol:
            res = await sol.run(self.instance, 5)
            self.assertIsNone(res.error)

    async def test_sol_exec_err(self):
        """The solver doesn't execute properly."""
        with await Solver.build(
            path=self.problem_path / "solver_execution_error", problem=TestProblem, config=self.config
        ) as sol:
            res = await sol.run(self.instance, 5)
            assert res.error is not None
            self.assertEqual(res.error.type, "ExecutionError")

    async def test_sol_syn_err(self):
        """The solver outputs a syntactically incorrect solution."""
        with await Solver.build(
            path=self.problem_path / "solver_syntax_error", problem=TestProblem, config=self.config
        ) as sol:
            res = await sol.run(self.instance, 5)
            assert res.error is not None
            self.assertEqual(res.error.type, "EncodingError")

    async def test_sol_sem_err(self):
        """The solver outputs a semantically incorrect solution."""
        with await Solver.build(
            path=self.problem_path / "solver_semantics_error", problem=TestProblem, config=self.config
        ) as sol:
            res = await sol.run(self.instance, 5)
            assert res.error is not None
            self.assertEqual(res.error.type, "ValidationError")

    async def test_sol_succ(self):
        """The solver outputs a solution with a low quality."""
        with await Solver.build(path=self.problem_path / "solver", problem=TestProblem, config=self.config) as sol:
            res = await sol.run(self.instance, 5)
            correct = TestSolution(semantics=True, quality=True)
            self.assertEqual(res.solution, correct)


if __name__ == "__main__":
    run_tests()
