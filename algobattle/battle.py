"""Main battle script. Executes all possible types of battles, see battle --help for all options."""
from __future__ import annotations
from argparse import ArgumentParser, Namespace
from contextlib import ExitStack
from dataclasses import dataclass, field
from functools import partial
import sys
import logging
import datetime as dt
from pathlib import Path
from typing import Callable, Literal, TypeVar
import tomli
from algobattle.battle_wrapper import BattleWrapper
from algobattle.fight_handler import FightHandler

from algobattle.match import MatchInfo
from algobattle.team import TeamInfo
from algobattle.ui import Ui
from algobattle.util import check_path, import_problem_from_path
from algobattle.battle_wrappers.averaged import Averaged
from algobattle.battle_wrappers.iterated import Iterated


def setup_logging(logging_path: Path, verbose_logging: bool, silent: bool):
    """Creates and returns a parent logger.

    Parameters
    ----------
    logging_path : Path
        Path to folder where the logfile should be stored at.
    verbose_logging : bool
        Flag indicating whether to include debug messages in the output
    silent : bool
        Flag indicating whether not to pipe the logging output to stderr.

    Returns
    -------
    logger : Logger
        The Logger object.
    """
    common_logging_level = logging.INFO

    if verbose_logging:
        common_logging_level = logging.DEBUG

    Path(logging_path).mkdir(exist_ok=True)

    t = dt.datetime.now()
    current_timestamp = f"{t.year:04d}-{t.month:02d}-{t.day:02d}_{t.hour:02d}-{t.minute:02d}-{t.second:02d}"
    logging_path = Path(logging_path, current_timestamp + '.log')

    logging.basicConfig(handlers=[logging.FileHandler(logging_path, 'w', 'utf-8')],
                        level=common_logging_level,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        datefmt='%H:%M:%S')
    logger = logging.getLogger('algobattle')

    if not silent:
        # Pipe logging out to console
        _consolehandler = logging.StreamHandler(stream=sys.stderr)
        _consolehandler.setLevel(common_logging_level)

        _consolehandler.setFormatter(logging.Formatter('%(message)s'))

        logger.addHandler(_consolehandler)

    logger.info(f"You can find the log files for this run in {logging_path}")
    return logger


@dataclass(kw_only=True)
class BattleConfig:
    problem: Path | None = None
    verbose: bool = False
    logging_path: Path = Path.home() / ".algobattle_logs"
    display: Literal["silent", "logs", "ui"] = "logs"
    safe_build: bool = False
    battle_type: Literal["iterated", "averaged"] = "iterated"
    teams: list[TeamInfo] = field(default_factory=list)
    rounds: int = 5
    points: int = 100
    timeout_build: float | None = 600
    timeout_generator: float | None = 30
    timeout_solver: float | None = 30
    space_generator: int | None = None
    space_solver: int | None = None
    cpus: int = 1

    @staticmethod
    def from_file(path: Path) -> BattleConfig:
        """Parses a BattleConfig object from a toml file."""
        with open(path, "rb") as file:
            try:
                config = tomli.load(file)
            except tomli.TOMLDecodeError as e:
                raise ValueError(f"The file at {path} is not a properly formatted TOML file!\n{e}")
        teams = []
        for team_spec in config["teams"]:
            try:
                name = team_spec["name"]
                gen = check_path(team_spec["generator"], type="dir")
                sol = check_path(team_spec["solver"], type="dir")
                teams.append(TeamInfo(name=name, generator=gen, solver=sol))
            except TypeError:
                raise ValueError(f"The config file at {path} is incorrectly formatted!")
        config["teams"] = teams
        for wrapper_name in ("iterated", "averaged"):
            config.pop(wrapper_name, None)
        return BattleConfig(**config)

_T = TypeVar("_T")
def _optional(f: Callable[[str], _T]) -> Callable[[str], _T | None]:
    def inner(arg: str) -> _T | None:
        if arg.lower() == "none":
            return None
        else:
            return f(arg)
    return inner


_float = _optional(float)
_int = _optional(int)


def parse_cli_args(args: list[str]) -> tuple[BattleConfig, BattleWrapper.Config]:
    """Parse a given CLI arg list into config objects."""

    parser = ArgumentParser()
    parser.add_argument("path", type=check_path, help="Path to the needed files if they aren't specified seperately.")
    parser.add_argument("--problem", type=partial(check_path, type="dir"), default=None, help="Path to a problem folder.")
    parser.add_argument("--config", type=partial(check_path, type="file"), default=None, help="Path to a config file.")

    parser.add_argument("--verbose", "-v", dest="verbose", action="store_true", help="More detailed log output.")
    parser.add_argument("--logging_path", type=partial(check_path, type="dir"), default=Path.home() / ".algobattle_logs", help="Folder that logs are written into.")
    parser.add_argument("--display", choices=["silent", "logs", "ui"], default="logs", help="Choose output mode, silent disables all output, logs displays the battle logs on STDERR, ui displays a small GUI showing the progress of the battle.")
    parser.add_argument("--safe_build", action="store_true", help="Isolate docker image builds from each other. Significantly slows down battle setup but closes prevents images from interfering with each other.")

    parser.add_argument("--battle_type", choices=["iterated", "averaged"], default="iterated", help="Type of battle wrapper to be used.")
    parser.add_argument("--team", dest="teams", type=partial(check_path, type="dir"), help="Path to a folder containing /generator and /solver folders. For more detailed team configuration use the config file.")
    parser.add_argument("--rounds", type=int, default=5, help="Number of rounds that are to be fought in the battle (points are split between all rounds).")
    parser.add_argument("--points", type=int, default=100, help="number of points distributed between teams.")

    parser.add_argument("--timeout_build", type=_float, default=600, help="Timeout for the build step of each docker image.")
    parser.add_argument("--timeout_generator", type=_float, default=30, help="Time limit for the generator execution.")
    parser.add_argument("--timeout_solver", type=_float, default=30, help="Time limit for the solver execution.")
    parser.add_argument("--space_generator", type=_int, default=None, help="Memory limit for the generator execution, in MB.")
    parser.add_argument("--space_solver", type=_int, default=None, help="Memory limit the solver execution, in MB.")
    parser.add_argument("--cpus", type=int, default=1, help="Number of cpu cores used for each docker container execution.")
    

    # battle wrappers have their configs automatically added to the CLI args
    for wrapper in (Iterated, Averaged):
        group = parser.add_argument_group(wrapper.name())
        for name, kwargs in wrapper.Config.as_argparse_args():
            group.add_argument(f"--{wrapper.name().lower()}_{name}", **kwargs)

    # we want the hierarchy to basically be CLI > config file > defaults, so we need to first parse the CLI args to get
    # the config file location, load that, and then parse CLI args again.
    # you could skip the second parse by having argparse not set the default in the namespace, but then we have worse CLI help messages
    cfg_args = parser.parse_args(args)
    if cfg_args.config is not None:
        cfg_path = cfg_args.config
    else:
        cfg_path = cfg_args.path / "config.toml"
    if cfg_path.is_file():
        with open(cfg_path, "rb") as file:
            try:
                config = tomli.load(file)
            except tomli.TOMLDecodeError as e:
                raise ValueError(f"The config file at {cfg_path} is not a properly formatted TOML file!\n{e}")
    else:
        config = {}

    battle_config = Namespace(**config.get("algobattle", {}))
    parser.parse_args(args, namespace=battle_config)

    # args where the defaults are dependend on other args
    if battle_config.problem is None:
        battle_config.problem = cfg_args.path
    if battle_config.teams:
        teams_pre = battle_config.teams
    else:
        teams_pre = [cfg_args.path]

    # building TeamInfo objects from the args, ideally there'd be a better way to do this
    battle_config.teams = []
    for team_spec in teams_pre:
        if isinstance(team_spec, dict):
            try:
                name = team_spec["name"]
                gen = check_path(team_spec["generator"], type="dir")
                sol = check_path(team_spec["solver"], type="dir")
                battle_config.teams.append(TeamInfo(name=name, generator=gen, solver=sol))
            except TypeError:
                raise ValueError(f"The config file at {cfg_path} is incorrectly formatted!")
        else:
            battle_config.teams.append(TeamInfo(name=team_spec.name, generator=team_spec / "generator", solver=team_spec / "solver"))

    battle_config = BattleConfig(**vars(battle_config))
    wrapper_config = BattleWrapper.Config()

    return battle_config, wrapper_config


def main():
    """Entrypoint of `algobattle` CLI."""
    try:
        battle_config, wrapper_config = parse_cli_args(sys.argv[1:])
        logger = setup_logging(battle_config.logging_path, battle_config.verbose, battle_config.display != "logs")

    except KeyboardInterrupt:
        raise SystemExit("Received keyboard interrupt, terminating execution.")

    try:
        problem = import_problem_from_path(battle_config.problem)
        fight_handler = FightHandler(problem, timeout_generator=battle_config.timeout_generator,
            timeout_solver=battle_config.timeout_solver, space_generator=battle_config.space_solver,
            space_solver=battle_config.space_solver, cpus=battle_config.cpus)
        wrapper = BattleWrapper.initialize(battle_config.battle_type, fight_handler, wrapper_config)
        with MatchInfo.build(
            problem=problem,
            wrapper=wrapper,
            teams=battle_config.teams,
            rounds=battle_config.rounds,
            safe_build=battle_config.safe_build,
        ) as match_info, ExitStack() as stack:
            if battle_config.display == "ui":
                ui = Ui()
                stack.enter_context(ui)
            else:
                ui = None

            result = match_info.run_match(ui)

            logger.info('#' * 78)
            logger.info(str(result))
            if battle_config.points > 0:
                points = result.calculate_points(battle_config.points)
                for team, pts in points.items():
                    logger.info(f"Group {team} gained {pts:.1f} points.")

    except KeyboardInterrupt:
        logger.critical("Received keyboard interrupt, terminating execution.")


if __name__ == "__main__":
    main()
