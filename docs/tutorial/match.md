
# Running a match

## Overview

Now that we've got everything we need and have even written some working code we can try running an actual match.
A _match_ is basically Algobattle's way of determining whose code generates the hardest instances and solves them the
best. It does this by running everyone's generator against everyone else's solver in what is called a _battle_.

??? Example
    Let's say there are three teams Crows, Cats, and Otters. The battles will then look like this

    | Generating | Solving |
    |------------|---------|
    |   crows    |   cats  |
    |   crows    | otters  |
    |    cats    |  crows  |
    |    cats    | otters  |
    |  otters    |  crows  |
    |  otters    |   cats  |

!!! tip
    If there's only one team Algobattle will run a single battle with that team performing both roles. You can use this
    to easily try out how well your code performs.

Algobattle also lets course instructors customize what each battle looks like. This is usually done much more rarely
than changing up the problem, so you won't have to learn much more stuff! Throughout this page we will be using the
Iterated battle type since it's the default and explains things the best. The idea behind Iterated battles is that we
want to figure out what the biggest size is where the solving team can still correctly solve the generating team's
instances. We do this by first having the generator create an instance up to some particular size. Then the solving team
must solve this instance. If it manages to do so, we repeat this cycle (called a _Fight_) with a bigger maximum instance
size. At some point the instances will be so big that the solver can't keep up any more and produces a wrong solution.
The last size where the solving team still was correct becomes that team's score.

!!! info "More details"
    The process described above is the best way to explain this battle type, but it's not actually precisely how it
    works. You can find the actual process description in our [battle types](../advanced/battle_types.md) page.


## Let's get started

To run a match we just execute

```console
algobattle run
```

This will display a lot of info to the command line. We will now go through it all step by step and explain what
Algobattle is doing and what the interface is trying to tell us.

## Building programs

The first part of a match is building every team's programs. Depending on how complicated they are this may take a
little while. During this step Algobattle gets all the programs ready for execution, compiles and installs them, etc.

??? question "You can't just skip over what's actually happening!"
    Yes I can :wink:. The actual details of this are somewhat complicated if you're not familiar with Docker (and if
    you are, you'll have already figured out what's going on) so we recommend skipping over this for now. We recommend
    skipping over the details here for now and if you still want to learn more later you can check out the
    [advanced guide on Docker](../advanced/docker.md#building-images).

During this the interface will look something like this

```{.sh .no-copy}
{!> interface_build.txt !}
```

!!! bug "This looks much better with colours"
    Don't worry if you find this hard to read here, it should be a lot more readable in your terminal with proper
    alignment and colour rendering.

This should be fairly straightforward, the top progress bar tracks how many programs need to be built in total and
below we have a full listing of every participating team. There are two programs here since there is only one team with
a generator and a solver.

## The match itself

With the programs built, the actual match can start. While this is happening a lot of different things will be
displayed, so let's go through each of them on its own:

### Match overview

```console hl_lines="3-8"
{!> interface_match.txt!}
```

Right at the top you will see an overview over the whole match. This table lists every battle in the match, its
participants, and what the result of that match was. For the Iterated battle type the result just is the highest size
the solving team was able to solve.

Everything below this is specific to each battle. It starts off by just showing you who the generating and solving team
is.

### Current fight

```console hl_lines="12-16"
{!> interface_match.txt!}
```

On the left we have info on the current fight. What maximum size it is using, and basic data on the programs. Here we
can see that the generator has already run successfully using only half a second of the 20 it has, and the solver is
still running at the moment.

### Battle data

On the right we see some data specific to the battle type. If you want to learn what the Iterated type displays here,
check out its documentation in the [battle types page](../advanced/battle_types.md#iterated).

### Most recent fights

```console hl_lines="17-26"
{!> interface_match.txt!}
```

At the bottom we can see some more info on the last five fights. The score of a fight indicates how well the solver did,
with the Pairsum problem it can really only pass or fail, but some other problems judge the solution by e.g. how well it
approximates an optimal solution. The detail column will display the runtimes of the programs if everything went well,
or a short error message if some error occurred. Here we can see that all but the second to last fight happened without
issue, but in that one the solver didn't actually output a solution, and thus failed.

## Finishing the match

To get the full results you need to wait until the match is done running everything it needs to. But this can take quite
a while, if you want you can safely cancel it early by pressing ++ctrl+c++.
Algobattle will handle stopping any running programs and log the (partially) completed match to the file path it prints.
This file will also contain more detailed error messages that didn't fit on the command line interface for every error
that happened during the match.

Finally, the leaderboard is displayed. Points are allocated by comparing how well each team did against each other team.
