"""A Battle is the portion of a match where a specific team generates instances and another one solves them.

This module contains the :class:`Battle` class, which speciefies how each type of battle is fought and scored,
some basic battle types, and related classed.
"""

from abc import abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.metadata import entry_points
from inspect import isclass
from itertools import count
from pathlib import Path
from types import EllipsisType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    Literal,
    ParamSpec,
    Protocol,
    Self,
    TypeAlias,
    TypeVar,
    Unpack,
    overload,
)

from annotated_types import Ge
from pydantic import (
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    SerializeAsAny,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
)
from pydantic_core import CoreSchema
from pydantic_core.core_schema import tagged_union_schema, with_info_wrap_validator_function
from typing_extensions import TypedDict

from algobattle.problem import InstanceModel, Problem, SolutionModel
from algobattle.program import (
    Generator,
    GeneratorResult,
    ProgramResult,
    ProgramUi,
    RunConfigOverride,
    Solver,
    SolverResult,
)
from algobattle.util import BaseModel, Encodable, EncodableModel, ExceptionInfo, Role

_BattleConfig: TypeAlias = Any
"""Type alias used to generate correct typings when subclassing :class:`Battle`.

Each battle type's :meth:`run` method is guaranteed to be passed an instance of its own :class:`BattleConfig` object.
But due to limitations in the python type system we are currently not able to express this properly.
When creating your own battle type it is recommended to not use this alias and instead use the :class:`BattleConfig` of
the new battle type directly.
"""
T = TypeVar("T")
P = ParamSpec("P")
_type = type


class ProgramLogConfigTime(StrEnum):
    """When to log a programs i/o."""

    never = "never"
    error = "error"
    always = "always"


class ProgramLogConfigLocation(StrEnum):
    """Where to log a programs i/o."""

    disabled = "disabled"
    inline = "inline"


class ProgramLogConfigView(Protocol):
    when: ProgramLogConfigTime = ProgramLogConfigTime.error
    output: ProgramLogConfigLocation = ProgramLogConfigLocation.inline


class ProgramRunInfo(BaseModel):
    """Data about a program's execution."""

    runtime: float = 0
    overriden: RunConfigOverride = Field(default_factory=RunConfigOverride, validate_default=True)
    error: ExceptionInfo | None = None
    battle_data: SerializeAsAny[EncodableModel] | None = None
    instance: SerializeAsAny[InstanceModel] | None = None
    solution: SerializeAsAny[SolutionModel[InstanceModel]] | None = None

    @classmethod
    def from_result(cls, result: ProgramResult, *, inline_output: bool) -> Self:
        """Converts the program run info into a jsonable model."""
        info = cls(
            runtime=result.runtime,
            overriden=result.overriden,
            error=result.error,
        )
        if inline_output:
            if isinstance(result.battle_data, EncodableModel):
                info.battle_data = result.battle_data
            if isinstance(result.solution, SolutionModel):
                info.solution = result.solution
            if isinstance(result, GeneratorResult) and isinstance(result.instance, InstanceModel):
                info.instance = result.instance
        return info


class Fight(BaseModel):
    """The result of one fight between the participating teams.

    For a more detailed description of what each fight looks like, see :meth:`FightHandler.run`.
    """

    score: float
    """The solving Team's score.

    Always a number in [0, 1]. 0 indicates a total failure of the solver, 1 that it succeeded perfectly.
    """
    max_size: int
    """The maximum size of an instance the generator was allowed to create."""
    generator: ProgramRunInfo
    """Data about the generator's execution."""
    solver: ProgramRunInfo | None
    """Data about the solver's execution."""

    @classmethod
    def from_results(
        cls,
        max_size: int,
        score: float,
        generator: GeneratorResult,
        solver: SolverResult | None,
        *,
        config: ProgramLogConfigView,
    ) -> Self:
        """Turns the involved result objects into a jsonable model."""
        inline_output = config.when == "always" or (
            config.when == "error"
            and (generator.error is not None or (solver is not None and solver.error is not None))
        )
        return cls(
            max_size=max_size,
            score=score,
            generator=ProgramRunInfo.from_result(generator, inline_output=inline_output),
            solver=ProgramRunInfo.from_result(solver, inline_output=inline_output) if solver is not None else None,
        )


class FightUi(ProgramUi, Protocol):
    """Provides an interface for :class:`Fight` to update the ui."""

    @abstractmethod
    def start_fight(self, max_size: int) -> None:
        """Informs the ui that a new fight has been started."""

    @abstractmethod
    def end_fight(self) -> None:
        """Informs the ui that the fight has finished running and has been added to the battle's `.fight_results`."""


class RunKwargs(TypedDict, total=False, closed=True):
    """The keyword arguments used by the FightHandler.run family of functions."""

    timeout_generator: float | None
    space_generator: int | None
    cpus_generator: int
    timeout_solver: float | None
    space_solver: int | None
    cpus_solver: int
    generator_battle_input: Encodable
    solver_battle_input: Encodable
    generator_battle_output: type[Encodable]
    solver_battle_output: type[Encodable]


@dataclass
class FightHandler:
    """Helper class to run fights of a given battle."""

    problem: Problem
    generator: Generator
    solver: Solver
    battle: "Battle"
    ui: FightUi
    set_cpus: str | None
    log_config: ProgramLogConfigView

    @overload
    async def run(
        self,
        max_size: int,
        *,
        with_results: Literal[False] = False,
        **kwargs: Unpack[RunKwargs],
    ) -> Fight: ...

    @overload
    async def run(
        self,
        max_size: int,
        *,
        with_results: Literal[True],
        **kwargs: Unpack[RunKwargs],
    ) -> tuple[Fight, GeneratorResult, SolverResult | None]: ...

    async def run(
        self,
        max_size: int,
        *,
        with_results: bool = False,
        **kwargs: Unpack[RunKwargs],
    ) -> Fight | tuple[Fight, GeneratorResult, SolverResult | None]:
        """Execute a single fight of a battle.

        First the generator will be run and its output parsed. Then the solver will be given the created instance
        and run. Its output gets parsed into a solution, which will then be scored.
        The timeout, space, and cpu arguments each override the corresponding match config options if set. Leaving them
        unset results in the config options being used.

        Args:
            max_size: The maximum instance size the generator is allowed to create.
            timeout_generator: Timeout in seconds for the generator to finish running. `None` means it is given an
                unlimited amount of time.
            space_generator: Memory space in MB the generator has access to. `None` means it is given an unlimited
                amount of space.
            cpus_generator: Number of physical cpu cores the generator can use.
            timeout_solver: Timeout in seconds for the solver to finish running. `None` means it is given an unlimited
                amount of time.
            space_solver: Memory space in MB the solver has access to. `None` means it is given
                an unlimited amount of space.
            cpus_solver: Number of physical cpu cores the solver can use.
            generator_battle_input: Additional data the generator will be provided with.
            solver_battle_input: Additional data the solver will be provided with.
            generator_battle_output: Class used to parse additional data the generator outputs into a python object.
            solver_battle_output: Class used to parse additional data the solver outputs into a python object.
            with_results: Whether to return the raw result objects.

        Returns:
            The resulting info about the executed fight, and the results if the flag has been set.
        """
        gen_result, sol_result = await self.run_raw(max_size=max_size, **kwargs)
        score = self.calculate_score(gen_result, sol_result)
        fight = Fight.from_results(
            score=score,
            max_size=max_size,
            generator=gen_result,
            solver=sol_result,
            config=self.log_config,
        )
        self.battle.fights.append(fight)
        self.ui.end_fight()
        if with_results:
            return fight, gen_result, sol_result
        else:
            return fight

    async def run_raw(
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
    ) -> tuple[GeneratorResult, SolverResult | None]:
        """Runs a fight and returns the unprocessed results."""
        min_size = self.problem.min_size
        if max_size < min_size:
            raise ValueError(
                f"Cannot run battle at size {max_size} since it is smaller than the smallest "
                f"size the problem allows ({min_size})."
            )
        ui = self.ui
        ui.start_fight(max_size)
        gen_result = await self.generator.run(
            max_size=max_size,
            timeout=timeout_generator,
            space=space_generator,
            cpus=cpus_generator,
            battle_input=generator_battle_input,
            battle_output=generator_battle_output,
            set_cpus=self.set_cpus,
            ui=ui,
        )
        if gen_result.error is not None:
            return gen_result, None
        assert gen_result.instance is not None

        sol_result = await self.solver.run(
            gen_result.instance,
            max_size=max_size,
            timeout=timeout_solver,
            space=space_solver,
            cpus=cpus_solver,
            battle_input=solver_battle_input,
            battle_output=solver_battle_output,
            set_cpus=self.set_cpus,
            ui=ui,
        )
        return gen_result, sol_result

    def calculate_score(self, gen_result: GeneratorResult, sol_result: SolverResult | None) -> float:
        """Calculates the score achieved by the solver in this fight.

        Both results need to contain all instance and/or solution data required.

        Args:
            gen_result: The generator's result.
            sol_result: The solver's result

        Returns:
            A number in [0, 1] with higher numbers meaning the solver performed better.
        """
        # We first need to check whether the generator somehow failed. This can happen in three cases:
        # it doesn't produce an instance, it creates an invalid instance or it doesn't create a needed solution
        # note that gen_result.instance and gen_result.error will both contain data if the generator outputted an
        # invalid instance and/or solution
        if (
            gen_result.instance is None
            or gen_result.error is not None
            or (self.problem.with_solution and gen_result.solution is None)
        ):
            return 1
        # sol_result is None only if the generator failed, which needs to be caught by the above check
        assert sol_result is not None
        # The solver failed if it didn't output a solution or the solution contains some error
        if sol_result.solution is None or sol_result.error is not None:
            return 0

        if self.problem.with_solution:
            # we need this assert since type checkers can't see the dependency between self.problem.with_solution
            # and gen_result.solution that is created by the last check in the first "if"
            assert gen_result.solution is not None
            score = self.problem.score(
                gen_result.instance, solver_solution=sol_result.solution, generator_solution=gen_result.solution
            )
        else:
            score = self.problem.score(gen_result.instance, solution=sol_result.solution)
        return max(0, min(1, float(score)))


# We need this to be here to prevent an import cycle between match.py and battle.py
class BattleUi(Protocol):
    """Provides an interface for :class:`Battle` to update the Ui."""

    @abstractmethod
    def update_battle_data(self, data: "Battle.UiData") -> None:
        """Passes new custom display data to the Ui.

        See :class:`Battle.UiData` for further details.
        """


class Battle(BaseModel):
    """Base for classes that execute a specific kind of battle.

    Each battle type determines what parameters each fight will be fought with, how many fights are fought, and how
    they will ultimately be scored.
    """

    fights: list[Fight] = Field(default_factory=list)
    """The list of fights that have been fought in this battle."""
    runtime_error: ExceptionInfo | None = None
    """The description of an otherwise unhandeled exception that occured during the execution of :meth:`Battle.run`."""

    _battle_types: ClassVar[dict[str, type[Self]]] = {}
    """Dictionary mapping the names of all registered battle types to their python classes."""

    class Config(BaseModel):
        """Config object for each specific battle type.

        A custom battle type can override this class to specify config options it uses. They will be parsed from a
        dictionary located at `battle` in the main config file. The created object will then be passed to the
        :meth:`Battle.run` method with its fields set accordingly.
        """

        type: Any
        """Type of battle that will be used."""

        @classmethod
        def __get_pydantic_core_schema__(cls, source: _type, handler: GetCoreSchemaHandler) -> CoreSchema:
            # there's two bugs we need to catch:
            # 1. this function is called during the pydantic BaseModel metaclass's __new__, so the BattleConfig class
            # won't be ready at that point and be missing in the namespace
            # 2. pydantic uses the core schema to build child classes core schema. for them we want to behave like a
            # normal model, only our own schema gets modified
            try:
                if cls != Battle.Config:
                    return handler(source)
            except NameError:
                return handler(source)

            match len(Battle._battle_types):
                case 0:
                    subclass_schema = handler(source)
                case 1:
                    subclass_schema = handler(next(iter(Battle._battle_types.values())))
                case _:
                    subclass_schema = tagged_union_schema(
                        choices={
                            battle.Config.model_fields["type"].default: battle.Config.__pydantic_core_schema__
                            for battle in Battle._battle_types.values()
                        },
                        discriminator="type",
                    )

            # we want to validate into the actual battle type's config, so we need to treat them as a tagged union
            # but if we're initializing a project the type might not be installed yet, so we want to also parse
            # into an unspecified dummy object. This wrap validator will efficiently and transparently act as a tagged
            # union when ignore_uninstalled is not set. If it is set it catches only the error of a missing tag, other
            # errors are passed through
            def check_installed(val: object, handler: ValidatorFunctionWrapHandler, info: ValidationInfo) -> object:
                try:
                    return handler(val)
                except ValidationError as e:
                    union_err = next(filter(lambda err: err["type"] == "union_tag_invalid", e.errors()), None)
                    if union_err is None:
                        raise
                    if info.context is not None and info.context.get("ignore_uninstalled", False):
                        if info.config is not None:
                            settings: dict[str, Any] = {
                                "strict": info.config.get("strict", None),
                                "from_attributes": info.config.get("from_attributes"),
                            }
                        else:
                            settings = {}
                        return Battle.FallbackConfig.model_validate(val, context=info.context, **settings)
                    else:
                        passed = union_err["input"]["type"]
                        installed = ", ".join(b.name() for b in Battle._battle_types.values())
                        raise ValueError(
                            f"The specified battle type '{passed}' is not installed. Installed types are: {installed}"
                        ) from e

            return with_info_wrap_validator_function(check_installed, subclass_schema)

    class FallbackConfig(Config):
        """Fallback config object to parse into if the proper battle typ isn't installed and we're ignoring installs."""

        type: str

        model_config = ConfigDict(extra="allow")

        if TYPE_CHECKING:
            # to hint that we're gonna fill this with arbitrary data belonging to some supposed battle type
            def __getattr__(self, attr: str, /) -> Any: ...

    class UiData(BaseModel):
        """Object containing custom diplay data.

        The display data object will be displayed as key-value pairs generated from the :meth:`.field` method.
        You can use the normally available pydantic config options to customize what these will look like.
        """

    @staticmethod
    def all() -> dict[str, type["Battle"]]:
        """Returns a dictionary mapping the names of all registered battle types to their python classes.

        It includes all subclasses of :class:`Battle` that have been initialized so far, including ones exposed to the
        algobattle module via the `algobattle.battle` entrypoint hook.
        """
        return Battle._battle_types

    @classmethod
    def load_entrypoints(cls) -> None:
        """Loads all battle types presented via entrypoints."""
        for entrypoint in entry_points(group="algobattle.battle"):
            battle = entrypoint.load()
            if not (isclass(battle) and issubclass(battle, Battle)):
                raise ValueError(f"Entrypoint {entrypoint.name} targets something other than a Battle type")

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        if cls.name() not in Battle._battle_types:
            Battle._battle_types[cls.name()] = cls
            Battle.Config.model_rebuild(force=True)
        return super().__pydantic_init_subclass__(**kwargs)

    @abstractmethod
    def score(self, config: _BattleConfig) -> float:
        """Calculates the score the solver has achieved during this battle.

        Should always be a nonnegative float, with higher values indicating a better performance of the solver.
        """
        raise NotImplementedError

    @staticmethod
    def format_score(score: float) -> str:
        """Formats a given score nicely.

        Purely auxialiary method that can be used to customize how a score will be rendered.
        """
        return f"{score:.2f}"

    @classmethod
    def name(cls) -> str:
        """Name of this battle type.

        Defaults to the battle class's name. Can be used to customize this behaviour if e.g. a battle type should have a
        name that is not a valid python identifier.
        """
        return cls.__name__

    @abstractmethod
    async def run_battle(self, fight: FightHandler, config: _BattleConfig, min_size: int, ui: BattleUi) -> None:
        """Executes one battle.

        Args:
            fight: The :class:`FightHandler` used to run each fight of this battle. It already contains information
                about the participating teams, default config settings, etc. Each fight can be executed using the
                :meth:`FightHandler.run` method.
            config: An instance of this battle type's :class:`BattleConfig` class, parsed from the corresponding section
                of the config file.
            min_size: The minimum size valid for this problem.
            ui: An interface to interact with the ui.
        """
        raise NotImplementedError


class Iterated(Battle):
    """Class that executes an iterated battle."""

    results: list[int] = Field(default_factory=list)

    class Config(Battle.Config):
        """Config options for Iterated battles."""

        type: Literal["Iterated"] = "Iterated"

        rounds: int = 3
        """Number of times the instance size will be increased until the solver fails to produce correct solutions."""
        maximum_size: int = 50_000
        """Maximum instance size that will be tried."""
        exponent: int = 2
        """Determines how quickly the instance size grows."""
        minimum_score: float = 1
        """Minimum score that a solver needs to achieve in order to pass."""
        max_generator_errors: int | Literal["unlimited"] = 5
        """If a generator fails to produce a valid instance, the solver wins the fight by default.

        This may create very lengthy battles where the generator keeps failing at higher and higher `max_size`s. You
        can use this setting to early exit and award the solver the full score if this happens. Set to an integer to
        exit after that many failures, or `"unlimited"` to never exit early.
        """

    class UiData(Battle.UiData):
        reached: list[int]
        cap: int
        note: str

    async def run_battle(self, fight: FightHandler, config: Config, min_size: int, ui: BattleUi) -> None:
        """Execute an iterated battle.

        Incrementally tries to search for the highest n for which the solver is still able to solve instances.
        The base increment value is multiplied with the number of iterations since the last unsolvable instance to the
        given exponent. Only once the solver fails directly after the multiplier is reset, it counts as failed. Since
        this would heavily favour probabilistic algorithms (That may have only failed by chance and are able to solve a
        certain instance size on a second try), we cap the maximum solution size by the last value that an algorithm
        has failed on. If the solver never stops, the battle will run until the instance size reaches `iteration_cap`.

        This process is repeated `rounds` many times, with each round being completely independent of each other.
        """

        def sizes(size: int, max_size: int) -> Iterable[int]:
            if size > max_size:
                return
            counter = count(1)
            while size < max_size:
                yield size
                size += next(counter) ** config.exponent
            yield max_size

        note = "Starting battle..."
        for _i in range(config.rounds):
            lower_bound = min_size
            upper_bound = config.maximum_size
            self.results.append(0)
            gen_errors = 0
            while lower_bound <= upper_bound:
                lower_bound = max(lower_bound, self.results[-1] + 1)
                for size in sizes(lower_bound, upper_bound):
                    ui.update_battle_data(self.UiData(reached=self.results, cap=upper_bound, note=note))
                    result = await fight.run(size)
                    if result.generator.error and config.max_generator_errors != "unlimited":
                        gen_errors += 1
                        if gen_errors >= config.max_generator_errors:
                            self.results[-1] = upper_bound
                            note = f"Generator failed {gen_errors} times in a row, solver wins round by default!"
                            break
                    else:
                        gen_errors = 0
                    if result.score < config.minimum_score:
                        upper_bound = size - 1
                        note = "Solver didn't achieve the needed score, resetting the cap"
                        break
                    else:
                        note = "Solver was successful, increasing the cap"
                        self.results[-1] = size
            note = "Cap reached, resetting instance size"

    def score(self, config: Config) -> float:
        """Averages the highest instance size reached in each round."""
        return 0 if len(self.results) == 0 else sum(self.results) / len(self.results)

    @staticmethod
    def format_score(score: float) -> str:
        return str(int(score))


class Averaged(Battle):
    """Class that executes an averaged battle."""

    class Config(Battle.Config):
        """Config options for Averaged battles."""

        type: Literal["Averaged"] = "Averaged"

        instance_size: int = 25
        """Instance size that will be fought at."""
        num_fights: int = 10
        """Number of iterations in each round."""

    class UiData(Battle.UiData):
        round: int

    async def run_battle(self, fight: FightHandler, config: Config, min_size: int, ui: BattleUi) -> None:
        """Execute an averaged battle.

        This simple battle type just executes `iterations` many fights after each other at size `instance_size`.
        """
        if config.instance_size < min_size:
            raise ValueError(f"size {config.instance_size} is smaller than the smallest valid size, {min_size}.")
        for i in range(config.num_fights):
            ui.update_battle_data(self.UiData(round=i + 1))
            await fight.run(config.instance_size)

    def score(self, config: Config) -> float:
        """Averages the score of each fight."""
        if len(self.fights) == 0:
            return 0
        else:
            return sum(f.score for f in self.fights) / len(self.fights)

    @staticmethod
    def format_score(score: float) -> str:
        return format(score, ".0%")


@dataclass
class FightHistory(Encodable):
    """A dictionary that can be encoded/decoded with each encodable being placed at the location its key specifies."""

    @dataclass
    class Fight:
        """The full data of a single fight."""

        score: float
        generator: GeneratorResult
        solver: SolverResult | None

    history: list[Fight] = field(default_factory=list, init=False)
    scores: set[Role]
    instances: set[Role]
    gen_sols: set[Role]
    sol_sols: set[Role]

    def encode(self, target: Path, role: Role) -> None:
        target.mkdir()
        for i, fight in enumerate(self.history):
            fight_dir = target / str(i)
            fight_dir.mkdir()
            if role in self.scores:
                fight_dir.joinpath("score.txt").write_text(str(fight.score))
            if fight.generator.instance and role in self.instances:
                fight.generator.instance.encode(fight_dir / "instance", role)
            if fight.generator.solution and role in self.gen_sols:
                fight.generator.solution.encode(fight_dir / "generator_solution", role)
            if fight.solver and fight.solver.solution and role in self.sol_sols:
                fight.solver.solution.encode(fight_dir / "solver_solution", role)

    @classmethod
    def decode(cls, source: Path, max_size: int, role: Role) -> Self:
        """We cannot decode this since we don't know the type of each instance/solution."""
        raise NotImplementedError


class Improving(Battle):
    """Class that executes an improving battle."""

    class Config(Battle.Config):
        """Config options for Improving battles."""

        type: Literal["Improving"] = "Improving"

        instance_size: int = 25
        """Instance size that will be fought at."""
        num_fights: int = 20
        """Number of fights that will be fought."""
        weighting: Annotated[float, Ge(0)] = 1.1
        """How much each successive fight should be weighted more than the previous."""
        scores: set[Role] = {Role.generator, Role.solver}  # noqa: RUF012
        """Who to show each fight's scores to."""
        instances: set[Role] = {Role.generator, Role.solver}  # noqa: RUF012
        """Who to show the instances to."""
        generator_solutions: set[Role] = {Role.generator}  # noqa: RUF012
        """Who to show the generator's solutions to, if the problem requires them."""
        solver_solutions: set[Role] = {Role.solver}  # noqa: RUF012
        """Who to show the solver's solutions to."""

    class UiData(Battle.UiData):
        round: int

    async def run_battle(self, fight: FightHandler, config: Config, min_size: int, ui: BattleUi) -> None:
        """Execute an improving battle.

        This simple battle type just executes `iterations` many fights after each other at size `instance_size`.
        """
        if config.instance_size < min_size:
            raise ValueError(f"size {config.instance_size} is smaller than the smallest valid size, {min_size}.")
        history = FightHistory(
            scores=config.scores,
            instances=config.instances,
            gen_sols=config.generator_solutions,
            sol_sols=config.solver_solutions,
        )
        for i in range(config.num_fights):
            ui.update_battle_data(self.UiData(round=i + 1))
            plain_fight, gen, sol = await fight.run(
                config.instance_size,
                generator_battle_input=history,
                solver_battle_input=history,
                with_results=True,
            )
            history.history.append(FightHistory.Fight(plain_fight.score, gen, sol))

    def score(self, config: Config) -> float:
        """Averages the score of each fight."""
        if len(self.fights) == 0:
            return 0
        else:
            total = sum(f.score * config.weighting**i for (i, f) in enumerate(self.fights))
            quotient = (1 - config.weighting ** len(self.fights)) / (1 - config.weighting)
            return total / quotient

    @staticmethod
    def format_score(score: float) -> str:
        return format(score, ".0%")
