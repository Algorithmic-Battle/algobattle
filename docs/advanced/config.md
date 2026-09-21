# Settings

You can configure Algobattle in a lot of different ways, so that it does exactly what you want it to do.

!!! question "Unsure about TOML syntax?"
    TOML syntax can be a bit confusing if you're unfamiliar with it, a full explanation of it can be found on
    [the official site](https://toml.io/en/).

## CLI config

To globally configure how Algobattle behaves you can use the cli config file. Open it by running

```console
algobattle config
```

It's a TOML document that contains two tables:

`general`
: This contains general cli config options. Its keys are:

    `team_name`
    : This is the team name used in the project config whenever you initialize a new project. It doesn't need to be
        the same name you use in the Algobattle website. The default is for Algobattle to dynamically generate a fun
        team name when you run the command.

    `install_mode`
    : If a problem requires some dependencies Algobattle installs them during project initialization. If the mode is
        `user` it will do so in user space, if it is `normal` it will install it globally instead. We recommend you use
        `normal` if you're using an environment manager like Conda and `user` otherwise. In the default setting
        Algobattle will explicitly ask you to set this the first time it is needed.

    `generator_language` and `solver_language`
    : This sets the default language to use in newly initialized projects. You can always override this by passing them
        explicitly when running the command. Defaults to `plain` for both.

`default_project_table`
: This table contains default values you would like to use in the `project` table in project level config files. See
    the [project config](#project-config) documentation for details on what you can specify here. Defaults to only
    containing a `results` key set to the `results` path.

## Project config files {#project-config}

These are the files normally called `algobattle.toml` that live in every Algobattle project folder. They can get quite
big and offer a lot of room for customization. It's made up of several tables at keys `match`, `teams`, `problems`,
`project`, and `docker`:

!!! info "Relative paths"
    If any path in this config file is specified it will be interpreted as relative to the config file, not Algobattle's
    current working directory.

### `match`
: This specifies how each match is run.
    !!! warning
        Be careful not to accidentally change things in here and then develop your programs to work with those settings.
        The match run on the Algobattle server will use the settings you got from your course instructors, so your
        programs might break when making wrong assumptions about the match structure.

    `problem`
    : The only mandatory key in this table. It must be the name of the problem that is to be used. Either the name of an
    installed problem, or one imported dynamically. If the latter option is used you need to specify the problem file's
    location in the `problems` table.

    `build_timeout`
    : A timeout used for every program build. If a build does not complete within this limit it will be cancelled and
    the team whose program it is excluded from the match. Can either be specified as a number which is interpreted as
    seconds, a string in the `HH:MM:SS` format, or `#!toml false` to set no limit. Defaults to 10 minutes.

    `max_program_size`
    : A limit on how big each program may be. Does not limit the memory it can use while running, but rather the disk
    space used by it after it has been built. Can either be an integer which is interpreted as bytes, or a string with
    a unit such as `500 MB` or `1.3gb`, or `#!toml false` to set no limit. Defaults to 4 GB. The
    [Pydantic ByteSize docs](https://docs.pydantic.dev/latest/usage/types/bytesize/#using-bytesize) contain a full
    explanation of possible formats.

    `strict_timeouts`
    : Programs may run into their timeout after already having generated some output. This setting determines how these
    cases are handled, if it's set to `#!toml true` exceeding the time limit is considered a completely unsuccessful
    program execution and is treated similar to if it had crashed completely. If it is `#!toml false`, the program will
    just be stopped after the allotted time and any solution it may have generated is treated as is. Defaults to
    `#!toml false`

    `generator` and `solver`
    : Both of these fields accept the same type of table. They specify parameters guiding each generator and solver
    execution respectively.

        `timeout`
        : A limit on the program runtime. Exact behaviour of what happens when it is exceeded depends on the
        `strict_timeouts` setting. Can either be a number which is interpreted as seconds, a string in the `HH:MM:SS`
        format, or `#!toml false` to set no limit. Defaults to 20 seconds.

        `space`
        : Limits the amount of memory space the program has available during execution. Can either be an integer which
        is interpreted as bytes, a string with a unit such as `500 MB` or `1.3gb`, or `#!toml false` to set no limit.
        Defaults to 4 GB. The
        [Pydantic ByteSize docs](https://docs.pydantic.dev/latest/usage/types/bytesize/#using-bytesize) contain a full
        explanation of possible formats.

        `cpus`
        : Sets the number of physical CPUs the program can use. Can be any non-zero integer. Defaults to 1.

    `battle`
    : This is a table containing settings relevant to the battle type the match uses. Valid keys are documented at the
    [battle type page](battle_types.md). A single key is shared by all battle types:

        `type`
        : This key specifies which battle type to use. Must be the name of a currently installed battle type. Defaults
        to `#!toml "Iterated"`.

### `teams`
: This table tells Algobattle where it can find each team's programs. Keys are team names and values table with this
structure with both keys being mandatory:

    `generator`
    : Path to the team's generator.
    
    `solver`
    : Path to the team's solver.

### `problem`
: Contains data specifying how to dynamically import the problem.

    !!! note
        This table is usually filled in by the course administrators, if you're a student you probably won't have to
        worry about it.

    `location`
    : Path to the problem module. Defaults to `problem.py`.

    `dependencies`
    : A list of [PEP 508](https://peps.python.org/pep-0508/) conformant dependency specification strings. These will be
    installed during project initialization to make sure the problem can be run without issue. Defaults to an empty list.

### `project`
: Contains various project settings.
    !!! info "Feel free to customize this"
        Even though some affect _how_ a match is run they will never change its result. Every student can change these to
        best fit their development workflow regardless of which ones might be used in the server matches.

    `points`
    : An integer specifying the maximum number of points a team can achieve during this match. Defaults to 100.

    `parallel_battles`
    : To speed up battle execution you can let Algobattle run multiple battles in parallel. Note that while programs can
    not directly interact with each other, they might still end up interfering with other programs that are being run at
    the same time by attempting to use the same CPU, memory, or disk resources as each other. You can use the `set_cpus`
    option to mitigate this problem. Defaults to 1.

    `set_cpus`
    : Many modern CPUs have different types of physical cores with different performance characteristics. To provide a
    level playing field it may be good to limit Algobattle to only use certain cores for programs. To do this, specify
    either a comma separated list of CPUs (the first is numbered 0) such as `0,1,3,5` or a range like `0-4`. Note that
    the formatting is very important here, you can not mix the two styles, add any spaces, or similar. A full format
    spec can be found on the [Docker site](https://docs.docker.com/config/containers/resource_constraints/).

        This option accepts either a single such string, or a list of them. If a list is provided each battle that is
        run in parallel will use one of the provided set of cores. For example, if this option is `["0,1", "2-3", "4,5"]`
        and there are two battles executed at the same time, the first would use the first two physical CPUs and the
        second the next two. Defaults to no CPU limitation.

    `name_images`
    : Whether to give the Docker images descriptive names. This is very useful during development, but can lead to
    security risks in matches between competing teams. Because of this we recommend setting this to true `#!toml true`
    if you're a student running Algobattle on your own machine, and `#!toml false` in matches on the Algobattle server.
    Defaults to `#!toml true`.

    `cleanup_images`
    : Whether to remove all Docker images after we're done using them. If set to `#!toml false` your system will be
    kept a bit tidier, but you will also have much longer build times since images can no longer be cached. Defaults
    to `#!toml false`.

    `results`
    : Path to the folder where result files are saved. Each result file will be a json file with a name containing the
    command that created it and the current timestamp. Defaults to `results`

    `error_detail`
    : Used to specify how detailed error messages included in the log files should be. Can be set to `high`, which
    includes full details and stack traces for any exceptions that occur, or `low` to hide sensitive data that may leak
    other team's strategic information.

    `log_program_io`
    : A table that specifies how each program's output should be logged.

        `when`
        : When to save the data. Can be either `never`, `error`, or `always`. When set to `never` or `always` it has the
        expected behaviour, when set to `error` it will save the data only if an error occurred during the fight.
        Defaults to `error`.

        `output`
        : Where to store each program's output data. Currently only supports `disabled` to turn of logging program output
        or `inline` to store jsonable data in the match result json file. Defaults to `inline.`

### `docker`
: Contains various advanced Docker settings that are passed through to the Docker daemon without influencing Algobattle
itself. You generally should not need to use these settings. If you are running into a problem you cannot solve without
them, we recommend first opening an issue on [our GitHub](https://github.com/Benezivas/algobattle/issues) to see if
we can add this functionality to Algobattle directly.

    !!! danger
        Many of these settings are very complicated and have potentially disastrous consequences. We recommend not using
        any of these settings unless you are absolutely sure what the ones you are modifying do. Improper Docker Daemon
        configuration may not only break Algobattle but can give potential attackers root access to your host machine.

    `build`
    : Table containing parameters passed to the docker build command. Further documentation can be found on the
    [Docker build site](https://docs.docker.com/engine/reference/commandline/build/).

    `run`
    : Table containing parameters passed to the docker run command. Further documentation can be found on the
    [Docker run site](https://docs.docker.com/engine/reference/commandline/run/).

## Algobattle subcommands

You can also directly configure many things as command line arguments. Which ones are available depends on the subcommand

### run

This command runs a match using the current project config file.

`path`
: A positional only argument that specifies where to find the project config file. May either point to a file directly,
or to the parent directory of one named `algobattle.toml`. Defaults to the current working directory.

`--ui` / `--no-ui`
: Keyword only option that controls whether the match UI is displayed during execution. Defaults to `#!py True`.

`--save` / `--no-save`
: Keyword only option that controls whether the match result is saved to disk after it's run. Defaults to `#!py True`.

### init

This command initializes a project folder.

`target`
: Path to the folder to create the project data in. When initializing a new problem this defaults to a new subdirectory
of the current working directory named after the problem. If you're instead using an existing project config file it
defaults to the current directory.

`--problem` / `-p`
: Specifies the problem to use for this project. Can either be missing to use an already existing project config, the
name of an installed problem, or the path to a problem spec file. Defaults to using an already existing project config.

`--generator` / `-g`
`--solver` / `-s`
`--language` / `-l`
: Specifies what language template to use for the generator, solver, or both. You cannot specify both `--language` and
either one of the other two options. Can be one of the names of language templates supported by Algobattle. Uses the
defaults set in the [CLI config](#cli-config) (which defaults to `plain`).

??? info "Language list"
    The full list of languages template names is:

    - python
    - rust
    - c
    - cpp
    - csharp
    - javascript
    - typescript
    - java
    - go

`--schemas` / `--no-schemas`
: Whether to also include the problem I/O json schemas in the `schemas` subdirectory. Defaults to `#!py False`.

### test

This runs a basic test checking whether the programs in a project build and run correctly.

`project`
: Path to the Algobattle project to test. Can either point directly to a project config file, or to a folder containing
one called `algobattle.toml`. Defaults to the current working directory.

`--size`
: Will be passed to the generator as it's `max_size`. Defaults to the problem's minimum size.

### config

Opens the CLI config file. Accepts no arguments.1

### package problem

Packages the problem in the project folder into a `.algo` file.

`project`
: Path to the Algobattle project containing the problem. Can either point directly to a project config file, or to
a folder containing one called `algobattle.toml`. Defaults to the current working directory.

`--description`
: Path to a file containing a human-readable description of the problem. Defaults to one called `description` (with any
extension) in the project's directory.

`--out` / `-o`
: Location where the packaged `.algo` file will be placed. Defaults to a file named after the problem in the project's
directory.

### package programs

Packages the programs of a particular team into `.prog` files. These files can be used to easily share programs, or
upload them to the Algobattle website.

!!! tip "Keep program sizes down"
    Algobattle will package everything in the program directories into a zip file. This may include unnecessary build
    artefacts, logs, program output, etc. It's best to remove any superfluous files (in particular, anything in your
    `.gitignore`) from the directories before running this command.

`project`
: Path to the Algobattle project containing the programs. Can either point directly to a project config file, or to
a folder containing one called `algobattle.toml`. Defaults to the current working directory.

`--team`
: Name of the team whose programs should be packaged. If there is only one team in this project, it will be selected
by default.

`--generator` and `--solver`
: Whether to package this particular program. Defaults to `#!py True`.

`--test` / `--no-test`
: Whether to test the programs before packaging them to make sure that they are building and running correctly.
Defaults to `#!py True`.
