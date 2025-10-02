"""Cli entrypoint to execute matches.

Provides a command line interface to start matches and observe them. See `battle --help` for further options.
"""

import operator
import shutil
import sys
from collections.abc import Iterable
from enum import StrEnum
from functools import cached_property
from importlib.metadata import version as pkg_version
from os import environ
from pathlib import Path
from random import choice
from shutil import rmtree
from subprocess import PIPE, Popen
from typing import Annotated, Any, ClassVar, Literal, Self, cast
from zipfile import ZipFile

from anyio import run as run_async_fn
from click import Choice
from click.core import Context, Parameter
from pydantic import Field, TypeAdapter, ValidationError
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    ProgressColumn,
    SpinnerColumn,
    Task,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Column, Table
from rich.text import Text
from rich.theme import Theme
from rich.traceback import Traceback
from tomlkit import TOMLDocument, comment, dumps as dumps_toml, nl as toml_newline, parse as parse_toml, table
from tomlkit.exceptions import ParseError
from tomlkit.items import Table as TomlTable
from typer import Abort, Argument, Option, Typer, get_app_dir, launch
from typing_extensions import override

from algobattle.battle import Battle
from algobattle.match import AlgobattleConfig, EmptyUi, Match, MatchConfig, MatchupStr, ProjectConfig, TeamInfo, Ui
from algobattle.problem import Instance, Problem, Solution
from algobattle.program import Generator, Matchup, Solver
from algobattle.templates import Language, PartialTemplateArgs, TemplateArgs, write_problem_template, write_templates
from algobattle.util import (
    BaseModel,
    BuildError,
    DockerNotRunning,
    EncodableModel,
    ExceptionInfo,
    Role,
    RunningTimer,
    TempDir,
    timestamp,
)

__all__ = ("app",)

help_message = """The Algobattle command line program.

You can use this to setup your workspace, develop programs, run matches, and more!
For more detailed documentation, visit our website at http://algobattle.org/docs/tutorial
"""
app = Typer(pretty_exceptions_show_locals=True, help=help_message)
packager = Typer(help="Subcommands to package problems and programs into `.algo` files.")
app.add_typer(packager, name="package")
theme = Theme({
    "success": "green",
    "warning": "orange3",
    "error": "red",
    "attention": "magenta2",
    "heading": "blue",
    "info": "dim cyan",
})
console = Console(theme=theme)


class _InstallMode(StrEnum):
    normal = "normal"
    user = "user"


class _General(BaseModel):
    team_name: str | None = None
    install_mode: _InstallMode | None = None
    generator_language: Language = Language.plain
    solver_language: Language = Language.plain


class CliConfig(BaseModel):
    general: _General = Field(default_factory=_General, validate_default=True)
    default_project_table: ProjectConfig | None = Field(default=None)

    _doc: TOMLDocument
    path: ClassVar[Path] = Path(get_app_dir("algobattle")) / "config.toml"

    @classmethod
    def init_file(cls) -> None:
        """Initializes the config file if it does not exist."""
        if not cls.path.is_file():
            cls.path.parent.mkdir(parents=True, exist_ok=True)
            general = table().append("generator_language", "plain").append("solver_language", "plain")
            doc = (
                table()
                .add(comment("# The Algobattle cli configuration"))
                .add(toml_newline())
                .append("general", general)
                .add(toml_newline())
            )
            cls.path.write_text(dumps_toml(doc))

    @classmethod
    def load(cls) -> Self:
        """Parses a config object from a toml file."""
        cls.init_file()
        doc = parse_toml(cls.path.read_text())
        self = cls.model_validate(doc)
        object.__setattr__(self, "_doc", doc)
        return self

    def save(self) -> None:
        """Saves the config to file."""
        self.path.write_text(dumps_toml(self._doc))

    @property
    def default_project_doc(self) -> TomlTable | None:
        """The default exec config for each problem."""
        return self._doc.get("default_project_table", None)

    @cached_property
    def install_cmd(self) -> list[str]:
        cmd = [sys.executable, "-m", "pip", "install"]
        if self.general.install_mode is None:
            command_str: str = Prompt.ask(
                "[attention]Do you want to install problems normally, or into the user directory?[/] If you're using "
                "an environment manager like venv or conda you should install them normally, otherwise user installs "
                "might be better.",
                default="normal",
                choices=["normal", "user"],
                console=console,
            )
            if command_str == "user":
                cmd.append("--user")
                self.general.install_mode = _InstallMode.user
            else:
                self.general.install_mode = _InstallMode.normal
            if "general" not in self._doc:
                self._doc.add("general", table())
            cast(TomlTable, self._doc["general"])["install_mode"] = command_str
            self.save()
        return cmd


@app.command("run")
def run_match(
    *,
    path: Annotated[
        Path, Argument(exists=True, help="Path to either a config file or a directory containing one.")
    ] = Path(),
    ui: Annotated[bool, Option(help="Whether to show the CLI UI during match execution.")] = True,
    save: Annotated[bool, Option(help="Whether to save the match result.")] = True,
) -> Match:
    """Runs a match using the config found at the provided path and displays it to the cli."""
    config = AlgobattleConfig.from_file(path)
    result = Match(config=config)
    try:
        with CliUi(result, config) if ui else EmptyUi() as ui_obj:
            run_async_fn(result.run, ui_obj)
    except DockerNotRunning:
        console.print("[error]Could not connect to the Docker Daemon.[/] Is Docker running?")
        save = False
    except KeyboardInterrupt:
        console.print("[error]Stopping match execution")
    try:
        if config.project.points > 0 and result.active_teams:
            points = result.calculate_points()
            leaderboard = Table(
                Column("Team", justify="center"),
                Column("Points", justify="right"),
                title="[heading]Leaderboard",
            )
            for team, pts in sorted(points.items(), key=operator.itemgetter(1)):
                leaderboard.add_row(team, f"{pts:.1f}")
            console.print(Padding(leaderboard, (1, 0, 0, 0)))
        if save:
            out_path = config.project.results.joinpath(f"match-{timestamp()}.json")
            config.project.results.mkdir(parents=True, exist_ok=True)
            out_path.write_text(result.format(error_detail=config.project.error_detail))
            console.print("Saved match result to ", out_path)
    except KeyboardInterrupt as e:
        raise Abort from e
    return result


def _init_program(target: Path, lang: Language, args: PartialTemplateArgs, role: Role) -> None:
    dir = target / role
    if dir.exists():
        replace = Confirm.ask(
            f"[attention]The targeted directory already contains a {role}, do you want to replace it?",
            default=True,
            console=console,
        )
        if replace:
            rmtree(dir)
            dir.mkdir()
        else:
            return
    else:
        dir.mkdir(parents=True, exist_ok=True)
    with console.status(f"Initializing {role}"):
        write_templates(dir, lang, TemplateArgs(program=role.value, **args))
    console.print(f"Created a {lang} {role} in {dir}")


class ClickLanguage(Choice):
    """Used to move the language list into the help text epilog."""

    def __init__(self, case_sensitive: bool = True) -> None:
        super().__init__([lang.value for lang in Language], case_sensitive)

    def get_metavar(self, param: Parameter, ctx: Context) -> str:
        return "LANGUAGE"


@app.command(epilog=f"Supported languages are: {', '.join(Language)}.")
def init(
    target: Annotated[Path | None, Argument(file_okay=False, writable=True, help="The folder to initialize.")] = None,
    problem_: Annotated[
        str | None,
        Option(
            "--problem",
            "-p",
            help="Path to the .algo file to use, or the name of an installed problem.",
        ),
    ] = None,
    language: Annotated[
        Language | None,
        Option("--language", "-l", help="The language to use for the programs.", click_type=ClickLanguage()),
    ] = None,
    generator: Annotated[
        Language | None,
        Option("--generator", "-g", help="The language to use for the generator.", click_type=ClickLanguage()),
    ] = None,
    solver: Annotated[
        Language | None,
        Option("--solver", "-s", help="The language to use for the solver.", click_type=ClickLanguage()),
    ] = None,
    schemas: Annotated[bool, Option(help="Whether to also save the problem's IO schemas.")] = False,
    new: Annotated[
        bool,
        Option(
            "--new",
            help="Whether to create a new problem from a template. You must then also provide a name with `--problem`",
        ),
    ] = False,
) -> None:
    """Initializes a project directory, setting up the problem files and program folders.

    Generates dockerfiles and an initial project structure for the language(s) you choose. Either use `--language` to
    use the same language for both, or specify each individually with `--generator` and `--solver`.
    """
    if language is not None and (generator is not None or solver is not None):
        console.print("You cannot use both `--language` and `--generator`/`--solver` at the same time.")
        raise Abort
    if language:
        generator = solver = language
    config = CliConfig.load()
    team_name = config.general.team_name or choice((
        "Dogs",
        "Cats",
        "Otters",
        "Red Pandas",
        "Crows",
        "Rats",
        "Cockatoos",
        "Dingos",
        "Penguins",
        "Kiwis",
        "Orcas",
        "Bearded Dragons",
        "Macaws",
        "Wombats",
        "Wallabies",
        "Owls",
        "Seals",
        "Octopuses",
        "Frogs",
        "Jellyfish",
    ))

    if new:  # create a new problem
        if problem_ is None:
            console.print("[error]In order to create a new problem you need to specify its name with `--problem`.")
            raise Abort
        if target is None:
            target = Path() / problem_
        target.mkdir(parents=True, exist_ok=True)
        target.joinpath("algobattle.toml").write_text(f"""[match]\nproblem = "{problem_}"\n""")
        write_problem_template(target / "problem.py", name=problem_)
        console.print(f"Created a new problem file at {target / 'problem.py'}")
        parsed_config = AlgobattleConfig(match=MatchConfig(problem=problem_))

    elif problem_ is None:  # use the preexisting config file in the target folder
        if target is None:
            target = Path()
        try:
            parsed_config = AlgobattleConfig.from_file(target, relativize_paths=False)
        except FileNotFoundError as e:
            console.print("[error]You must use a problem spec file or target a directory with an existing config.")
            raise Abort from e
        except ValueError as e:
            console.print("[error]The Algobattle config file is not formatted properly\n", e)
            raise Abort from e
        console.print("Using existing project data")
        if len(parsed_config.teams) == 1:
            team_name = next(iter(parsed_config.teams.keys()))

    elif problem_ in Problem.available():  # use a preinstalled problem
        if target is None:
            target = Path() / problem_
        target.mkdir(parents=True, exist_ok=True)
        target.joinpath("algobattle.toml").write_text(f"""[match]\nproblem = "{problem_}"\n""")
        parsed_config = AlgobattleConfig(match=MatchConfig(problem=problem_))

    elif (problem := Path(problem_)).is_file():  # use a problem spec file
        with TempDir() as unpack_dir:
            with console.status("Extracting problem data"), ZipFile(problem) as problem_zip:
                problem_zip.extractall(unpack_dir)

            parsed_config = AlgobattleConfig.from_file(unpack_dir, relativize_paths=False)
            if target is None:
                target = Path() / parsed_config.match.problem

            target.mkdir(parents=True, exist_ok=True)
            problem_data = list(unpack_dir.iterdir())
            if any(target.joinpath(path.name).exists() for path in problem_data):
                copy_problem_data = Confirm.ask(
                    "[attention]The target directory already contains an algobattle project, "
                    "do you want to replace it?",
                    default=True,
                    console=console,
                )
            else:
                copy_problem_data = True
            if copy_problem_data:
                for path in problem_data:
                    if (file := target / path.name).is_file():
                        file.unlink()
                    elif (dir := target / path.name).is_dir():
                        rmtree(dir)
                    shutil.move(path, target / path.name)
                console.print("Unpacked problem data")
            else:
                parsed_config = AlgobattleConfig.from_file(target, relativize_paths=False)
                console.print("Using existing problem data")

    else:
        console.print(
            "[error]The problem argument is neither the name of an installed problem, nor the path to a problem spec"
        )
        raise Abort

    problem_name = parsed_config.match.problem
    if deps := parsed_config.problem.dependencies:
        cmd = config.install_cmd
        with (
            console.status(f"Installing {problem_name}'s dependencies"),
            Popen(cmd + deps, env=environ.copy(), stdout=PIPE, stderr=PIPE, text=True) as installer,
        ):
            assert installer.stdout is not None
            assert installer.stderr is not None
            for line in installer.stdout:
                console.print(line.strip("\n"))
            error = "".join(installer.stderr.readlines())
        if installer.returncode:
            console.print(f"[error]Couldn't install the dependencies[/]\n{error}")
            raise Abort
        else:
            console.print(f"[success]Installed dependencies of {problem_name}")

    with console.status("Initializing metadata"):
        config_doc = parse_toml(target.joinpath("algobattle.toml").read_text())
        if "teams" not in config_doc:
            config_doc.add(
                "teams",
                table().add(
                    team_name,
                    table().add("generator", "generator").add("solver", "solver"),
                ),
            )
        if config.default_project_doc is not None and "project" not in config_doc:
            config_doc["project"] = config.default_project_doc
        target.joinpath("algobattle.toml").write_text(dumps_toml(config_doc))
        res_path = parsed_config.project.results
        if not res_path.is_absolute():
            res_path = target / res_path
        res_path.mkdir(parents=True, exist_ok=True)
        gitignore = "*.algo\n*.prob\n"
        if res_path.resolve().is_relative_to(target.resolve()):
            gitignore += f"{res_path.relative_to(target)}/\n"
        target.joinpath(".gitignore").write_text(gitignore)

    if not parsed_config.problem.location.is_absolute():
        parsed_config.problem.location = target / parsed_config.problem.location
    problem_obj = parsed_config.loaded_problem
    if schemas:
        instance: type[Instance] = problem_obj.instance_cls
        solution: type[Solution[Instance]] = problem_obj.solution_cls
        schema_folder = target / "schemas"
        schema_folder.mkdir(exist_ok=True)
        if s := instance.io_schema():
            schema_folder.joinpath("instance.json").write_text(s)
        if s := solution.io_schema():
            schema_folder.joinpath("solution.json").write_text(s)

    template_args: PartialTemplateArgs = {
        "problem": problem_name,
        "team": team_name,
        "with_solution": problem_obj.with_solution,
        "instance_json": issubclass(problem_obj.instance_cls, EncodableModel),
        "solution_json": issubclass(problem_obj.solution_cls, EncodableModel),
    }
    if generator is not None:
        _init_program(target, generator, template_args, Role.generator)
    elif not target.joinpath("generator").exists():
        _init_program(target, config.general.generator_language, template_args, Role.generator)
    if solver is not None:
        _init_program(target, solver, template_args, Role.solver)
    elif not target.joinpath("solver").exists():
        _init_program(target, config.general.solver_language, template_args, Role.solver)

    console.print(f"[success]Initialized algobattle project[/] in {target}")


class TestErrors(BaseModel):
    """Helper class holding test error messages."""

    generator_build: ExceptionInfo | None = None
    solver_build: ExceptionInfo | None = None
    generator_run: ExceptionInfo | None = None
    solver_run: ExceptionInfo | None = None

    def ok(self) -> bool:
        """Return whether the test passed with no problems."""
        return not (self.generator_build or self.solver_build or self.generator_run or self.solver_run)


def test_team(config: AlgobattleConfig, team: str, size: int | None = None) -> TestErrors:
    problem = config.loaded_problem
    console.print(f"Testing programs of team {team}")
    errors = TestErrors()
    instance = None

    async def gen_builder() -> Generator:
        with console.status("Building generator"):
            return await Generator.build(
                config.teams[team].generator, problem=problem, config=config.as_prog_config(), team_name=team
            )

    try:
        with run_async_fn(gen_builder) as gen:
            console.print("[success]Generator built successfully")
            with console.status("Running generator"):
                instance = gen.test(size)
            if isinstance(instance, ExceptionInfo):
                console.print("[error]Generator didn't run successfully")
                errors.generator_run = instance
                instance = None
            else:
                console.print("[success]Generator ran successfully")
    except BuildError as e:
        console.print("[error]Generator didn't build successfully")
        errors.generator_build = ExceptionInfo.from_exception(e)
        instance = None

    sol_error = None

    async def sol_builder() -> Solver:
        with console.status("Building solver"):
            return await Solver.build(
                config.teams[team].solver, problem=problem, config=config.as_prog_config(), team_name=team
            )

    try:
        with run_async_fn(sol_builder) as sol:
            console.print("[success]Solver built successfully")

            instance = instance or cast(Instance, problem.test_instance)
            if instance:
                with console.status("Running solver"):
                    sol_error = sol.test(instance)
                if isinstance(sol_error, ExceptionInfo):
                    console.print("[error]Solver didn't run successfully")
                    errors.solver_run = sol_error
                else:
                    console.print("[success]Solver ran successfully")
            else:
                console.print("[warning]Cannot test running the solver")
    except BuildError as e:
        console.print("[error]Solver didn't build successfully")
        errors.solver_build = ExceptionInfo.from_exception(e)
        instance = None

    return errors


@app.command()
def test(
    project: Annotated[Path, Argument(help="The project folder to use.")] = Path(),
    size: Annotated[int | None, Option(help="The size of instance the generator will be asked to create.")] = None,
) -> Literal["success", "error"]:
    """Tests whether the programs install successfully and run on dummy instances without crashing."""
    if not (project.is_file() or project.joinpath("algobattle.toml").is_file()):
        console.print("[error]The folder does not contain an Algobattle project")
        raise Abort
    config = AlgobattleConfig.from_file(project)
    all_errors: dict[str, TestErrors] = {}

    for team in config.teams:
        res = test_team(config, team, size)
        if not res.ok():
            all_errors[team] = res

    if all_errors:
        err_path = config.project.results.joinpath(f"test-{timestamp()}.json")
        config.project.results.mkdir(parents=True, exist_ok=True)
        err_path.write_bytes(TypeAdapter(dict[str, TestErrors]).dump_json(all_errors, indent=2, exclude_defaults=True))
        console.print(f"You can find detailed error messages at {err_path}")
        return "error"
    else:
        return "success"


@app.command()
def config() -> None:
    """Opens the algobattle cli tool config file."""
    CliConfig.init_file()
    print(f"Opening the algobattle cli config file at {CliConfig.path}.")
    launch(str(CliConfig.path))


@packager.command("problem")
def package_problem(
    project: Annotated[Path, Argument(exists=True, resolve_path=True, help="Path to the project directory.")] = Path(),
    description: Annotated[
        Path | None, Option(exists=True, dir_okay=False, help="Path to a problem description file.")
    ] = None,
    out: Annotated[
        Path | None, Option("--out", "-o", dir_okay=False, file_okay=False, help="Location of the output.")
    ] = None,
) -> None:
    """Packages problem data into an `.algo` file."""
    if project.is_file():
        config = project
        project = project.parent
    else:
        config = project / "algobattle.toml"
    if description is None:
        match list(project.glob("description.*")):
            case []:
                pass
            case [desc]:
                description = desc
            case _:
                console.print(
                    "[error]Found multiple potential description files[/], explicitly specify which you want to include"
                )
                raise Abort

    try:
        config_doc = parse_toml(config.read_text())
        parsed_config = AlgobattleConfig.from_file(config)
    except (ValidationError, ParseError) as e:
        console.print(f"[error]Improperly formatted config file[/]\nError: {e}")
        raise Abort from e
    problem_name = parsed_config.match.problem
    try:
        with console.status("Loading problem"):
            # we need to access the property so that it gets loaded
            parsed_config.loaded_problem # noqa: B018
    except ValueError as e:
        console.print(f"[error]Couldn't load the problem file[/]\nError: {e}")
        raise Abort from e
    except RuntimeError as e:
        error = e.__cause__
        if error is None:
            console.print(f"[error]Couldn't load the problem file[/]\nError: {e}")
            raise Abort from e
        trace = Traceback.from_exception(error.__class__, error, error.__traceback__)
        console.print("[error]Couldn't execute the problem file[/]\nError:", trace)
        raise Abort from e

    if "project" in config_doc:
        config_doc.remove("project")
    if "teams" in config_doc:
        config_doc.remove("teams")
    prob_table: Any = config_doc.get("problem", None)
    if isinstance(prob_table, TomlTable) and "location" in prob_table:
        prob_table.remove("location")
        if len(prob_table) == 0:
            config_doc.remove("problem")

    if out is None:
        out = project / f"{problem_name.lower().replace(' ', '_')}.algo"
    with console.status("Packaging data"), ZipFile(out, "w") as file:
        if parsed_config.problem.location.exists():
            file.write(parsed_config.problem.location, "problem.py")
        file.writestr("algobattle.toml", dumps_toml(config_doc))
        if description is not None:
            file.write(description, description.name)
    console.print("[success]Packaged Algobattle project[/] into", out)


@packager.command("programs")
def package_programs(
    project: Annotated[Path, Argument(help="The project folder to use.")] = Path(),
    team: Annotated[
        str | None,
        Option(
            help="Name of team whose programs should be packaged. If None are specified, every team's are packaged."
        ),
    ] = None,
    generator: Annotated[bool, Option(help="Wether to package the generator")] = True,
    solver: Annotated[bool, Option(help="Wether to package the solver")] = True,
    test_programs: Annotated[
        bool, Option("--test/--no-test", help="Whether to test the programs before packaging them")
    ] = True,
) -> None:
    config = AlgobattleConfig.from_file(project)
    if not config.teams:
        console.print("[error]The project config file doesn't contain any teams[/]")
        raise Abort
    if team is not None and team not in config.teams:
        console.print("[erorr]The selected team isn't in the config file[/]")
        raise Abort
    out = project.parent if project.is_file() else project

    def _package_program(name: str, info: TeamInfo, role: Role) -> None:
        with console.status(f"Packaging {name}'s {role}"), ZipFile(out / f"{name} {role}.prog", "w") as zipfile:
            program_root: Path = getattr(info, role)
            for file in program_root.rglob("*"):
                if file.is_dir():
                    continue
                zipfile.write(file, file.relative_to(program_root))
        console.print(f"[success]Packaged {name}'s {role}")

    for name, info in [(team, config.teams[team])] if team else config.teams.items():
        if test_programs:
            test_result = test_team(config, name)
            if not test_result.ok():
                console.print(f"[error]Team {name} does not pass tests")
                continue
        if generator:
            _package_program(name, info, Role.generator)
        if solver:
            _package_program(name, info, Role.solver)


class TimerTotalColumn(ProgressColumn):
    """Renders time elapsed."""

    def render(self, task: Task) -> Text:
        """Show time elapsed."""
        if not task.started:
            return Text("")
        elapsed = task.finished_time if task.finished else task.elapsed
        total = f" / {task.fields['total_time']}" if "total_time" in task.fields else ""
        current = f"{elapsed:.1f}" if elapsed is not None else ""
        return Text(current + total, style="progress.elapsed")


class LazySpinnerColumn(SpinnerColumn):
    """Spinner that only starts once the task starts."""

    @override
    def render(self, task: Task) -> RenderableType:
        if not task.started:
            return " "
        return super().render(task)


class BuildView(Group):
    """Displays the build process."""

    def __init__(self, teams: Iterable[str]) -> None:
        teams = list(teams)
        self.overall_progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=True,
        )
        self.team_progress = Progress(
            TextColumn("{task.fields[name]}"),
            LazySpinnerColumn(),
            BarColumn(bar_width=10),
            TimeElapsedColumn(),
            TextColumn("{task.fields[status]}"),
        )
        self.overall_task = self.overall_progress.add_task("[heading]Building programs", total=2 * len(teams))
        self.teams = {
            team: self.team_progress.add_task(team, start=False, total=2, status="", name=team) for team in teams
        }
        super().__init__(*self._make_renderables())

    def _make_renderables(self) -> list[RenderableType]:
        return [
            Padding(self.overall_progress, (0, 0, 1, 0)),
            self.team_progress,
        ]


class FightPanel(Panel):
    """Panel displaying a currently running fight."""

    def __init__(self, max_size: int) -> None:
        self.max_size = max_size
        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            LazySpinnerColumn(),
            TimerTotalColumn(),
            TextColumn("{task.fields[message]}"),
            transient=True,
        )
        self.generator = self.progress.add_task("Generator", start=False, total=1, message="")
        self.solver = self.progress.add_task("Solver", start=False, total=1, message="")
        super().__init__(Group(f"Max size: {self.max_size}", self.progress), title="[heading]Current Fight", width=30)


class BattlePanel(Group):
    """Panel that displays the state of a battle."""

    def __init__(self, matchup: Matchup) -> None:
        self.matchup = matchup
        self._battle_data: RenderableType = ""
        self._curr_fight: FightPanel | Literal[""] = ""
        self._past_fights = self._fights_table()
        super().__init__(*self._make_renderable())

    def _make_renderable(self) -> list[RenderableType]:
        return [
            Padding(Rule(title=f"[heading]{self.matchup}"), pad=(1, 0)),
            Columns((self._curr_fight, self._battle_data), align="left"),
            self._past_fights,
        ]

    @property
    def battle_data(self) -> RenderableType:
        return self._battle_data

    @battle_data.setter
    def battle_data(self, value: RenderableType) -> None:
        self._battle_data = Panel(value, title="[heading]Battle Data")
        self._render = list(self._make_renderable())

    @property
    def curr_fight(self) -> FightPanel | Literal[""]:
        return self._curr_fight

    @curr_fight.setter
    def curr_fight(self, value: FightPanel | Literal[""]) -> None:
        self._curr_fight = value
        self._render = self._make_renderable()

    @property
    def past_fights(self) -> Table:
        return self._past_fights

    @past_fights.setter
    def past_fights(self, value: Table) -> None:
        self._past_fights = value
        self._render = self._make_renderable()

    def _fights_table(self) -> Table:
        return Table(
            Column("Fight", justify="right"),
            Column("Max size", justify="right"),
            Column("Score", justify="right"),
            "Detail",
            title="[heading]Most recent fights",
        )


class CliUi(Live, Ui):
    """Ui that uses rich to draw to the console."""

    def __init__(self, match: Match, config: AlgobattleConfig) -> None:
        self.build: BuildView | None = None
        self.battle_panels: dict[Matchup, BattlePanel] = {}
        self.match = match
        self.config = config
        super().__init__(None, refresh_per_second=10, transient=True, console=console)

    def _update_renderable(self) -> None:
        if self.build is None:
            renderable = Group(self.display_match(self.match, self.config.match), *self.battle_panels.values())
        else:
            renderable = self.build
        self.update(Panel(renderable, title=f"[orange1]Algobattle {pkg_version('algobattle_base')}"))

    @staticmethod
    def display_match(match: Match, config: MatchConfig) -> RenderableType:
        """Formats the match data into a table that can be printed to the terminal."""
        table = Table(
            Column("Generating", justify="center"),
            Column("Solving", justify="center"),
            Column("Result", justify="right"),
            title="[heading]Match overview",
        )
        for matchup, battle in match.battles.items():
            res = battle.format_score(battle.score(config.battle)) if battle.runtime_error is None else ":warning:"
            table.add_row(matchup.generator, matchup.solver, res)
        return Padding(table, pad=(1, 0, 0, 0))

    @override
    def start_build_step(self, teams: Iterable[str], timeout: float | None) -> None:
        self.build = BuildView(teams)
        self._update_renderable()

    @override
    def start_build(self, team: str, role: Role) -> None:
        view = self.build
        assert view is not None
        task = view.teams[team]
        match role:
            case Role.generator:
                view.team_progress.start_task(task)
            case Role.solver:
                view.team_progress.advance(task)
                view.overall_progress.advance(view.overall_task, 1)

    @override
    def finish_build(self, team: str, success: bool) -> None:
        view = self.build
        assert view is not None
        task = view.teams[team]
        current = view.team_progress._tasks[task].completed
        view.team_progress.update(task, completed=2, status="" if success else "[error]failed!")
        view.overall_progress.advance(view.overall_task, 2 - current)

    @override
    def start_battles(self) -> None:
        self.build = None
        self._update_renderable()

    @override
    def start_battle(self, matchup: Matchup) -> None:
        self.battle_panels[matchup] = BattlePanel(matchup)
        self._update_renderable()

    @override
    def battle_completed(self, matchup: Matchup) -> None:
        del self.battle_panels[matchup]
        self._update_renderable()

    @override
    def start_fight(self, matchup: Matchup, max_size: int) -> None:
        self.battle_panels[matchup].curr_fight = FightPanel(max_size)

    @override
    def end_fight(self, matchup: Matchup) -> None:
        battle = self.match.battles[MatchupStr.make(matchup)]
        assert battle is not None
        fights = battle.fights[-1:-6:-1]
        panel = self.battle_panels[matchup]
        table = panel._fights_table()
        for i, fight in zip(range(len(battle.fights), len(battle.fights) - len(fights), -1), fights, strict=True):
            if fight.generator.error:
                info = f"[error]Generator failed[/]: {fight.generator.error.message}"
            elif fight.solver and fight.solver.error:
                info = f"[error]Solver failed[/]: {fight.solver.error.message}"
            else:
                assert fight.solver is not None
                info = f"Runtimes: gen {fight.generator.runtime:.1f}s, sol {fight.solver.runtime:.1f}s"
            table.add_row(str(i), str(fight.max_size), f"{fight.score:.1%}", info)
        panel.past_fights = table

    @override
    def start_program(self, matchup: Matchup, role: Role, data: RunningTimer) -> None:
        fight = self.battle_panels[matchup].curr_fight
        assert fight != ""
        match role:
            case Role.generator:
                fight.progress.update(fight.generator, total_time=data.timeout)
                fight.progress.start_task(fight.generator)
            case Role.solver:
                fight.progress.update(fight.solver, total_time=data.timeout)
                fight.progress.start_task(fight.solver)

    @override
    def end_program(self, matchup: Matchup, role: Role, runtime: float) -> None:
        fight = self.battle_panels[matchup].curr_fight
        assert fight != ""
        match role:
            case Role.generator:
                fight.progress.update(fight.generator, completed=1, message=":heavy_check_mark:")
            case Role.solver:
                fight.progress.update(fight.solver, completed=1)

    @override
    def update_battle_data(self, matchup: Matchup, data: Battle.UiData) -> None:
        self.battle_panels[matchup].battle_data = Group(
            *(f"[orchid]{key}[/]: [info]{value}" for key, value in data.model_dump().items())
        )
        self._update_renderable()


if __name__ == "__main__":
    app(prog_name="algobattle")
