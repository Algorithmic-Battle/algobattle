"""Module providing an interface to interact with the teams' programs."""

import json
from abc import ABC, abstractmethod
from collections.abc import Generator as PyGenerator, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import combinations
from os import environ
from pathlib import Path
from tarfile import TarFile, is_tarfile
from tempfile import TemporaryDirectory
from timeit import default_timer
from types import EllipsisType, TracebackType
from typing import Any, ClassVar, Protocol, Self, TypeVar, cast
from uuid import uuid4
from zipfile import ZipFile, is_zipfile

from anyio import run as run_async
from anyio.to_thread import run_sync
from docker import DockerClient
from docker.errors import APIError, BuildError as DockerBuildError, DockerException, ImageNotFound
from docker.models.containers import Container as DockerContainer
from docker.models.images import Image as DockerImage
from docker.types import Mount
from requests import ConnectionError, Timeout
from typing_extensions import TypedDict
from urllib3.exceptions import ReadTimeoutError

from algobattle.problem import Instance, Problem, Solution
from algobattle.util import (
    BuildError,
    DockerError,
    DockerNotRunning,
    Encodable,
    EncodingError,
    ExceptionInfo,
    ExecutionError,
    ExecutionTimeout,
    Role,
    TempDir,
    ValidationError,
)

_client_var: DockerClient | None = None


T = TypeVar("T")


def client() -> DockerClient:
    """Returns the docker api client, checking that it's still responsive."""
    global _client_var
    try:
        if _client_var is None:
            _client_var = DockerClient.from_env()
        else:
            _client_var.ping()
    except (DockerException, APIError) as e:
        raise DockerNotRunning from e
    return _client_var


class RunConfigOverride(TypedDict, total=False):
    """Run parameters that were overriden by the battle type."""

    timeout: float | None
    space: int | None
    cpus: int


@dataclass(frozen=True, slots=True)
class RunSpecs:
    """Actual specification of a program run."""

    timeout: float | None
    space: int | None
    cpus: int
    overriden: RunConfigOverride


class RunConfigView(Protocol):
    """Config view for single runs."""

    timeout: float | None
    space: int | None
    cpus: int


@dataclass(frozen=True, slots=True)
class ProgramConfigView:
    """Config settings relevant to the program module."""

    build_timeout: float | None
    max_program_size: int | None
    strict_timeouts: bool
    build_kwargs: dict[str, Any]
    run_kwargs: dict[str, Any]
    generator: RunConfigView
    solver: RunConfigView
    name_images: bool
    cleanup_images: bool


class ProgramUi(Protocol):
    """Provides an interface for :class:`Program` to update the Ui."""

    @abstractmethod
    def start_program(self, role: Role, timeout: float | None) -> None:
        """Signals that the program execution has been started."""

    @abstractmethod
    def stop_program(self, role: Role, runtime: float) -> None:
        """Signals that the program execution has been finished."""


class ProgramIO:
    """Manages the directories used to pass IO to programs.

    Normally we can just create temporary directories using the python stdlib, but when running inside a container we
    need to use a directory thats bound to one on the host machine.
    """

    host_dir: ClassVar[Path | None] = Path(environ["ALGOBATTLE_IO_DIR"]) if "ALGOBATTLE_IO_DIR" in environ else None
    parent_dir: ClassVar[Path | None] = Path("/algobattle/io") if "ALGOBATTLE_IO_DIR" in environ else None

    def __init__(self) -> None:
        """Creates the needed temporary directories."""
        super().__init__()
        self._input = TemporaryDirectory(dir=self.parent_dir)
        self._output = TemporaryDirectory(dir=self.parent_dir)

    @property
    def input(self) -> Path:
        """Path to the input directory."""
        return Path(self._input.name)

    @property
    def output(self) -> Path:
        """Path to the output directoy."""
        return Path(self._output.name)

    @property
    def mounts(self) -> list[Mount]:
        """A list of Mounts corresponding to these IO directories that can be passed to the docker api."""
        if self.host_dir:
            host_input = self.host_dir / self.input.name
            host_output = self.host_dir / self.output.name
        else:
            host_input = self.input
            host_output = self.output
        return [
            Mount(target="/input", source=str(host_input), type="bind", read_only=True),
            Mount(target="/output", source=str(host_output), type="bind"),
        ]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc: type[BaseException] | None, val: BaseException | None, tb: TracebackType | None):
        self._input.__exit__(exc, val, tb)
        self._output.__exit__(exc, val, tb)


@dataclass(frozen=True)
class SolverResult:
    """The result of a solver execution."""

    runtime: float = 0
    overriden: RunConfigOverride = field(default_factory=RunConfigOverride)
    error: ExceptionInfo | None = None
    battle_data: Encodable | None = None
    solution: Solution[Instance] | None = None


@dataclass(frozen=True)
class GeneratorResult(SolverResult):
    """The result of a generator execution."""

    instance: Instance | None = None


ProgramResult = GeneratorResult | SolverResult


@dataclass
class _WrappedException(Exception):
    """Wraps an inner exception such that we can recover the runtime from outer methods easily."""

    inner: Exception
    runtime: float


@dataclass(frozen=True)
class Program(ABC):
    """A higher level interface for a team's programs."""

    id: str
    """The id of the Docker image."""
    problem: Problem
    """The problem this program generates/solves."""
    config: ProgramConfigView
    """Config settings used for this program."""

    role: ClassVar[Role]
    """Role of this program."""

    @classmethod
    @contextmanager
    def _setup_docker_env(cls, source: Path) -> PyGenerator[tuple[Path, str | None], None, None]:
        """Creates a folder containing the actual docker environment used to build a program."""
        if not source.exists():
            raise ValueError
        if source.is_dir():
            yield source, None
            return
        if source.name == "Dockerfile" or source.suffix == ".dockerfile":
            yield source.parent, source.name
            return

        with TempDir() as build_folder:
            if is_zipfile(source):
                with ZipFile(source, "r") as f:
                    f.extractall(build_folder)
            elif is_tarfile(source):
                with TarFile(source, "r") as f:
                    f.extractall(build_folder)
            else:
                raise ValueError(f"The file {source} is not recognisable as a dockerfile.")

            yield build_folder, None

    @classmethod
    async def build(
        cls,
        path: Path,
        *,
        problem: Problem,
        config: ProgramConfigView,
        team_name: str | None = None,
    ) -> Self:
        """Creates a program by building the specified docker image.

        Args:
            path: Path to a Dockerfile (or folder containing one) from which to build the image.
            problem: The problem this program generates/solves.
            config: Settings for this program.
            team_name: If set the image will be given a descriptive name.

        Returns:
            The built Program.

        Raises:
            BuildError: If the build fails for any reason.
        """
        if team_name is not None and config.name_images:
            normalized = team_name.lower().replace(" ", "_")
            name = f"algobattle_{normalized}_{cls.role.name}"
            try:
                old_image = client().images.get(name)
            except ImageNotFound:
                old_image = None
        else:
            name = None
            old_image = None

        with cls._setup_docker_env(path) as (path, dockerfile):
            try:
                image = await run_sync(
                    cls._build_daemon_call,
                    str(path),
                    name,
                    config.build_timeout,
                    dockerfile,
                    config.build_kwargs,
                    cancellable=True,
                )
                if old_image is not None:
                    old_image.reload()
                    if len(old_image.tags) == 0:
                        old_image.remove(force=True)

            except Timeout as e:
                raise BuildError("Build ran into a timeout.") from e
            except DockerBuildError as e:
                logs = cast(list[dict[str, Any]], list(e.build_log))
                raise BuildError("Build did not complete successfully.", detail=logs) from e
            except APIError as e:
                raise BuildError("Docker APIError thrown while building.", detail=str(e)) from e

        self = cls(
            cast(str, image.id),
            problem=problem,
            config=config,
        )
        used_size = image.attrs.get("Size", 0)
        if config.max_program_size is not None and used_size > config.max_program_size:
            try:
                self.remove()
            finally:
                raise BuildError(
                    "Built image is too large.", detail=f"Size: {used_size}B, limit: {config.max_program_size}B."
                )
        return self

    @classmethod
    def _build_daemon_call(
        cls, path: str, tag: str | None, timeout: float | None, dockerfile: str | None, build_kwargs: dict[str, Any]
    ) -> DockerImage:
        image, _logs = cast(
            tuple[DockerImage, Iterator[Any]],
            client().images.build(
                path=str(path),
                tag=tag,
                timeout=timeout, # type: ignore
                dockerfile=dockerfile,
                **build_kwargs,
            ),
        )
        return image

    def run_specs(
        self,
        timeout: float | None | EllipsisType,
        space: int | None | EllipsisType,
        cpus: int | EllipsisType,
    ) -> RunSpecs:
        """Merges the overriden config options with the parsed ones."""
        overriden = RunConfigOverride()
        match self.role:
            case Role.generator:
                config = self.config.generator
            case Role.solver:
                config = self.config.solver
        if timeout is ...:
            timeout = config.timeout
        else:
            overriden["timeout"] = timeout
        if space is ...:
            space = config.space
        else:
            overriden["space"] = space
        if cpus is ...:
            cpus = config.cpus
        else:
            overriden["cpus"] = cpus
        return RunSpecs(timeout=timeout, space=space, cpus=cpus, overriden=overriden)

    async def _run_inner(
        self,
        *,
        io: ProgramIO,
        max_size: int,
        specs: RunSpecs,
        battle_input: Encodable | None,
        battle_output: type[Encodable] | None,
        set_cpus: str | None,
        ui: ProgramUi | None,
    ) -> tuple[float, Encodable | None]:
        """Encodes the metadata, runs the docker container, and decodes battle metadata."""
        io.input.joinpath("info.json").write_text(
            json.dumps(
                {
                    "max_size": max_size,
                    "timeout": specs.timeout,
                    "space": specs.space,
                    "cpus": specs.cpus,
                },
            )
        )
        if battle_input is not None:
            try:
                battle_input.encode(io.input / "battle_data", self.role)
            except Exception as e:
                raise EncodingError("Battle data couldn't be encoded.", detail=str(e)) from e

        runtime = 0
        try:
            container = client().containers.create(
                image=self.id,
                name=f"algobattle_{uuid4().hex[:8]}",
                mem_limit=specs.space,
                nano_cpus=specs.cpus * 1_000_000_000,
                detach=True,
                mounts=io.mounts if io else None,
                cpuset_cpus=set_cpus,
                **self.config.run_kwargs,
            )

            if ui is not None:
                ui.start_program(self.role, specs.timeout)
            try:
                runtime = await run_sync(self._run_daemon_call, container, specs.timeout, cancellable=True)
            except ExecutionError as e:
                raise _WrappedException(e, e.runtime) from e
            finally:
                container.remove(force=True)
                if ui is not None:
                    ui.stop_program(self.role, runtime)
        except APIError as e:
            raise _WrappedException(
                DockerError("Docker APIError thrown while running container.", detail=str(e)), runtime
            ) from e

        if battle_output:
            try:
                decoded_battle_output = battle_output.decode(io.output / "battle_data", max_size, self.role)
            except Exception as e:
                raise _WrappedException(e, runtime) from e
        else:
            decoded_battle_output = None
        return runtime, decoded_battle_output

    def _run_daemon_call(self, container: DockerContainer, timeout: float | None = None) -> float:
        """Runs the container.

        Returns:
            The container runtime
        Raises:
            ExecutionTimeout: When the container runs into the timeout.
            ExecutionError: When the process inside the container crashes.
            DockerException: When the daeomon raises some other error.
        """
        # this method has to be a thicker wrapper since we have to kill the container asap, not just when the
        # async manager gives us back control.
        container.start()
        start_time = default_timer()
        elapsed_time = 0
        try:
            response = cast(dict[str, Any], container.wait(timeout=timeout))
            elapsed_time = round(default_timer() - start_time, 2)
            if response["StatusCode"] == 0:
                return elapsed_time
            else:
                raise ExecutionError(
                    "The program executed in the container crashed.",
                    detail=f"exit code: {response['StatusCode']}, error message:\n{container.logs().decode()}",
                    runtime=elapsed_time,
                )
        except (Timeout, ConnectionError) as e:
            container.kill()
            elapsed_time = round(default_timer() - start_time, 2)
            if len(e.args) != 1 or not isinstance(e.args[0], ReadTimeoutError):
                raise
            if self.config.strict_timeouts:
                raise ExecutionTimeout("The docker container exceeded the time limit.", runtime=elapsed_time) from e
            return elapsed_time

    def remove(self) -> None:
        """Removes the image from the docker daemon.

        **This will not cause the python object to be deleted.**
        Attempting to run the image after it has been removed will cause runtime errors.
        Will not throw an error if the image has been removed already.

        Raises:
            DockerError: When removing the image fails.
        """
        try:
            client().images.remove(image=self.id, force=True)
        except ImageNotFound:
            pass
        except APIError as e:
            raise DockerError("Docker APIError thrown while removing image.", detail=str(e)) from e

    def __enter__(self):
        return self

    def __exit__(self, *args: object):
        if self.config.cleanup_images:
            self.remove()


class Generator(Program):
    """A higher level interface for a team's generator."""

    role: ClassVar[Role] = Role.generator

    async def run(
        self,
        max_size: int,
        *,
        timeout: float | None | EllipsisType = ...,
        space: int | None | EllipsisType = ...,
        cpus: int | EllipsisType = ...,
        battle_input: Encodable | None = None,
        battle_output: type[Encodable] | None = None,
        ui: ProgramUi | None = None,
        set_cpus: str | None = None,
    ) -> GeneratorResult:
        """Executes the generator and parses its output into a problem instance.

        Args:
            max_size: Maximum size of the instance that the generator is allowed to generate.
            timeout: Timeout for the program in seconds.
            space: Maximum amount of memory space this program can use in bytes.
            cpus: Number of cpu cores this program can use.
            battle_input: Additional data that will be given to the generator.
            battle_output: Class that will be used to parse additional data the generator outputs.
            ui: Interface the program execution uses to update the ui.
            set_cpus: A docker format string specifying what cpu cores the program should use, or None for any cores.

        Returns:
            Datastructure containing all info about the generator execution and the created problem instance.
        """
        specs = self.run_specs(timeout, space, cpus)
        runtime = 0
        battle_data = None
        instance = None
        solution = None
        exception_info = None
        with ProgramIO() as io:
            try:
                io.input.joinpath("max_size.txt").write_text(str(max_size))
                runtime, battle_data = await self._run_inner(
                    io=io,
                    max_size=max_size,
                    specs=specs,
                    battle_input=battle_input,
                    battle_output=battle_output,
                    ui=ui,
                    set_cpus=set_cpus,
                )

                try:
                    instance = self.problem.instance_cls.decode(io.output / "instance", max_size, self.role)
                except EncodingError:
                    raise
                except Exception as e:
                    raise EncodingError(
                        "Unknown error thrown while decoding the problem instance.", detail=str(e)
                    ) from e
                try:
                    instance.validate_instance()
                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError("Unknown error thrown during instance validation.", detail=str(e)) from e
                if instance.size > max_size:
                    raise ValidationError(  # noqa: TRY301
                        "Instance is too large.", detail=f"Generated: {instance.size}, maximum: {max_size}"
                    )
                if self.problem.with_solution:
                    try:
                        solution = self.problem.solution_cls.decode(
                            io.output / "solution", max_size, self.role, instance
                        )
                    except EncodingError:
                        raise
                    except Exception as e:
                        raise EncodingError("Unknown error thrown while decoding the solution.", detail=str(e)) from e
                    try:
                        solution.validate_solution(instance, Role.generator)
                    except ValidationError:
                        raise
                    except Exception as e:
                        raise ValidationError("Unknown error thrown during solution validation.", detail=str(e)) from e

            except _WrappedException as e:
                runtime = e.runtime
                exception_info = ExceptionInfo.from_exception(e.inner)
            except Exception as e:
                exception_info = ExceptionInfo.from_exception(e)
            return GeneratorResult(
                runtime=runtime,
                overriden=specs.overriden,
                error=exception_info,
                battle_data=battle_data,
                instance=instance,
                solution=solution,
            )

    def test(self, max_size: int | None = None) -> Instance | ExceptionInfo:
        """Tests whether the generator runs without issues and creates a syntactically valid instance."""
        res = run_async(self.run, max_size or self.problem.min_size)
        if res.error:
            return res.error
        else:
            assert res.instance is not None
            return res.instance


class Solver(Program):
    """A higher level interface for a team's solver."""

    role: ClassVar[Role] = Role.solver

    async def run(
        self,
        instance: Instance,
        max_size: int,
        *,
        timeout: float | None | EllipsisType = ...,
        space: int | None | EllipsisType = ...,
        cpus: int | EllipsisType = ...,
        battle_input: Encodable | None = None,
        battle_output: type[Encodable] | None = None,
        ui: ProgramUi | None = None,
        set_cpus: str | None = None,
    ) -> SolverResult:
        """Executes the solver on the given problem instance and parses its output into a problem solution.

        Args:
            max_size: Maximum size of the instance that the generator is allowed to generate.
            timeout: Timeout for the program in seconds.
            space: Maximum amount of memory space this program can use in bytes.
            cpus: Number of cpu cores this program can use.
            battle_input: Additional data that will be given to the solver.
            battle_output: Class that will be used to parse additional data the solver outputs.
            ui: Interface the program execution uses to update the ui.
            set_cpus: A docker format string specifying what cpu cores the program should use, or None for any cores.

        Returns:
            Datastructure containing all info about the solver execution and the solution it computed.
        """
        specs = self.run_specs(timeout, space, cpus)
        runtime = 0
        battle_data = None
        solution = None
        exception_info = None
        with ProgramIO() as io:
            try:
                instance.encode(io.input / "instance", self.role)
                runtime, battle_data = await self._run_inner(
                    io=io,
                    max_size=max_size,
                    specs=specs,
                    battle_input=battle_input,
                    battle_output=battle_output,
                    ui=ui,
                    set_cpus=set_cpus,
                )
                try:
                    solution = self.problem.solution_cls.decode(io.output / "solution", max_size, self.role, instance)
                except EncodingError:
                    raise
                except Exception as e:
                    raise EncodingError("Unexpected error thrown while decoding the solution.", detail=str(e)) from e
                try:
                    solution.validate_solution(instance, Role.solver)
                except ValidationError:
                    raise
                except Exception as e:
                    raise ValidationError("Unexpected error during solution validation.", detail=str(e)) from e

            except _WrappedException as e:
                runtime = e.runtime
                exception_info = ExceptionInfo.from_exception(e.inner)
            except Exception as e:
                exception_info = ExceptionInfo.from_exception(e)
            return SolverResult(
                runtime=runtime,
                overriden=specs.overriden,
                error=exception_info,
                battle_data=battle_data,
                solution=solution,
            )

    def test(self, instance: Instance) -> ExceptionInfo | None:
        """Tests whether the solver runs without issues and creates a syntactically valid solution."""
        res = run_async(self.run, instance, instance.size)
        if res.error:
            return res.error
        else:
            return None


class BuildUi(Protocol):
    """Provides and interface for the build process to update the ui."""

    @abstractmethod
    def start_build_step(self, teams: Iterable[str], timeout: float | None) -> None:
        """Tells the ui that the build process has started."""

    @abstractmethod
    def start_build(self, team: str, role: Role) -> None:
        """Informs the ui that a new program is being built."""

    @abstractmethod
    def finish_build(self, team: str, success: bool) -> None:
        """Informs the ui that the current build has been finished."""


class _TeamInfo(Protocol):
    generator: Path
    solver: Path


@dataclass(frozen=True, slots=True)
class Team:
    """Class bundling together the programs of a team."""

    name: str
    generator: Generator
    solver: Solver

    @classmethod
    async def build(
        cls,
        name: str,
        info: _TeamInfo,
        problem: Problem,
        config: ProgramConfigView,
        ui: BuildUi,
    ) -> "Team":
        """Builds the specified docker files into images and return the corresponding team.

        Args:
            name: Name of the team.
            info: Team info containing the paths to the program data.
            problem: The problem class the current match is fought over.
            config: Config for the programs.

        Returns:
            The built team.

        Raises:
            ValueError: If the team name is already in use.
            DockerError: If the docker build fails for some reason
        """
        ui.start_build(name, Role.generator)
        generator = await Generator.build(
            path=info.generator,
            problem=problem,
            config=config,
            team_name=name,
        )
        try:
            ui.start_build(name, Role.solver)
            solver = await Solver.build(
                path=info.solver,
                problem=problem,
                config=config,
                team_name=name,
            )
        except Exception:
            if config.cleanup_images:
                generator.remove()
            raise
        return Team(name, generator, solver)

    def __str__(self) -> str:
        return self.name

    def __eq__(self, o: object) -> bool:
        if isinstance(o, Team):
            return self.name == o.name
        else:
            return False

    def __hash__(self) -> int:
        return hash(self.name)

    def __enter__(self) -> Self:
        self.generator.__enter__()
        self.solver.__enter__()
        return self

    def __exit__(self, *args: object):
        self.generator.__exit__(*args)
        self.solver.__exit__(*args)

    def cleanup(self) -> None:
        """Removes the built docker images."""
        self.generator.remove()
        self.solver.remove()


@dataclass(frozen=True)
class Matchup:
    """Represents an individual matchup of teams."""

    generator: Team
    solver: Team

    def __iter__(self) -> Iterator[Team]:
        yield self.generator
        yield self.solver

    def __repr__(self) -> str:
        return f"Matchup({self.generator.name}, {self.solver.name})"

    def __str__(self) -> str:
        return f"{self.generator.name} vs {self.solver.name}"


@dataclass
class TeamHandler:
    """Handles building teams and cleaning them up."""

    active: list[Team] = field(default_factory=list)
    excluded: dict[str, ExceptionInfo] = field(default_factory=dict)

    @classmethod
    async def build(
        cls,
        infos: Mapping[str, _TeamInfo],
        problem: Problem,
        config: ProgramConfigView,
        ui: BuildUi,
    ) -> Self:
        """Builds the programs of every team.

        Attempts to build the programs of every team. If any build fails, that team will be excluded and all its
        programs cleaned up.

        Args:
            infos: Teams that participate in the match.
            problem: Problem class that the match will be fought with.
            config: Config options.

        Returns:
            :class:`TeamHandler` containing the info about the participating teams.
        """
        handler = cls()
        ui.start_build_step(infos.keys(), config.build_timeout)
        for name, info in infos.items():
            try:
                team = await Team.build(name, info, problem, config, ui)
                handler.active.append(team)
            except Exception as e:
                handler.excluded[name] = ExceptionInfo.from_exception(e)
                ui.finish_build(name, False)
            else:
                ui.finish_build(name, True)
        return handler

    def __enter__(self) -> Self:
        for team in self.active:
            team.__enter__()
        return self

    def __exit__(self, *args: object):
        for team in self.active:
            team.__exit__(*args)

    @property
    def grouped_matchups(self) -> list[tuple[Matchup, Matchup]]:
        """All matchups, grouped by the involved teams.

        Each tuple's first matchup has the first team in the group generating, the second has it solving.
        """
        return [(Matchup(*g), Matchup(*g[::-1])) for g in combinations(self.active, 2)]

    @property
    def matchups(self) -> list[Matchup]:
        """All matchups that will be fought."""
        if len(self.active) == 1:
            return [Matchup(self.active[0], self.active[0])]
        else:
            return [m for pair in self.grouped_matchups for m in pair]
