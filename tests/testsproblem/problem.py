"""Problem class built for tests."""

from algobattle.problem import Problem, InstanceModel, SolutionModel
from algobattle.util import Role, ValidationError


class TestInstance(InstanceModel):
    """Artificial problem used for tests."""

    semantics: bool

    @property
    def size(self) -> int:
        return 0

    def validate_instance(self):
        if not self.semantics:
            raise ValidationError("")


class TestSolution(SolutionModel[TestInstance]):
    """Solution class for :class:`Tests`."""

    semantics: bool
    quality: bool

    def validate_solution(self, instance: TestInstance, role: Role) -> None:
        if not self.semantics:
            raise ValidationError("")


def score(instance: TestInstance, solver_solution: TestSolution, generator_solution: TestSolution | None) -> float:
    """Test score function."""
    return solver_solution.quality


TestProblem = Problem(
    name="Tests",
    instance_cls=TestInstance,
    solution_cls=TestSolution,
    with_solution=False,
    score=score,
)
