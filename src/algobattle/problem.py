"""Module defining the Problem and Solution base classes and related objects."""
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from importlib.metadata import entry_points
from inspect import Parameter, Signature, signature
from itertools import chain
from math import inf, isnan
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    Literal,
    ParamSpec,
    Protocol,
    Self,
    TypeVar,
    cast,
    get_args,
    overload,
    runtime_checkable,
)

from annotated_types import GroupedMetadata
from pydantic import GetCoreSchemaHandler, ValidationInfo
from pydantic.main import BaseModel
from pydantic_core import CoreSchema
from pydantic_core.core_schema import (
    ValidatorFunctionWrapHandler,
    with_info_after_validator_function,
    with_info_wrap_validator_function,
)

from algobattle.util import Encodable, EncodableBase, EncodableModel, EncodableModelBase, Role, import_file_as_module


class Instance(Encodable, ABC):
    """Instance base class."""

    @property
    @abstractmethod
    def size(self) -> int:
        """The instance's size."""
        raise NotImplementedError

    def validate_instance(self) -> None:
        """Confirms that the parsed instance is valid.

        Should be idempotent, but may also perform additional postprocessing such as bringing the instance
        into a normal form.

        Raises:
            ValidationError: if the created instance is invalid.
        """
        return


InstanceT = TypeVar("InstanceT", bound=Instance, contravariant=True)
P = ParamSpec("P")


class Solution(EncodableBase, ABC, Generic[InstanceT]):
    """A proposed solution for an instance of this problem."""

    @classmethod
    @abstractmethod
    def decode(cls, source: Path, max_size: int, role: Role, instance: InstanceT) -> Self:
        raise NotImplementedError

    def validate_solution(self, instance: InstanceT, role: Role) -> None:
        """Confirms that the parsed solution is valid.

        Should be idempotent, but may also perform additional postprocessing such as bringing the solution
        into a normal form.

        Args:
            instance: The problem instance this solution is purported to solve.
            role: The role of the team that generated this solution.

        Raises:
            ValidationError: if the created instance is invalid.
        """
        return

    def score(self, instance: InstanceT, role: Role) -> float:
        """Calculate the score of this solution for the given problem instance.

        The default implementation always returns 1, indicating that all solutions of this problem are equally good.

        Args:
            instance: The instance this solution solves
            role: The role of the team that generated this solution
        Returns:
            The calculates score of this solution. Must be a nonnegative number. Bigger scores are considered better,
            if your score rates better scores lower you can use the @minimize decorator.
        """
        return 1


def minimize(function: Callable[P, float]) -> Callable[P, float]:
    """Wraps a score function such that smaller scores are considered better."""

    @wraps(function)
    def inner(*args: P.args, **kwargs: P.kwargs) -> float:
        try:
            return 1 / function(*args, **kwargs)
        except ZeroDivisionError:
            return inf

    return inner


def maximize(function: Callable[P, float]) -> Callable[P, float]:
    """No-op decorator to indicate that bigger scores are considered better."""
    return function


SolutionT = TypeVar("SolutionT", bound=Solution[Any])


_I = TypeVar("_I", bound=Instance, contravariant=True)
_S = TypeVar("_S", bound=Solution[Instance], contravariant=True)


@runtime_checkable
class ScoreFunctionWithSol(Protocol, Generic[_I, _S]):
    """Type of `score` function passed to Problem if `with_solution` is set."""

    def __call__(self, instance: _I, *, generator_solution: _S, solver_solution: _S) -> float:
        """Calculates how well a solution solves this problem instance.

        Args:
            instance: The generated instance.
            generator_solution: The solution output by the generator.
            solver_solution: The solution created by the solver.

        Returns:
            The calculated score, a number in [0, 1] with a value of 0 indicating that the solver failed completely and
            1 that it solved the instance perfectly.
        """
        ...


@runtime_checkable
class ScoreFunctionNoSol(Protocol, Generic[_I, _S]):
    """Type of `score` function passed to Problem if `with_solution` is not set."""

    def __call__(self, instance: _I, *, solution: _S) -> float:
        """Calculates how well a solution solves this problem instance.

        Args:
            instance: The generated instance.
            solution: The solution output by the generator.

        Returns:
            The calculated score, a number in [0, 1] with a value of 0 indicating that the solver failed completely and
            1 that it solved the instance perfectly.
        """
        ...


ScoreFunction = ScoreFunctionWithSol[InstanceT, SolutionT] | ScoreFunctionNoSol[InstanceT, SolutionT]


@overload
def default_score(instance: Instance, *, solution: Solution[Any]) -> float:
    ...


@overload
def default_score(instance: Instance, *, generator_solution: SolutionT, solver_solution: SolutionT) -> float:
    ...


def default_score(
    instance: Instance,
    solution: SolutionT | None = None,
    generator_solution: SolutionT | None = None,
    solver_solution: SolutionT | None = None,
) -> float:
    """Calculates how well a solution solves this problem instance.

    If the problem is `with_solution` it calculates the ratio between the solver's and generator's solutions.
    Otherwise it just returns the solution's score clamped to [0, 1].

    Args:
        instance: The generated instance.
        solution: The solution if the problem is with_solution=False.
        solver_solution: The solution created by the solver.
        generator_solution: The solution output by the generator.

    Returns:
        The calculated score, a number in [0, 1] with a value of 0 indicating that the solver failed completely and
        1 that it solved the instance perfectly.
    """
    if solution is None:
        assert generator_solution is not None
        assert solver_solution is not None
        gen_score = generator_solution.score(instance, Role.generator)
        if gen_score < 0 or isnan(gen_score):
            raise RuntimeError("Score function didn't return a nonnegative value.")
        sol_score = solver_solution.score(instance, Role.solver)
        if sol_score < 0 or isnan(sol_score):
            raise RuntimeError("Score function didn't return a nonnegative value.")

        try:
            return max(0, min(1, sol_score / gen_score))
        except ZeroDivisionError:
            # if generator scored 0 then the solver will have achieved an equal or better score
            # i.e. the Fight's score is simply 1 regardless of its solution score.
            return 1
    else:
        return max(0, min(1, solution.score(instance, Role.solver)))


class Problem:
    """The definition of a problem."""

    @overload
    def __init__(
        self,
        *,
        name: str,
        instance_cls: type[InstanceT],
        solution_cls: type[SolutionT],
        min_size: int = 0,
        with_solution: Literal[True] = True,
        score_function: ScoreFunctionWithSol[InstanceT, SolutionT] = default_score,
        test_instance: InstanceT | None = None,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        *,
        name: str,
        instance_cls: type[InstanceT],
        solution_cls: type[SolutionT],
        min_size: int = 0,
        with_solution: Literal[False],
        score_function: ScoreFunctionNoSol[InstanceT, SolutionT] = default_score,
        test_instance: InstanceT | None = None,
    ) -> None:
        ...

    def __init__(
        self,
        *,
        name: str,
        instance_cls: type[InstanceT],
        solution_cls: type[SolutionT],
        min_size: int = 0,
        with_solution: bool = True,
        score_function: ScoreFunction[InstanceT, SolutionT] = default_score,
        test_instance: InstanceT | None = None,
    ) -> None:
        """The definition of a problem.

        Args:
            name: The name of the problem.
            instance_cls: Class defining what instances of this problem look like.
            solution_cls: Class definitng what solutions of this problem look like.
            min_size: Minimum size of valid instances of this problem.
            with_solution: Whether the generator should also create a solution.
            score_function: Function used to score how well a solution solves a problem instance.

                The default scoring function returns the quotient of the solver's to the generator's solution score.

                The score function always takes the instance as the first argument. If `with_solution` is set it then
                gets the generated solutions at `generator_solution` and `solver_solution`. If it is not set it receives
                the solver's solution at `solution`. It should return the calculated score, a number in [0, 1] with a
                value of 0 indicating that the solver failed completely and 1 that it solved the instance perfectly.
            test_instance: A dummy instance that can be used to test whether a solver produces correct output.
        """
        self.name = name
        self.instance_cls = instance_cls
        self.solution_cls = solution_cls
        self.min_size = min_size
        self.with_solution = with_solution
        self.score_function = score_function
        self.test_instance = test_instance
        self._problems[name] = self

    __slots__ = ("instance_cls", "min_size", "name", "score_function", "solution_cls", "test_instance", "with_solution")
    _problems: ClassVar[dict[str, Self]] = {}

    @overload
    def score(self, instance: InstanceT, *, solution: Solution[InstanceT]) -> float:
        ...

    @overload
    def score(
        self, instance: InstanceT, *, generator_solution: Solution[InstanceT], solver_solution: Solution[InstanceT]
    ) -> float:
        ...

    def score(
        self,
        instance: Instance,
        *,
        solution: SolutionT | None = None,
        generator_solution: SolutionT | None = None,
        solver_solution: SolutionT | None = None,
    ) -> float:
        """Helper function to call self.score_function with easier to use overloads."""
        if self.with_solution:
            if not (
                isinstance(instance, self.instance_cls)
                and isinstance(generator_solution, self.solution_cls)
                and isinstance(solver_solution, self.solution_cls)
                and solution is None
            ):
                raise TypeError
            if TYPE_CHECKING:
                assert isinstance(self.score_function, ScoreFunctionWithSol)
            return self.score_function(instance, generator_solution=generator_solution, solver_solution=solver_solution)
        else:
            if not (
                isinstance(instance, self.instance_cls)
                and isinstance(solution, self.solution_cls)
                and generator_solution is None
                and solver_solution is None
            ):
                raise TypeError
            if TYPE_CHECKING:
                assert isinstance(self.score_function, ScoreFunctionNoSol)
            return self.score_function(instance, solution=solution)

    @classmethod
    def load_file(cls, name: str, file: Path) -> Self:
        """Loads the problem from the specified file."""
        existing_problems = cls._problems.copy()
        cls._problems = {}
        try:
            import_file_as_module(file, "__algobattle_problem__")
            if name not in cls._problems:
                raise ValueError(f"The {name} problem is not defined in {file}")
            else:
                return cls._problems[name]
        finally:
            cls._problems = existing_problems

    @classmethod
    def load(cls, name: str, file: Path | None = None) -> Self:
        """Loads the problem with the given name.

        Args:
            name: The name of the Problem to use.
            file: Path to a file containing this problem.

        Raises:
            ValueError: If the problem is not specified properly
            RuntimeError: If the problem's dynamic import fails
        """
        if file:
            return cls.load_file(name, file)
        if name in cls._problems:
            return cls._problems[name]
        match list(entry_points(group="algobattle.problem", name=name)):
            case []:
                raise ValueError("Problem name is not valid.")
            case [e]:
                loaded: object = e.load()
                if not isinstance(loaded, cls):
                    raise ValueError( # noqa: TRY004
                        f"The entrypoint '{name}' doesn't point to a problem but a {loaded.__class__.__qualname__}."
                    )
                return loaded
            case entypoints:
                raise ValueError(
                    f"Multiple problem entrypoints with the name {name} exist!"
                    f" The modules providing them are: {', '.join(e.module for e in entypoints)}."
                )

    @classmethod
    def available(cls) -> set[str]:
        """Returns the names of all available Problems."""
        return set(chain(cls._problems.keys(), (e.name for e in entry_points(group="algobattle.problem"))))


ModelType = Literal["instance", "solution"]
ModelReference = ModelType | Literal["self"]


@dataclass(frozen=True, slots=True)
class AttributeReference:
    """Creates a reference to the attribute of a model to be used in validaton schemas."""

    model: ModelReference
    attribute: str

    def get_value(self, info: ValidationInfo) -> Any | None:
        """Returns the referenced value from the correct object in the info context.

        If the correct object is not in the context or doesn't have the referenced attribute it returns None.
        """
        if info.context is None or self.model not in info.context:
            return None
        model = info.context[self.model]
        if hasattr(model, self.attribute):
            return getattr(model, self.attribute)
        else:
            return None

    def __str__(self) -> str:
        return f"{self.model}.{self.attribute}"

    def needs_self(self, model_type: Literal["instance", "solution"]) -> bool:
        """Checks if an attribute reference needs a reference to the current model in order to be resolved."""
        if self.model == "self":
            return True
        else:
            return self.model == model_type


NoInfoAttrValidatorFunction = Callable[[Any, Any], Any]
GeneralAttrValidatorFunction = Callable[[Any, Any, ValidationInfo], Any]
AttrValidatorFunction = NoInfoAttrValidatorFunction | GeneralAttrValidatorFunction


def count_positional_params(sig: Signature) -> int:
    """Counts the number of positional parameters in a signature."""
    return sum(1 for param in sig.parameters.values() if can_be_positional(param))


def can_be_positional(param: Parameter) -> bool:
    """Checks whether a parameter is positional."""
    return param.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)


def is_info_validator(validator: AttrValidatorFunction) -> bool:
    """Helper method to discriminate the union."""
    match count_positional_params(signature(validator)):
        case 2:
            return False
        case 3:
            return True
        case _:
            raise TypeError


@dataclass(frozen=True, slots=True)
class AttributeReferenceValidator:
    """An AfterValidator that can resolve a reference to a model attribute and pass it to the validator function.

    Using this with a reference to an attribute in the model it is defined may significantly impact performance.
    """

    func: AttrValidatorFunction
    attribute: AttributeReference

    def __get_pydantic_core_schema__(self, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        schema = handler(source_type)
        info_arg = is_info_validator(self.func)
        if info_arg:
            func = cast(GeneralAttrValidatorFunction, self.func)

            def wrapper(value: Any, info: ValidationInfo) -> Any:
                attribute_val = self.attribute.get_value(info)
                if attribute_val is None:
                    return value
                return func(value, attribute_val, info)

        else:
            func = cast(NoInfoAttrValidatorFunction, self.func)

            def wrapper(value: Any, info: ValidationInfo) -> Any:
                attribute_val = self.attribute.get_value(info)
                if attribute_val is None:
                    return value
                return func(value, attribute_val)

        return with_info_after_validator_function(wrapper, schema=schema)

    def needs_self(self, model_type: ModelType) -> bool:
        """Checks if the validator needs a reference to the current model in order to work fully."""
        if self.attribute.model == "self":
            return True
        else:
            return self.attribute.model == model_type


@dataclass
class AttributeReferenceMaker:
    """Helper class to easily create attribute references."""

    _attr_ref_maker_model: ModelReference

    def __getattr__(self, name: str, /) -> AttributeReference:
        return AttributeReference(self._attr_ref_maker_model, name)


SelfRef = AttributeReferenceMaker("self")
InstanceRef = AttributeReferenceMaker("instance")
SolutionRef = AttributeReferenceMaker("solution")


class InstanceSolutionModel(EncodableModelBase):
    """Base class for Instance and solution models."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type[BaseModel], handler: GetCoreSchemaHandler) -> CoreSchema:
        schema = handler(cls)
        try:
            model_type = "instance" if issubclass(cls, InstanceModel) else "solution"
        except NameError:
            return schema
        if cls._validate_with_self(model_type):

            def validate_with_self(input: object, validate: ValidatorFunctionWrapHandler, info: ValidationInfo) -> Self:
                self: Self = validate(input)
                if info.context is None or "self" not in info.context:
                    self = cast(
                        Self, cls.model_validate(input, context=(info.context or {}) | {"self": self, model_type: self})
                    )
                return self

            schema = with_info_wrap_validator_function(validate_with_self, schema)
        return schema

    @classmethod
    def _annotation_needs_self(cls, annotation: object, model_type: ModelType) -> bool:
        if isinstance(annotation, AttributeReferenceValidator):
            return annotation.needs_self(model_type)
        if isinstance(annotation, GroupedMetadata):
            return any(cls._annotation_needs_self(e, model_type) for e in annotation)
        return any(cls._annotation_needs_self(e, model_type) for e in get_args(annotation))

    @classmethod
    def _validate_with_self(cls, model_type: ModelType) -> bool:
        # info.annotation contains the type and any nested metadata, info.metadata the top level metadata
        # we can use _annotation_needs_self for all of them, so we iterate over all fields and see if any of them
        # either have an annotation or metadata we need to parse with a self reference
        for info in cls.model_fields.values():
            values = chain((info.annotation,), info.metadata)
            if any(cls._annotation_needs_self(value, model_type) for value in values):
                return True
        return False


class InstanceModel(InstanceSolutionModel, EncodableModel, Instance, ABC):
    """An instance that can easily be parsed to/from a json file."""

    pass


class SolutionModel(InstanceSolutionModel, Solution[InstanceT], ABC):
    """A solution that can easily be parsed to/from a json file."""

    @classmethod
    def decode(cls, source: Path, max_size: int, role: Role, instance: InstanceT) -> Self:
        """Uses pydantic to create a python object from a `.json` file."""
        context: dict[str, Any] = {"max_size": max_size, "role": role, "instance": instance}
        return cls._decode(cls, source, **context)
