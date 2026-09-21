# Writing programs

## Problems

Now that we've got our project setup we can take a look at what we actually need to do: solve some problem. In this page
we'll work with the [Pairsum problem](https://github.com/Benezivas/algobattle-problems/tree/main/problems/pairsum). It's
a nice and easy starting point to get familiar with things, but you can also jump right into things with the problem
your course instructors gave you.

### What is a problem?

The Algobattle lab course is about solving algorithmic problems. So what is that exactly? From a theoretical computer
science perspective this doesn't have a clear answer, there are decision problems, function problems, optimization
problems, etc. What all of them share is that a problem is a description of what its instances look like, and what
correct solutions to them are.

This idea is what Algobattle works with, a problem really is just some specification of what _instances_ look like and
what _solutions_ of these are. For Pairsum this is very straightforward, each instance is a list of natural numbers and
a solution is two pairs of them that have the same sum. For example, in the list `1, 2, 3, 4, 5` we find `2 + 5 = 3 + 4`.
Unfortunately computers aren't quite clever enough to just take such an abstract definition and work with it directly,
so each Algobattle problem also defines how instances and solutions should be encoded/decoded. Pairsum uses json for this,
so the example above looks like this:

!!! example "Example instance"

    ```json
    {!> pairsum_instance.json!}
    ```

!!! example "Example solution"

    ```json
    {!> pairsum_solution.json!}
    ```

Where the solution is the list of the indices of the numbers that we found, 2 is at index 1, 5 at 4, etc.

### What do we need to do?

Previously we've said that the code we're going to write will solve problems, but that is only half of the truth. What
we actually need to do is write two different programs for each problem, one that _generates_ instances and one that
_solves_ them. In a stroke of creativity typical for computer science we'll call these the _generator_ and the _solver_
and use the correspondingly named subfolders for them.

??? info "Project config"
    This is why the `teams` table in the project config has that structure. It tells Algobattle which teams' programs
    can be found where.

## Generator

### Setup

The first step in writing a program is deciding what language you want to use. Algobattle lets you choose whatever
language you want, whether that be Python or rust, or even more esoteric choices like Brainfuck or PROLOG. But it's a
lot easier to use one of the more common languages since it comes with some project templates for them. The list of
these is:

- Python
- Rust
- C
- C++
- C#
- JavaScript
- Typescript
- Java
- Go

!!! failure "Can't find your favourite language?"
    If the language you want to use isn't on here you can still use it, but you have to set some things up yourself.
    It's probably easier to get started with one of these first and then once you're familiar with everything switch to
    what you want to stick with.

??? tip "Help us make Algobattle better"
    Some languages either have no templates or some very bare-bones ones. This is mainly just because we aren't familiar
    enough with every language to provide better support. If you want to help us out make Algobattle even more awesome
    you can open an issue or submit a pull request on [our GitHub](https://github.com/Benezivas/algobattle) with a
    better template for your language.

We can then rerun the project initialization step and also tell it what language we want to use, Python in this example.
Since the project is already initialized we can just omit the `--problem` option to reuse the current setup.

```console
algobattle init --generator python
```

!!! info "Overriding data"
    Whenever you tell Algobattle to do something that would override already existing files it will ask you if you want
    to continue. Make sure that you only confirm if you don't need these files any more. In this example the data is just
    the initially auto-generated file we made when we set up the project folder, so we can safely replace it with the
    python template.

!!! tip "No need to repeat yourself"
    You can directly specify the languages you want to use when unpacking the problem spec file. We're only doing it in
    several steps here to explain every part on its own.

Our project folder should now look something like this

``` { .sh .no-copy }
.
└─ Pairsum
   ├─ generator/
   │  ├─ .gitignore    
   │  ├─ Dockerfile
   │  ├─ generator.py
   │  └─ pyproject.toml
   ├─ results/
   ├─ solver/
   │  └─ Dockerfile
   ├─ .gitignore
   └─ algobattle.toml
```

The important file here is `generator.py`, we need to put the code that we want to run as our generator in there.

??? question "What's `pyproject.toml`?"
    This is the file that Python uses to specify package metadata such as dependencies, project names, etc. It's
    already filled out with the data we need so we can just leave it as is for now.

??? question "What's `Dockerfile`?"
    This is the file that specified what Docker is supposed to do with our code. What exactly Docker does and what the
    Dockerfile says is rather complicated and not super important for us right now. It's explained in detail in the
    [Docker guide](../advanced/docker.md).

### What it needs to do

When we look in there it's rather empty right now:

```py title="generator.py"
"""Main module, will be run as the generator."""

import json
from pathlib import Path


max_size = int(Path("/input/max_size.txt").read_text())  # (1)!


instance = ...
solution = ...


Path("/output/instance.json").write_text(json.dumps(instance))  # (2)!
Path("/output/solution.json").write_text(json.dumps(solution))
```

1. This opens the input file and parses it into an integer.

2. This writes the generated instance/solution as correctly formatted json to the output file.

The first thing that stands out is that we read from and write to some rather weird files. This is very intentional!
When Algobattle is run your program won't see the actual filesystem of your computer but a more or less empty Linux
install. It will also see two special folders there: `/input` and `/output`. As their names suggest these are responsible
for holding the input to the program and where Algobattle looks for its output.

So if a generator's job is to just create some difficult instance, why is it getting any input? This is because in
principle a generator could make its job very easy by not actually making _hard_ instances but just making _big_ ones.
Finding pairs of numbers with the same sum is going to be much harder in a 10000 number long list than one with only 10
after all. To make things more comparable and not just about who can write the most data to a file Algobattle forces
us to stick to some given upper limit of size of instance we make.

!!! info
    Usually your generator will be called with various different instance sizes, don't assume that it will always be the
    same. But on the other hand, you can always output an instance that is smaller than the asked for maximum size.

??? question "What exactly is an instance's size?"
    The exact definition of an instance's size depends on the particular problem. Most of the time it is what you'd
    intuitively understand it to mean though. In Pairsum's case it is the length of the list, practically all graph
    problems use the number of vertices, etc. If you're unsure check the problem description or ask your course
    instructors.

The code then writes things to the output directory, but it doesn't just write the instance, it also writes a solution.
It might seem weird at first, but many problems do require the generator to not only come up with an instance, but also
solve it. This is to make sure that the instance does indeed have a solution. Otherwise, we could just make some list
of numbers were no two pairs have the same sum and then always win no matter how good the other teams' solvers are!


### Writing the code

Now comes the hardest part, writing the code that actually does all that! What exactly that looks like will depend on
the particular problem you're working with, the language you chose, your workflow, etc. The great part is that Algobattle
lets you have a lot of freedom here, you are completely free to write the code how you want to. To keep going with this
tutorial we've provided an example generator here, but the particularities of it aren't super important for you to
understand.

!!! example "Example generator"
    An easy way to make a generator for Pairsum is to just output a bunch of random numbers:

    ```python title="generator.py"
    {!> pairsum_generator/start.py !}
    ```

    1. Generate `max_size` many random numbers in the 64-bit unsigned integer range.

    2. Pairsum expects a json object with a single key, `numbers` that contains the list of numbers.


    But if we do that we'd then have to also actually solve this instance and if we're particularly unlucky that might not
    even be possible! So it's better if we don't make the entire list random and insert a handcrafted solution into the list:

    ```python title="generator.py" hl_lines="10 15-25"
    {!> pairsum_generator/main.py !}
    ```

    1. We now use four fewer random numbers

    2. Create four numbers such that a + b = c + d

    3. Insert them into the list at random places

### Trying it out

Now that we have an actual program we're ready to test it out by running

```console
algobattle test
```

This tests both the generator and the solver, so it's expected that it shouts at us right now about the solver not
working since we haven't written that yet. If your generator is written correctly the build and run tests for it should
complete without issue though. If something isn't working quite right you will find the particular error message in the
json document it links to.

## Solver

With a working generator all that's missing is a solver. During a match this program will get the instances other teams'
generators have created and be asked to solve them. In this example I will use rust for this, but you can again choose
any language you like. First we run the initialization command again

```console
algobattle init --solver rust
```

The project then looks like this

``` { .sh .no-copy }
.
└─ Pairsum
   ├─ generator/
   │  ├─ .gitignore    
   │  ├─ Dockerfile
   │  ├─ generator.py
   │  └─ pyproject.toml
   ├─ results/
   ├─ solver/
   │  ├─ src
   │  │  └─ main.rs
   │  ├─ .gitignore
   │  ├─ Cargo.toml
   │  └─ Dockerfile
   ├─ .gitignore
   └─ algobattle.toml
```

We can again see a similar structure to the Python template, but this time it's using a slightly different layout.

??? question "What's `Cargo.toml`?"
    This is what rust's tool Cargo uses for project specification. We can again ignore the contents of this for now.

### Writing the code

The solver takes an instance and should produce a solution for it. Similar to the generator these will be in the
`/input` and `/output` directory, but this time called `/input/instance.json` and `/output/solution.json` as you'd
expect. Since we're already familiar with this I/O structure we can get right into writing the actual program.

This will again widely vary based on how you choose to do things, We've got our rust example solver here:

!!! example "Example solver"
    This solver just iterates over all possible combinations of four numbers in the input list and checks if they form
    a valid pair. It's horribly inefficient but will do for now :grin:

    ```rust title="main.rs"
    {!> pairsum_solver/main.rs !}
    ```

    1. This tells rust how to destructure the json input

    2. And this how to serialize the output

    3. Iterate over all possible combinations of four indices

    4. If the pairs have the same number we output them as the solutions

    !!! note
        This program uses itertools so we have to run `cargo add itertools` inside the solver directory to add it to
        our dependencies.

    ??? question "Not familiar with Rust?"
        If you're not familiar with Rust this program probably looks pretty intimidating, but don't worry you won't need to
        understand the details of this program.


### Trying it out

Now we can try our programs out again

```console
algobattle test
```

This time it should run without any errors. If that doesn't work for you, there's error messages in the linked json file.

## Packaging the Programs

You may want to share your code with e.g. your lab instructors. The best way to do that is to package them into Algobattle
program files. We do this by running

```
algobattle package programs
```

!!! note "Using the web framework"
    If your lab is using the web framework, these files are what you need to upload to have your programs run in the
    matches.

!!! tip "Keep program sizes down"
    Algobattle will package everything in the program directories. This may include unnecessary build artefacts, logs,
    program output, etc. It's best to remove any superfluous files (in particular, anything in your `.gitignore`)
    from the directories before running this command.

!!! tip "A peek behind the curtain"
    These files again are just `zip` files containing everything in your programs' folders in a specific format.

This will create two `.prog` files that contain all the data Algobattle needs to run our programs. We can then easily
share our code using just these files, or upload them to the Algobattle website.
