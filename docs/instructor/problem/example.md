# A Complex Example
## The 2D Knapsack Problem
In this section, we implement the so called 2D Knapsack Problem in its entirety,
starting from scratch and ending with a packaged problem archive that
can be handed out to others.

!!! abstract "Usage of Complex Features"
    In parts of this we will use rather advanced features of Algobattle. We recommend looking up the more detailed
    explanations of anything you're unsure about in its corresponding section.

To start, let us define the problem. We are given a two-dimensional, rectangular
space with an integer length and width, each of size at least one. We now
want to pack a number of smaller rectangles into this space, such that no two 
pieces overlap and such that as much space is covered as possible. Each
piece may be rotated by 90 degrees.

An instance for this problem thus consists of the dimensions of the knapsack as
well as a limited set of rectangular items. A solution for this problem then
describes where which piece should be placed and if it should be rotated by 90
degrees before being placed. The size of the solution is then the total area
covered.

## Starting Off
As in the previous section, we use the `algobattle` cli to construct a dummy
problem folder for us. Since we are interested in later writing a dummy
generator and dummy solver in python, we let the cli generate a stub of them
for us as well as follows:

```console
~ algobattle init --new -p "2D Knapsack" -l python
Created a new problem file at 2D Knapsack/problem.py
Created a python generator in 2D Knapsack/generator
Created a python solver in 2D Knapsack/solver
Initialized algobattle project in 2D Knapsack
```

We navigate into the newly created folder named `2D Knapsack`, which has the
following file structure:

``` { .sh .no-copy }
.
└─ 2D Knapsack
   ├─ generator/
   │  ├─ .gitignore
   │  ├─ Dockerfile
   │  ├─ generator.py
   │  └─ pyproject.toml
   ├─ results/
   ├─ solver/
   │  ├─ .gitignore
   │  ├─ Dockerfile
   │  ├─ pyproject.toml
   │  └─ solver.py
   ├─ .gitignore
   ├─ problem.py
   └─ algobattle.toml
```

Before we implement anything, we should take the time to specify exactly how
an instance should look like. This means specifying the names of each key,
their function and which values are legal for each.

First of all, an instance should contain the dimensions of the knapsack that is
to be packed. For this, we introduce two keys `height` and `width`, and would
like each to be an integer of value at least one and at most of value `2**64`.

Secondly, we need to describe the items that are to be packed. Each item itself
has a height and a width, which should again each be of integer size at least
one. As an added restriction, we only want to allow items that are at all able
to fit into the knapsack, so as not to allow spamming a solver with items that
can never be part of a valid solution. To spare us some headache in the validation
step of the instance, we demand each item to fit into the knapsack without any 
rotation, as a sort of normalization of the instance.

Next, we need to specify the contents of a valid solution file. This is in
principle quite simple: We are interested in a list specifying which of 
the items of the instance
* should be placed in the knapsack
* at which position
* being rotated or not.

We will be lazy and define a dictionary `packing` that maps the index of items
to a three-tuple, as described.

## Writing a Mock Generator and Solver
Before we start writing any problem code, we write a mock generator and a mock
solver. This helps us do plausibility checks while writing the actual problem file
and is not required for the finished problem file.

We start with filling in the generator.

```py title="generator/generator.py"
"""Main module, will be run as the generator."""

import json
from pathlib import Path


max_size = int(Path("/input/max_size.txt").read_text())

instance = {"height": 4, "width": 3, "items": [[1, 3], [4, 3], [3, 3], [3, 2], [1, 3]]}

solution = {"packing": {0: [0, 0, "unrotated"], 3: [1, 0, "unrotated"], 4: [1, 2, "rotated"]}}


Path("/output/instance.json").write_text(json.dumps(instance))
Path("/output/solution.json").write_text(json.dumps(solution))
```

We made sure that the solution is not unique for the given instance
to make sure that the framework is able to compare two different solutions.
We next fill in the solver.

```py title="generator/solver.py"
"""Main module, will be run as the solver."""

import json
from pathlib import Path


instance = json.loads(Path("/input/instance.json").read_text())

solution = {"packing": {1: [0, 0, "rotated"]}}


Path("/output/solution.json").write_text(json.dumps(solution))
```

We are now able to immediately test any code that we write.

## Handling Instances
We already know that we expect three keys in any instance: A `height`,
a `width` and a list of `items`.

///note
For brevity, the following code snippets do not include all necessary imports.
We provide the complete content of the `problem.py` at the end of this section.
///

Our first approach uses only very rough type annotations for our expected keys
and does a lot of the validation of the instance explicitly.

```python
"""The 2D Knapsack problem module."""

from algobattle.problem import Problem, InstanceModel, SolutionModel, maximize
from algobattle.util import Role, ValidationError
from algobattle.types import u64


class Instance(InstanceModel):
    """Instances of 2D Knapsack."""

    height: u64
    width: u64

    items: list[u64, u64]

    def validate_instance(self) -> None:
        super().validate_instance()
        if self.height < 1 or self.width < 1:
            raise ValidationError("The knapsack is smaller than allowed!")
        if any(item[0] < 1 or item[1] < 1 for item in self.items):
            raise ValidationError("An item of the instance is smaller than 1x1!")
        if any((item[0] > self.height or item[1] > self.width) for item in self.items):
            raise ValidationError("An item of the instance cannot fit in the knapsack!")

    @property
    def size(self) -> int:
        return len(self.items)
```

We can clean this code up by tightening up the annotations a bit. 

```python
"""The 2D Knapsack problem module."""

from pydantic import Field
from typing import Annotated

from algobattle.problem import Problem, InstanceModel, SolutionModel, maximize
from algobattle.util import Role, ValidationError
from algobattle.types import u64, Interval, InstanceRef


item_height = Annotated[int, Interval(ge=1, le=InstanceRef.height)]
item_width = Annotated[int, Interval(ge=1, le=InstanceRef.width)]
point = tuple[item_height, item_width]


class Instance(InstanceModel):
    """Instances of 2D Knapsack."""

    height: u64 = Field(ge=1)
    width: u64 = Field(ge=1)

    items: list[point]

    @property
    def size(self) -> int:
        return len(self.items)
```

As you can see, we have moved all explicit checks from the `validate_instance`
method into the annotations. Do note that by using the `InstanceRef` import,
we are able to use the values of some keys to annotate other keys!

///note
If you are not familiar with pydantics annotations, we recommend
using the [pydantic documentation](https://docs.pydantic.dev/2.4/concepts/models/)
as a reference. As you have seen in the previous iteration of the code,
they are not essential, but very helpful to reduce code clutter and potential
mistakes.
///

This is already everything we need to implement for the instance. The `size`
method ensures that the number of items does not exceed the allowed limit given
by the instance size. We next turn to the solutions.

## Handling Solutions
The `packing` key is slightly more involved to construct. To
recapitulate, we would like this key to be a dictionary that maps
indices of items to a two-dimensional position and an indicator
whether they should be rotated. We use a similar approach as for the
`items` list. We additionally import the `Literal` class from the
`typing` module as well as the `SizeIndex` type alias from
`algobattle.types`.

```python
position_height = Annotated[int, Interval(ge=0, lt=InstanceRef.height)]
position_width = Annotated[int, Interval(ge=0, lt=InstanceRef.width)]
rotation = Literal["unrotated", "rotated"]


class Solution(SolutionModel[Instance]):
    """Solutions of 2D Knapsack."""

    packing: dict[SizeIndex, tuple[position_height, position_width, rotation]]
```

This of course does not at all ensure that the given solution is valid, yet.
We did not yet check whether items overlap or extend beyond the boundaries
of the knapsack. Since these checks are arguably beyond the scope of simple
type checking, we implement these tests explicitly in the `validate_solution`
method. For convenience, we import the `itertools` library.

```python
def validate_solution(self, instance: Instance, role: Role) -> None:
    flattened_packing = []
    for index, (pos_height, pos_width, rotation) in self.packing.items():
        item_height = instance.items[index][0 if rotation == "unrotated" else 1]
        item_width = instance.items[index][1 if rotation == "unrotated" else 0]

        height_endpoint = pos_height + item_height
        width_endpoint = pos_width + item_width
        flattened_packing.append((index, pos_height, height_endpoint, pos_width, width_endpoint))

    if height_endpoint > instance.height or width_endpoint > instance.width:
        raise ValidationError(
            "Item extends the knapsack boundaries.",
            detail=f"Item {index} was placed at position ({pos_height, pos_width}), extending the knapsack boundaries.",
        )

    for item, other_item in itertools.combinations(flattened_packing, 2):
        if item[1] < other_item[2] and item[2] > other_item[1]:
            if item[3] < other_item[4] and item[4] > other_item[3]:
                raise ValidationError("Two items overlap.", detail=f"Items {item[0]} and {other_item[0]} overlap.")
```

We are almost done writing the problem class. The next step is to tell
the framework what the quality of a solution is, i.e. which values it
should compare when given two solutions to determine which is the better one.

For this, we overwrite the `score` method. We have access to the solution
via the `self` argument, access to the instance via the `instance` argument
and can even decide to judge the certificate solution of the generator and
a solvers solution differently, via the `role` argument, e.g. to give the
solver some additional slack.

```python
    @maximize
    def score(self, instance: Instance, role: Role) -> float:
        area = 0
        for index in self.packing:
            area += instance.items[index][0] * instance.items[index][1]
        return area
```

You can find the complete contents of the `problem.py` at the end of this
tutorial section.

## Best Practice: Writing Tests
Now that we have created a problem file, it is time to see if it
does what we want it to do. The most straightforward sanity check
is to run the mock generator and solver that we have written
previously.

///note
If you did not generate the problem folder as we did in this tutorial,
make sure that a team is entered in the `algobattle.toml` file that
utilizes the solver and generator that we wrote!
///

For this, we can use the `algobattle test` command. This command
builds the generators and solvers of the configured teams and
executes a single run of them at the minimum size that was configured
for the problem.

Running this command does however produce an issue:
```console
~ algobattle test
Testing programs of team Rats
Generator built successfully
Generator didn't run successfully
Solver built successfully
Cannot test running the solver
You can find detailed error messages at results/test-2024-01-01_12-35-10.json
```

So what went wrong? Looking into the log files reveals the issue.

```json
{
    "Rats": {
        "generator_run": {
            "type": "ValidationError",
            "message": "Instance is too large.",
            "detail": "Generated: 5, maximum: 1"
        }
    }
} 
```

We wrote a generator and solver that run on an instance with five items,
but proclaimed in the `problem.py` that any instance with at least one 
item is valid:

```python
Problem(
    name="2D Knapsack",
    min_size=1,
    instance_cls=Instance,
    solution_cls=Solution,
)
```

Should we thus change our generator and solver? We do not have to,
as the `algobattle test` command allows us to run the test on a specific
instance size:

```console
~ algobattle test --size 5
Testing programs of team Rats
Generator built successfully
Generator ran successfully
Solver built successfully
Solver ran successfully
```

This tells us that the combination of our problem description
with a small, hand-crafted instance behaves as expected. It is at this
stage where most of the errors in the code come to light. You
can use the log files written into the `results` folder to assist
you in debugging your code. You may find at this stage that it does
pay off to write detailed `ValidationError` exception messages.

Just because our single, hand-crafted test ran through, this does not
mean that our code is without any conceptual errors. Especially when
giving your problem file to other people, who will likely spend much more
time dissecting your code and descriptions to learn how to write their
own programs, many unexpected issues with your code may come to light.

To mitigate some of the reports of illegal inputs that are nevertheless
accepted by your code, legal inputs that are rejected by your code, or worst
-- code that crashes your validation code -- it is a good idea to write a few
unittests.

We do not want to dive into too much detail on how you could test your
code, how much coverage may be desirable and related topics, as this
goes well beyond the scope of this tutorial. Testing code is a topic
about which volumes have been written by authors who are much more
knowledgeable about the topic as we could claim to be.

Thus, we only talk about how to best interface the problem that we
have designed, so that you can then use this knowledge to write
your own tests. We use the `unittest` module from the standard library
for this part of the tutorial.

We create a file `tests.py` in the `2D Knapsack` folder, with generic
scaffolding.

```py title="tests.py"
"""Tests for the 2D Knapsack problem."""

import unittest

from algobattle.util import Role

from problem import Instance, Solution, ValidationError


class Tests(unittest.TestCase):
    """Tests for the 2D Knapsack problem solution class."""

    ...


if __name__ == "__main__":
    unittest.main()
```

You can then access all additional helper methods that you may have
added to the `Instance` and `Solution` classes as you would normally do.

If you would like to test the validation methods, i.e. `validate_instance`
and `validate_solution`, you could do so as follows.

Assume, just for the sake of being able to give an example, that we would have
added a `validate_instance` method to the `Instance` class with the following,
rather nonsensical content:

```python
# This method is just for demonstration purposes.
def validate_instance(self) -> None:
    super().validate_instance()
    if self.height != 1:
        raise ValidationError("The knapsack is not of height 1!?")
```

This rather silly method raises a validation error whenever the
height of the knapsacks is unequal to one.

```python
# Sample test for the validate_instance method
def test_knapsack_height_not_silly(self):
    with self.assertRaises(ValidationError):
        faulty_instance = Instance.model_validate({"height": 2, "width": 1, "items": [(1, 1)]})
        faulty_instance.validate_instance()


# Sample test for the validate_solution method
def test_item_overlap(self):
    instance = Instance(height=1, width=1, items=[(1, 1), (1, 1)])
    with self.assertRaises(ValidationError):
        faulty_solution = Solution.model_validate({"packing": {0: (0, 0, "unrotated"), 1: (0, 0, "unrotated")}})
        faulty_solution.validate_solution(instance, Role.generator)
```

You can test the `size` function of the `Instance` class
and the `score` function of the `Solution` class as you would test any other
method.

If you use the `unittest` module, you can then run these tests by
executing `python -m unittest` in the `2D Knapsack` folder.

## Writing a Description

We are done writing code for the problem. Now, it is a good idea
to write a description file that tells the users that should work
on the problem what it is about. This includes explaining the general
idea and, more importantly, how the expected I/O is defined.

We recommend creating a file in the `2D Knapsack` folder named `description.md`,
as this file name is automatically picked up by the packaging step 
that we will handle in the next step.

///note
If you use the `algobattle-web` framework, the contents of this file
will be displayed to your users when they click on the respective
problem tab.
///

## Packaging Everything Together

Now that our code is tested and documented, we are ready to hand it out!
For this, we can again use the `algobattle` cli, which wraps up the
`problem.py`, the `algobattle.toml` and the `description.md` into a file
that others can work on.

```console
~ algobattle package problem
Packaged Algobattle project into /path/to/working/dir/2D Knapsack/2d_knapsack.algo
```

///note
The `algobattle.toml` gets truncated during the packaging step. Only the `[match]`
entries remain.
///

## The Completed problem.py File
This is the final content of the `problem.py` that we have created.

```py title="problem.py"
"""The 2D Knapsack problem module."""

import itertools
from pydantic import Field
from typing import Annotated, Literal

from algobattle.problem import Problem, InstanceModel, SolutionModel, maximize
from algobattle.util import Role, ValidationError
from algobattle.types import u64, Interval, InstanceRef, SizeIndex


item_height = Annotated[int, Interval(ge=1, le=InstanceRef.height)]
item_width = Annotated[int, Interval(ge=1, le=InstanceRef.width)]
point = tuple[item_height, item_width]


class Instance(InstanceModel):
    """Instances of 2D Knapsack."""

    height: u64 = Field(ge=1)
    width: u64 = Field(ge=1)

    items: list[point]

    @property
    def size(self) -> int:
        return len(self.items)


position_height = Annotated[int, Interval(ge=0, lt=InstanceRef.height)]
position_width = Annotated[int, Interval(ge=0, lt=InstanceRef.width)]
rotation = Literal["unrotated", "rotated"]


class Solution(SolutionModel[Instance]):
    """Solutions of 2D Knapsack."""

    packing: dict[SizeIndex, tuple[position_height, position_width, rotation]]

    def validate_solution(self, instance: Instance, role: Role) -> None:
        flattened_packing = []
        for index, (pos_height, pos_width, rotation) in self.packing.items():
            item_height = instance.items[index][0 if rotation == "unrotated" else 1]
            item_width = instance.items[index][1 if rotation == "unrotated" else 0]

            height_endpoint = pos_height + item_height
            width_endpoint = pos_width + item_width
            flattened_packing.append((index, pos_height, height_endpoint, pos_width, width_endpoint))

        if height_endpoint > instance.height or width_endpoint > instance.width:
            raise ValidationError(
                "Item extends the knapsack boundaries.",
                detail=f"Item {index} was placed at position ({pos_height, pos_width}), extending the knapsack boundaries.",
            )

        for item, other_item in itertools.combinations(flattened_packing, 2):
            if item[1] < other_item[2] and item[2] > other_item[1]:
                if item[3] < other_item[4] and item[4] > other_item[3]:
                    raise ValidationError("Two items overlap.", detail=f"Items {item[0]} and {other_item[0]} overlap.")

    @maximize
    def score(self, instance: Instance, role: Role) -> float:
        area = 0
        for index in self.packing:
            area += instance.items[index][0] * instance.items[index][1]
        return area


Problem(
    name="2D Knapsack",
    min_size=1,
    instance_cls=Instance,
    solution_cls=Solution,
)
```