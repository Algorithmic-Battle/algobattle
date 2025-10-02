"""Module defining how a match is run."""

import tomllib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property
from itertools import combinations
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, Protocol, Self, TypeAlias, TypeVar, cast

from anyio import CapacityLimiter, create_task_group
from anyio.to_thread import current_default_thread_limiter
from docker.types import LogConfig, Ulimit
from pydantic import (
    AfterValidator,
    ByteSize,
    ConfigDict,
    Field,
    GetCoreSchemaHandler,
    SerializeAsAny,
    ValidationInfo,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic.types import PathType
from pydantic_core import CoreSchema
from pydantic_core.core_schema import no_info_after_validator_function, union_schema
from typing_extensions import TypedDict, override

from algobattle.battle import (
    Battle,
    BattleUi,
    FightHandler,
    FightUi,
    Iterated,
    ProgramLogConfigLocation,
    ProgramLogConfigTime,
)
from algobattle.problem import Problem
from algobattle.program import BuildUi, Matchup, ProgramConfigView, ProgramUi, TeamHandler
from algobattle.util import BaseModel, ExceptionInfo, Role, RunningTimer


@dataclass(frozen=True)
class MatchupStr:
    """Holds the names of teams in a matchup."""

    generator: str
    solver: str

    @classmethod
    def make(cls, matchup: Matchup) -> Self:
        """Creates an instance from a matchup object."""
        return cls(matchup.generator.name, matchup.solver.name)

    @classmethod
    def __pydantic_get_core_schema__(cls, source: type[Self], handler: GetCoreSchemaHandler) -> CoreSchema:
        def parse(val: str) -> Self:
            return cls(*val.split(" vs "))

        return no_info_after_validator_function(parse, handler(str))

    @model_serializer
    def __str__(self) -> str:
        return f"{self.generator} vs {self.solver}"


class Match(BaseModel):
    """The Result of a whole Match."""

    config: "AlgobattleConfig" = Field(exclude=True)
    active_teams: list[str] = Field(default_factory=list)
    excluded_teams: dict[str, ExceptionInfo] = Field(default_factory=dict)
    battles: dict[MatchupStr, SerializeAsAny[Battle]] = Field(default_factory=dict)

    async def _run_battle(
        self,
        battle: Battle,
        matchup: Matchup,
        problem: Problem,
        cpus: list[str | None],
        ui: "Ui",
        limiter: CapacityLimiter,
    ) -> None:
        async with limiter:
            set_cpus = cpus.pop()
            ui.start_battle(matchup)
            battle_ui = BattleObserver(ui, matchup)
            handler = FightHandler(
                problem=problem,
                generator=matchup.generator.generator,
                solver=matchup.solver.solver,
                battle=battle,
                ui=battle_ui,
                set_cpus=set_cpus,
                log_config=self.config.project.log_program_io,
            )
            try:
                await battle.run_battle(
                    handler,
                    self.config.match.battle,
                    problem.min_size,
                    battle_ui,
                )
            except Exception as e:
                battle.runtime_error = ExceptionInfo.from_exception(e)
            cpus.append(set_cpus)
            ui.battle_completed(matchup)

    async def run(
        self,
        ui: "Ui | None" = None,
    ) -> Self:
        """Runs a match with the given config settings and problem type.

        The first step is building the docker images for each team in `config.teams`. Any teams where this process fails
        are excluded from the match and will receive zero points. Then each pair of teams will fight two battles against
        each other, one where the first is generating and the second is solving, and one where the roles are swapped.
        Since all of these battles are completely independent, you can set `config.parallel_battles` to have some number
        of them run in parallel. This will speed up the exection of the match, but can also make the match unfair if the
        hardware running it does not have the resources to adequately execute that many containers in parallel.
        """
        if ui is None:
            ui = EmptyUi()
        config = self.config
        problem = config.loaded_problem

        with await TeamHandler.build(config.teams, problem, config.as_prog_config(), ui) as teams:
            self.active_teams = [t.name for t in teams.active]
            self.excluded_teams = teams.excluded
            battle_cls = Battle.all()[config.match.battle.type]
            limiter = CapacityLimiter(config.project.parallel_battles)
            current_default_thread_limiter().total_tokens = config.project.parallel_battles
            set_cpus = config.project.set_cpus
            if isinstance(set_cpus, list):
                match_cpus = cast(list[str | None], set_cpus[: config.project.parallel_battles])
            else:
                match_cpus = [set_cpus] * config.project.parallel_battles
            ui.start_battles()
            async with create_task_group() as tg:
                for matchup in teams.matchups:
                    battle = battle_cls()
                    self.battles[MatchupStr.make(matchup)] = battle
                    tg.start_soon(self._run_battle, battle, matchup, problem, match_cpus, ui, limiter)
        return self

    def calculate_points(self) -> dict[str, float]:
        """Calculate the number of points each team scored.

        Every team scores between 0 and `total_points_per_team` points.
        Excluded teams are considered to have lost all their battles and thus receive 0 points.
        The other teams each get points based on how well they did against each other team compared to how well that
        other team did against them.
        """
        total_points_per_team = self.config.project.points
        points = dict.fromkeys(self.active_teams + list(self.excluded_teams), 0.0)
        if len(self.active_teams) == 0:
            return points
        if len(self.active_teams) == 1:
            points[self.active_teams[0]] = total_points_per_team
            return points

        points_per_matchup = round(total_points_per_team / (len(self.active_teams) - 1), 1)

        for first, second in combinations(self.active_teams, 2):
            try:
                first_res = self.battles[MatchupStr(second, first)]
                second_res = self.battles[MatchupStr(first, second)]
            except KeyError:
                continue
            total_score = max(0, first_res.score(self.config.match.battle)) + max(
                0, second_res.score(self.config.match.battle)
            )
            if total_score == 0:
                # Default values for proportions, assuming no team manages to solve anything
                first_ratio = 0.5
                second_ratio = 0.5
            else:
                first_ratio = first_res.score(self.config.match.battle) / total_score
                second_ratio = second_res.score(self.config.match.battle) / total_score

            points[first] += round(points_per_matchup * first_ratio, 1)
            points[second] += round(points_per_matchup * second_ratio, 1)

        # we need to also add the points each team would have gotten fighting the excluded teams
        # each active team would have had one set of battles against each excluded team
        for team in self.active_teams:
            points[team] += points_per_matchup * len(self.excluded_teams)

        return points

    def format(self, *, indent: int | None = 2, error_detail: Literal["high", "low"] = "low") -> str:
        """Nicely formats the match result into a json string."""
        match error_detail:
            case "high":
                exclude = None
            case "low":
                detail = {"detail"}
                program = {"error": detail}
                exclude = {
                    "excluded_teams": {"__all__": detail},
                    "battles": {
                        "__all__": {
                            "runtime_error": detail,
                            "fights": {
                                "__all__": {
                                    "generator": program,
                                    "solver": program,
                                }
                            },
                        }
                    },
                }
        return self.model_dump_json(exclude_defaults=True, indent=indent, exclude=exclude)


class Ui(BuildUi, Protocol):
    """Base class for a UI that observes a Match and displays its data.

    The Ui object both observes the match object as it's being built and receives additional updates through
    method calls. To do this, it provides several objects whose methods are essentially curried versions of
    its own methods. These observer classes should generally not be subclassed, all Ui functionality can be implemented
    by just subclassing :class:`Ui` and implementing its methods.
    """

    match: Match

    def start_build_step(self, teams: Iterable[str], timeout: float | None) -> None:
        """Tells the ui that the build process has started."""
        return

    def start_build(self, team: str, role: Role) -> None:
        """Informs the ui that a new program is being built."""
        return

    def finish_build(self, team: str, success: bool) -> None:
        """Informs the ui that the current build has been finished."""
        return

    def start_battles(self) -> None:
        """Tells the UI that building the programs has finished and battles will start now."""
        return

    def start_battle(self, matchup: Matchup) -> None:
        """Notifies the Ui that a battle has been started."""
        return

    def battle_completed(self, matchup: Matchup) -> None:
        """Notifies the Ui that a specific battle has been completed."""
        return

    def update_battle_data(self, matchup: Matchup, data: Battle.UiData) -> None:
        """Passes new custom battle data to the Ui."""
        return

    def start_fight(self, matchup: Matchup, max_size: int) -> None:
        """Informs the Ui of a newly started fight."""
        return

    def end_fight(self, matchup: Matchup) -> None:
        """Informs the Ui that the current fight has finished."""
        return

    def start_program(
        self,
        matchup: Matchup,
        role: Role,
        data: RunningTimer,
    ) -> None:
        """Passes new info about programs in the current fight to the Ui."""
        return

    def end_program(self, matchup: Matchup, role: Role, runtime: float) -> None:
        """Informs the Ui that the currently running programmes has finished."""
        return


class EmptyUi(Ui):
    """A dummy Ui."""

    match: Match

    def __enter__(self) -> Self:
        """Starts displaying the Ui."""
        return self

    def __exit__(self, *args: object) -> None:
        """Stops the Ui."""
        return


@dataclass
class BattleObserver(BattleUi, FightUi, ProgramUi):
    """Tracks updates for a specific battle."""

    ui: Ui
    matchup: Matchup

    @override
    def update_battle_data(self, data: Battle.UiData) -> None:
        self.ui.update_battle_data(self.matchup, data)

    @override
    def start_fight(self, max_size: int) -> None:
        self.ui.start_fight(self.matchup, max_size)

    @override
    def end_fight(self) -> None:
        self.ui.end_fight(self.matchup)

    @override
    def start_program(self, role: Role, timeout: float | None) -> None:
        self.ui.start_program(self.matchup, role, RunningTimer(datetime.now(), timeout))

    @override
    def stop_program(self, role: Role, runtime: float) -> None:
        self.ui.end_program(self.matchup, role, runtime)


################################################################################
#   Config stuff
################################################################################


class TimeFloat:
    """A float specifying a number of seconds.

    Can be parsed from pydantic either as a number of seconds or a timedelta specifier.
    """

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        def convert(val: float | timedelta) -> float:
            return val.total_seconds() if isinstance(val, timedelta) else val

        return no_info_after_validator_function(convert, union_schema([handler(float), handler(timedelta)]))


def parse_none(value: Any) -> Any | None:
    """Used as a validator to parse false-y values into Python None objects."""
    return value or None


T = TypeVar("T")
TimeDeltaFloat = Annotated[float, TimeFloat]
ByteSizeInt = Annotated[int, ByteSize]
WithNone = Annotated[T | None, AfterValidator(parse_none)]


def _relativize_path(path: Path, info: ValidationInfo) -> Path:
    """If the passed path is relative to the current directory it gets relativized to the `base_path` instead."""
    if info.context and isinstance(info.context.get("base_path", None), Path) and not path.is_absolute():
        return info.context["base_path"] / path
    return path


def _relativize_file(path: Path, info: ValidationInfo) -> Path:
    path = _relativize_path(path, info)
    return PathType.validate_file(path, info)


RelativePath = Annotated[Path, AfterValidator(_relativize_path), Field(validate_default=True)]
RelativeFilePath = Annotated[Path, AfterValidator(_relativize_file), Field(validate_default=True)]


class _Adapter:
    """Turns a docker library config class into a pydantic parseable one."""

    _Args: ClassVar[type]

    @classmethod
    def _construct(cls, kwargs: dict[str, Any]) -> Self:
        return cls(**kwargs)

    @classmethod
    def __get_pydantic_core_schema__(cls, source: type, handler: GetCoreSchemaHandler) -> CoreSchema:
        return no_info_after_validator_function(cls._construct, handler(cls._Args))


class PydanticLogConfig(LogConfig, _Adapter):
    class _Args(TypedDict):
        type: str
        conifg: dict[Any, Any]


class PydanticUlimit(Ulimit, _Adapter):
    class _Args(TypedDict):
        name: str
        soft: int
        hard: int


class AdvancedRunArgs(BaseModel):
    """Advanced docker run options.

    Contains all options exposed on the python docker run api, except `device_requests`
    and those set by :meth:`Image.run` itself.
    """

    class _BlockIOWeight(TypedDict):
        Path: str
        Weight: int

    class _DeviceRate(TypedDict):
        Path: str
        Rate: int

    class _HealthCheck(TypedDict):
        test: list[str] | str
        interval: int
        timeout: int
        retries: int
        start_period: int

    # defaults set by us
    network_mode: str = "none"

    # actual docker defaults
    command: str | list[str] | None = None
    auto_remove: bool | None = None
    blkio_weight_device: list[_BlockIOWeight] | None = None
    blkio_weight: int | None = Field(default=None, ge=10, le=1000)
    cap_add: list[str] | None = None
    cap_drop: list[str] | None = None
    cgroup_parent: str | None = None
    cgroupns: str | None = None
    cpu_count: int | None = None
    cpu_percent: int | None = None
    cpu_period: int | None = None
    cpu_quota: int | None = None
    cpu_rt_period: int | None = None
    cpu_rt_runtime: int | None = None
    cpu_shares: int | None = None
    cpuset_mems: str | None = None
    device_cgroup_rules: list[str] | None = None
    device_read_bps: list[_DeviceRate] | None = None
    device_read_iops: list[_DeviceRate] | None = None
    device_write_bps: list[_DeviceRate] | None = None
    device_write_iops: list[_DeviceRate] | None = None
    devices: list[str] | None = None
    dns: list[str] | None = None
    dns_opt: list[str] | None = None
    dns_search: list[str] | None = None
    domainname: str | list[str] | None = None
    entrypoint: str | list[str] | None = None
    environment: dict[str, str] | list[str] | None = None
    extra_hosts: dict[str, str] | None = None
    group_add: list[str] | None = None
    healthcheck: _HealthCheck | None = None
    hostname: str | None = None
    init: bool | None = None
    init_path: str | None = None
    ipc_mode: str | None = None
    isolation: str | None = None
    kernel_memory: int | str | None = None
    labels: dict[str, str] | list[str] | None = None
    links: dict[str, str] | None = None
    log_config: PydanticLogConfig | None = None
    lxc_conf: dict[Any, Any] | None = None
    mac_address: str | None = None
    mem_limit: int | str | None = None
    mem_reservation: int | str | None = None
    mem_swappiness: int | None = None
    memswap_limit: str | int | None = None
    network: str | None = None
    network_disabled: bool | None = None
    oom_kill_disable: bool | None = None
    oom_score_adj: int | None = None
    pid_mode: str | None = None
    pids_limit: int | None = None
    platform: str | None = None
    ports: dict[Any, Any] | None = None
    privileged: bool | None = None
    publish_all_ports: bool | None = None
    read_only: bool | None = None
    restart_policy: dict[Any, Any] | None = None
    runtime: str | None = None
    security_opt: list[str] | None = None
    shm_size: str | int | None = None
    stdin_open: bool | None = None
    stdout: bool | None = None
    stderr: bool | None = None
    stop_signal: str | None = None
    storage_opt: dict[Any, Any] | None = None
    stream: bool | None = None
    sysctls: dict[Any, Any] | None = None
    tmpfs: dict[Any, Any] | None = None
    tty: bool | None = None
    ulimits: list[PydanticUlimit] | None = None
    use_config_proxy: bool | None = None
    user: str | int | None = None
    userns_mode: str | None = None
    uts_mode: str | None = None
    version: str | None = None
    volume_driver: str | None = None
    volumes: dict[Any, Any] | list[Any] | None = None
    volumes_from: list[Any] | None = None
    working_dir: str | None = None

    @cached_property
    def kwargs(self) -> dict[str, Any]:
        """Transforms the object into :meth:`client.containers.run` kwargs."""
        return self.model_dump(exclude_none=True)


class AdvancedBuildArgs(BaseModel):
    """Advanced docker build options.

    Contains all options exposed on the python docker build api, except those set by :meth:`Image.build` itself.
    """

    class _ContainerLimits(TypedDict):
        memory: int
        memswap: int
        cpushares: int
        cpusetcpus: str

    # defaults set by us
    rm: bool = True
    forcerm: bool = True
    quiet: bool = True
    network_mode: str = "host"
    pull: bool | None = True

    # actual Docker defaults
    nocache: bool | None = None
    encoding: str | None = None
    buildargs: dict[Any, Any] | None = None
    container_limits: _ContainerLimits | None = None
    shmsize: int | None = None
    labels: dict[Any, Any] | None = None
    cache_from: list[Any] | None = None
    target: str | None = None
    squash: bool | None = None
    extra_hosts: dict[Any, Any] | None = None
    platform: str | None = None
    isolation: str | None = None
    use_config_proxy: bool | None = None

    @cached_property
    def kwargs(self) -> dict[str, Any]:
        """Transforms the object into :meth:`client.images.build` kwargs."""
        return self.model_dump(exclude_none=True)


class DockerConfig(BaseModel):
    """Settings passed directly to the docker daemon."""

    build: AdvancedBuildArgs = AdvancedBuildArgs()
    run: AdvancedRunArgs = AdvancedRunArgs()


class RunConfig(BaseModel):
    """Parameters determining how a program is run."""

    timeout: WithNone[TimeDeltaFloat] = 20
    """Timeout in seconds, or `false` for no timeout."""
    space: WithNone[ByteSizeInt] = 4_000_000_000
    """Maximum memory space available, or `false` for no limitation.

    Can be either an plain number of bytes like `30000` or a string including
    a unit like `30 kB`.
    """
    cpus: int = 1
    """Number of cpu cores available."""

    @field_validator("cpus")
    @classmethod
    def check_nonzero(cls, val: int) -> int:
        """Checks that the number of available cpus is non-zero."""
        if not val:
            raise ValueError("Number must be non-zero")
        else:
            return val


class MatchConfig(BaseModel):
    """Parameters determining the match execution.

    It will be parsed from the given config file and contains all settings that specify how the match is run.
    """

    problem: str
    """The problem this match is over."""
    build_timeout: WithNone[TimeDeltaFloat] = 600.0
    """Timeout for building each docker image."""
    max_program_size: WithNone[ByteSizeInt] = 4_000_000_000
    """Maximum size a built program image is allowed to be."""
    strict_timeouts: bool = False
    """Whether to raise an error if a program runs into the timeout."""
    generator: RunConfig = RunConfig()
    """Settings determining generator execution."""
    solver: RunConfig = RunConfig()
    """Settings determining solver execution."""
    battle: Battle.Config = Iterated.Config()
    """Config for the battle type."""

    model_config = ConfigDict(revalidate_instances="always")


class DynamicProblemConfig(BaseModel):
    """Defines metadata used to dynamically import problems."""

    location: RelativePath = Field(default=Path("problem.py"), validate_default=True)
    """Path to the file defining the problem"""
    dependencies: list[str] = Field(default_factory=list)
    """List of dependencies needed to run the problem"""


class ProjectConfig(BaseModel):
    """Various project settings."""

    class ProgramOutputConfig(BaseModel):
        """How to log program output."""

        # a bit janky atm, allows for future expansion
        when: ProgramLogConfigTime = ProgramLogConfigTime.error
        output: ProgramLogConfigLocation = ProgramLogConfigLocation.inline

    parallel_battles: int = 1
    """Number of battles exectuted in parallel."""
    name_images: bool = True
    """Whether to give the docker images names."""
    cleanup_images: bool = False
    """Whether to clean up the images after we use them."""
    set_cpus: str | list[str] | None = None
    """Wich cpus to run programs on, if it is a list each battle will use a different cpu specification for it."""
    error_detail: Literal["low", "high"] = "high"
    """How detailed error messages should be.
    Higher settings help in debugging, but may leak information from other teams.
    """
    log_program_io: ProgramOutputConfig = ProgramOutputConfig()
    """How to log program output."""
    points: int = 100
    """Highest number of points each team can achieve."""
    results: RelativePath = Field(default=Path("./results"), validate_default=True)
    """Path to a folder where the results will be saved."""

    @model_validator(mode="after")
    def val_set_cpus(self) -> Self:
        """Validates that each battle that is being executed is assigned some cpu cores."""
        if isinstance(self.set_cpus, list) and self.parallel_battles > len(self.set_cpus):
            raise ValueError("Number of parallel battles exceeds the number of set_cpu specifier strings.")
        else:
            return self


class TeamInfo(BaseModel):
    """The config parameters defining a team."""

    generator: RelativePath
    solver: RelativePath


TeamInfos: TypeAlias = dict[str, TeamInfo]


def _empty_default() -> Any:
    """Helper to make a structure that gets parsed to a default pydantic struct while passing type checking."""
    return {}


class AlgobattleConfig(BaseModel):
    """Base that contains all config options and can be parsed from config files."""

    # funky defaults to force their validation with context info present
    teams: TeamInfos = Field(default_factory=dict)
    project: ProjectConfig = Field(default_factory=_empty_default, validate_default=True)
    match: MatchConfig
    docker: DockerConfig = DockerConfig()
    problem: DynamicProblemConfig = Field(default_factory=_empty_default, validate_default=True)

    model_config = ConfigDict(revalidate_instances="always")

    @cached_property
    def loaded_problem(self) -> Problem:
        """The problem this config uses."""
        return Problem.load(self.match.problem, self.problem.location if self.problem.location.is_file() else None)

    @classmethod
    def from_file(cls, file: Path, *, ignore_uninstalled: bool = False, relativize_paths: bool = True) -> Self:
        """Parses a config object from a toml file.

        Args:
            file: Path to the file, or a directory containing one called 'algobattle.toml'.
            ignore_uninstalled: Whether to raise errors if the specified battle type is not installed.
            relativize_paths: Wether to relativize paths to the config's location rather than the cwd.
        """
        Battle.load_entrypoints()
        if not file.is_file():
            if file.joinpath("algobattle.toml").is_file():
                file /= "algobattle.toml"
            else:
                raise FileNotFoundError("The path does not point to an Algobattle project")
        try:
            config_dict = tomllib.loads(file.read_text())
        except tomllib.TOMLDecodeError as e:
            raise ValueError(f"The config file at {file} is not a properly formatted TOML file!\n{e}") from e
        context: dict[str, Any] = {"ignore_uninstalled": ignore_uninstalled}
        if relativize_paths:
            context["base_path"] = file.parent
        return cls.model_validate(config_dict, context=context)

    def as_prog_config(self) -> ProgramConfigView:
        """Builds a simple object containing all program relevant settings."""
        return ProgramConfigView(
            build_timeout=self.match.build_timeout,
            max_program_size=self.match.max_program_size,
            strict_timeouts=self.match.strict_timeouts,
            build_kwargs=self.docker.build.kwargs,
            run_kwargs=self.docker.run.kwargs,
            generator=self.match.generator,
            solver=self.match.solver,
            name_images=self.project.name_images,
            cleanup_images=self.project.cleanup_images,
        )
