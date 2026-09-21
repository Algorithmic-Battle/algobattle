# Creating a Problem File

Algobattle uses _Problem files_ to specify all the details of a problem formally, i.e. what instances and solutions
should look like, how to score them, how to decode and encode them, etc. These are Python files and leave a lot of room
for you to write them however you like. This overview will cover the basic structure of them and common use cases, for
more advanced features refer to later sections of the problem creation guide.

!!! example "Pairsum"
    Throughout this page we will use the Pairsum problem as our working example.

## Initializing the Project Folder

When students develop their programs they are typically working within an Algobattle project folder created by the CLI
tool from a `.algo` file. Our goal now is to create a brand-new project folder with problem files for our new problem.
Once we're done we can then package this into a `.algo` file and distribute it to our students.

To initialize the folder we also use the `algobattle init` command, but this time specify that we want to create a new
problem and its name.

```console
algobattle init --new --problem "Pairsum"
```

This creates a new folder named `Pairsum` with the following contents:

``` { .sh .no-copy }
.
└─ Pairsum
   ├─ generator/
   │  └─ Dockerfile
   ├─ results/
   ├─ solver/
   │  └─ Dockerfile
   ├─ .gitignore
   ├─ problem.py
   └─ algobattle.toml
```

Let us take a look at the contents of the `problem.py` file, which is where we will implement the problem logic.

``` { .py .title="problem.py" .no-copy }
"""The Pairsum problem module."""
from algobattle.problem import Problem, InstanceModel, SolutionModel, maximize # (1)!
from algobattle.util import Role


class Instance(InstanceModel): # (2)!
    """Instances of Pairsum."""

    ...

    @property
    def size(self) -> int:
        ...


class Solution(SolutionModel[Instance]): # (3)!
    """Solutions of Pairsum."""

    ...

    @maximize
    def score(self, instance: Instance, role: Role) -> float:
        ...


Problem( # (4)!
    name="Pairsum",
    min_size=1,
    instance_cls=Instance,
    solution_cls=Solution,
)
```

1. These lines import the needed parts of the Algobattle framework.
2. This class specifies what instances of the problem look like.
3. This class specifies what solutions of the problem look like.
4. The `Problem` constructor ties all the information together and creates the problem.

As you can see, the file is mostly empty now and only contains some bare-bones structure. The ellipses tell us where
we need to implement the basic problem specific code, though there also are more options for us to customize later on.

!!! tip "Type Checking"
    The Algobattle module is fully typed, but Python doesn't actually require you do include type hints in your own
    code. We strongly recommend still using type hints as much as possible since they prevent many bugs and make code
    easier to read. We will also make heavy use of type annotations to easily specify data formats.

## The Instance Class

Let's start by looking at the `Instance` class. This will specify what every instance of your problem should look like.
As you can see this class inherits from the `InstanceModel` utility class, which uses
[Pydantic](https://docs.pydantic.dev/latest/) to make instances that can easily be decoded to and from json files.

??? info "Advanced Usage"
    In the most general case they need to only inherit from the
    [`Instance`](../../api/problem.md#algobattle.problem.Instance) class and implement the
    [`Encodable`](../../api/util.md#algobattle.util.Encodable) protocol, but doing so manually is much more
    complicated and not needed for most problems. We will see how to use these classes in the
    [arbitrary i/o formats](io.md) guide.

!!! tip "Pydantic"
    Pydantic is a very powerful library with excellent support for many use cases. This can also make it harder to
    understand how exactly everything works and what the "best" way of doing something is. For now, we recommend just
    staying here and focusing on how Algobattle lets us use it. If you're curious and want to see how it works under the
    hood you can then go back to its documentation later.

### Instance Data

First we need to specify what an instance actually looks like. In our case it just is a list of natural numbers.
This means we want the json file of an instance to look something like this:

```json
{
    "numbers": [1, 3, 17, 95, 0, 24, 6]
}
```

I.e. it contains a single field called `numbers` which contains a list of non-negative integers. This can be copied to
the first ellipsis of the Instance class almost verbatim!

```py
class Instance(InstanceModel):
    """Instances of Pairsum."""

    numbers: list[int]

    @property
    def size(self) -> int: ...
```

Here we create a Python class attribute named after the key we want in the json file, and give it a type annotation that
matches the kind of data we want at that key. If a json file contains a key that is not listed here, or if it is missing
one of the keys listed here, the framework will assume that the given instance is malformed and reject it. Pydantic
also ensures that the values at each key also match the types specified in the class!

??? info "Unfamiliar with Python type annotations?"
    Here's some more examples of type annotations and what they mean:

    - `float`: a single real number.
    - `Literal["Ice Cream", "Cake", "Donuts"]`: one of `Ice Cream`, `Cake`, or `Donuts`, no other strings or any other
        values are permitted.
    - `tuple[int, str]`: a tuple of an integer and a string. Since json only knows lists this will look like
        `[123, "Cats"]` or `[-17, "Dogs"]`, but never something like `[1, 2]` or `["Wombats", "are", "great"]`.
    - `dict[str, int]`: a mapping of strings to integers, e.g. `{"Pasta": 1, "Pizza": 17, "Sushi": 5}`.
    - `set[list[str]]`: a set of lists of strings. Similar to tuples, json does not support sets so they will be encoded
        as plain lists, but with the requirement that no elements are duplicated and that order does not matter.

    In general, you can use most basic types on their own, with collections having the type they contain in square
    brackets after them.

!!! example "Example Instances"
    Here are some valid example instances:

    - `#!json {"numbers": [1, 2, 3]}`
    - `#!json {"numbers": [17, 0, 0]}`
    - `#!json {"numbers": [95, 74694, 65549, 6486681, 6513232135186, 651344168]}`

    These are invalid and will be rejected automatically:

    - `#!json {"numbers": [1, 2, 3], "other": 5}`
    - `#!json {}`
    - `#!json {"nums": [1, 2, 3]}`
    - `#!json {"numbers"`
    - `#!json {"numbers": [1.5, 2, 3]}`
    - `#!json {"numbers": 17}`

### Additional Validation

But there still is an issue with this instance definition, it says that the numbers can be any integers and not just
natural numbers. This means that `#!json {"numbers": [-1, -2, -3]}` would also be accepted! Another potential issue is
that Python allows arbitrarily large numbers in its `int` type, but many other languages make very large numbers hard to
work with. To make everything a bit fairer for different teams using different languages and not make winning a match
be based on exploiting corner case overflow bugs, we recommend also limiting the maximum size of the numbers, so they
can fit in a 64-bit integer. This can be done very easily by using the Algobattle utility types we provide in the
`algobattle.types` module. In our case we want `u64` for an unsigned 64-bit integer.

```py
from algobattle.types import u64  # (1)!


class Instance(InstanceModel):
    """Instances of Pairsum."""

    numbers: list[u64]

    @property
    def size(self) -> int: ...
```

1. Always remember to add imports at the top of the file for everything you use from an external module.

!!! tip "Integer Types"
    The `algobattle.types` module contains predefined types for all commonly found integer types. These are `u64`,
    `u32`, `u16` for unsigned integers that fit in 64, 32, and 16 bits and `i64`, `i32`, `i16` for the corresponding
    signed variants.

But there also are some properties that we cannot validate by just using one of the predefined types. The easiest way
to do that is to implement the `validate_instance` method. It will be called after all the basic properties of the
types have been validated and can then perform more complicated checks. For example, if we wanted to also add the
constraint that all the numbers are even we could add this:

```py
from algobattle.util import ValidationError


class Instance(InstanceModel):
    """Instances of Pairsum."""

    numbers: list[u64]

    def validate_instance(self) -> None:  # (1)!
        super().validate_instance()  # (1)!
        for number in self.numbers:
            if number % 2 != 0:
                raise ValidationError(
                    "A number in the instance is not even!",
                    detail=f"Odd number {number} was passed.",
                )

    @property
    def size(self) -> int: ...
```

1. The `validate_instance` method takes only the instance itself as an argument, and returns nothing.
2. Always include this line at the top of this method. It will call the parent's class validation logic to make sure
    that properties assured by it are actually enforced.

If the instance is valid this method should simply return nothing, if it is invalid it needs to raise a
`ValidationError`.

!!! note "Error Messages"
    You may notice the optional `detail` argument of the `ValidationError` exception.  When the logs are visible for
    everyone, accidentally leaking information about parts of an instance, may reveal the strategy of a team. On
    the other hand, when developing code, a team may nevertheless _want_ to see exactly what went wrong.

    The first argument will always be visible to everyone, while the `detail` field is hidden in match logs but visible
    in local test runs. This means that the first argument should only contain a basic description of the general error
    and detailed info should be in the `detail` argument.

Implementing this method is entirely optional. Many simpler problems like Pairsum do not need it at all since their
properties are easily encoded in just the predefined types.

### Instance Size

Each instance also has a specific _size_ that is used to limit the generating team so that it actually needs to produce
_hard_ instances and not just _big_ ones. In our case the size naturally just is the length of the list of numbers.
We specify what a specific instance's size is by implementing the `size` property in the Instance class.

```py
class Instance(InstanceModel):
    """Instances of Pairsum."""

    numbers: list[u64]

    @property
    def size(self) -> int:
        return len(self.numbers)
```

There are many more things you can customize here, but this is all you need to know to get started. If you want to take
a deeper dive, check out the advanced problem creation pages once you've got a feeling for everything.

## The Solution Class

The Solution class works very similar to the Instance class. Its job is to specify what solutions look like and how to
score them. The data encoding and decoding can again be done using Pydantic:

```py
class Solution(SolutionModel[Instance]):
    """Solutions of Pairsum."""

    indices: tuple[u64, u64, u64, u64]

    @maximize
    def score(self, instance: Instance, role: Role) -> float: ...
```

But note that we're actually looking for four different indices into the list in the input, not just any four numbers.
That means we need to validate that the numbers are valid indices (i.e. smaller than the length of the list) and are
all different from each other. We could again do that with a custom validation method, but we can also use some more
advanced utility types.

```py
class Solution(SolutionModel[Instance]):
    """Solutions of Pairsum."""

    indices: Annotated[tuple[SizeIndex, SizeIndex, SizeIndex, SizeIndex], UniqueItems]

    @maximize
    def score(self, instance: Instance, role: Role) -> float: ...
```

The first change is to use `SizeIndex` instead of a `u64`. This ensures that the numbers are valid indices into a list
of the length of the `size` of the instance. In our case the size is defined to be exactly the length of the list we
want to index, so this works perfectly. The other change is that we add a `Annotated[..., UniqueItems]` wrapped around
the actual type. This is a Python construct that lets us add some metadata to a type annotation. The `UniqueItems` data
will instruct Algobattle (again using Pydantic) to also validate that the items in the wrapped collection are different
from each other.

!!! tip "Annotated Metadata"
    Using the `Annotated[...]` construct to add metadata is a powerful way to define validation, but can also be very
    confusing to people new to the Python type system. We go over it in much more detail in the
    [advanced types](annotations.md#advanced-type-annotations) section.

We also need to check that the first two numbers actually have the same sum as the second two. This is best done with
a custom validation method:

```py
class Solution(SolutionModel[Instance]):
    """Solutions of Pairsum."""

    indices: Annotated[tuple[SizeIndex, SizeIndex, SizeIndex, SizeIndex], UniqueItems]

    def validate_solution(self, instance: Instance, role: Role) -> None:
        super().validate_solution(instance, role)
        first = instance.numbers[self.indices[0]] + instance.numbers[self.indices[1]]
        second = instance.numbers[self.indices[2]] + instance.numbers[self.indices[3]]
        if first != second:
            raise ValidationError("Solution elements don't have the same sum.")

    @maximize
    def score(self, instance: Instance, role: Role) -> float: ...
```

Note that this is now called `validate_solution` and takes not only the solution itself, but also the instance it is
trying to solve and the role of the team that created this solution as arguments.

!!! note "Role Argument"
    Most of the time the role argument won't be used to validate a solution. You must still have it listed in the
    argument list of the method for everything to work smoothly. Some problems use this to e.g. relax some condition for
    the solving team.

### Solution Score

Many problems not only care about a team providing a valid solution but also want them to compute the best solution they
can. For example, we might modify to not just want any four such numbers, but want the sum of each pair to be as big as
possible. For these problems we implement the `score` function. If we leave it out all solutions will be scored
equally.

```py
class Solution(SolutionModel[Instance]):
    """Solutions of Pairsum."""

    indices: Annotated[tuple[SizeIndex, SizeIndex, SizeIndex, SizeIndex], UniqueItems]

    def validate_solution(self, instance: Instance, role: Role) -> None:
        super().validate_solution(instance, role)
        first = instance.numbers[self.indices[0]] + instance.numbers[self.indices[1]]
        second = instance.numbers[self.indices[2]] + instance.numbers[self.indices[3]]
        if first != second:
            raise ValidationError("Solution elements don't have the same sum.")

    @maximize
    def score(self, instance: Instance, role: Role) -> float:
        return instance.numbers[self.indices[0]] + instance.numbers[self.indices[1]]
```

This method again receives the solution itself, the instance it solves, and the role of the team that generated it. It
needs to return a non-negative real number indicating how good the solution is. When using the `@maximize` decorator
(or using no decorator at all) bigger scores are considered better, if the problem instead asks for the smallest of
some value instead import and use the `@minimize` decorator.

## Constructing the Problem

Now that we have an Instance and a Solution class we can tie everything together using the Problem constructor.

```py
Problem(
    name="Pairsum",
    min_size=4,
    instance_cls=Instance,
    solution_cls=Solution,
)
```

In its most basic form it just takes the name of the problem, and both classes we defined above. Finally, it also takes
a number that defines what the smallest reasonable instance size for this problem can be. This is needed because in our
case there aren't any sensible problem instances that only contain 3 numbers since we're looking for two pairs of two
numbers in the list. So if a generator was asked to create an instance of size 3 they couldn't possibly do this and
would fail immediately. To prevent bugs like that fill in `min_size` with whatever the smallest size your problem can
properly operate at is.

In summary, our final Pairsum problem file looks like this

```py title="problem.py"
from typing import Annotated

from algobattle.problem import Problem, InstanceModel, SolutionModel
from algobattle.util import Role, ValidationError
from algobattle.types import u64, MinLen, SizeIndex, UniqueItems


class Instance(InstanceModel):
    """An instance of a Pairsum problem."""

    numbers: Annotated[list[u64], MinLen(4)]

    @property
    def size(self) -> int:
        return len(self.numbers)


class Solution(SolutionModel[Instance]):
    """A solution to a Pairsum problem."""

    indices: Annotated[tuple[SizeIndex, SizeIndex, SizeIndex, SizeIndex], UniqueItems]

    def validate_solution(self, instance: Instance, role: Role) -> None:
        super().validate_solution(instance, role)
        first = instance.numbers[self.indices[0]] + instance.numbers[self.indices[1]]
        second = instance.numbers[self.indices[2]] + instance.numbers[self.indices[3]]
        if first != second:
            raise ValidationError("Solution elements don't have the same sum.")


Problem(
    name="Pairsum",
    min_size=4,
    instance_cls=Instance,
    solution_cls=Solution,
)
```

## Creating a Description

Now that we've made the problem file to tell the framework how our problem works, we need to create a description file
to tell our students the same. This can be any file that just describes the problem in human-readable terms. It will be
packaged together with the problem file and distributed to the students. By default, Algobattle expects this file to be
named `description` with an appropriate file ending, e.g. `description.md`, `description.pdf`, etc.

!!! tip "Web Framework"
    When using the Algobattle web framework, Markdown files work best for this since they can be displayed inline on the
    problem page.

~~~md title="description.md"
# The Pairsum Problem

The Pairsum problem asks you to find two pairs of numbers in a list that have the same sum. I.e.:

**Given**: List `L = [z_1,...,z_n]`
**Question**: Are there pairwise different `a, b, c, d in [0,...,n-1]` such that `L[a] + L[b] = L[c] + L[d]`?

I.e. given a list of natural numbers the task is to find two pairs of these numbers with the same sum.
The `size` of an instance limits the length of the list of numbers.

The generator should create a hard to solve instance and a certificate solution to prove that such a pair of pairs
indeed exists. The generator should be able to efficiently find the solution for any input list.

## Instances
An instance just contains the list of numbers. For example:
```json
{
    "numbers": [1, 2, 3, 4, 5]
}
```

## Solutions
A solution contains a list with the four indices `a, b, c, d` in this order. For example:
```json
{
    "indices": [1, 4, 2, 3]
}
```
This is a valid solution since `L[1] + L[4] = 2 + 5 = 3 + 4 = L[2] + L[3]`.
~~~

## Packaging

To easily distribute your problem to your students you can use the Algobattle CLI like this:

```console
algobattle package problem
```

This creates a `pairsum.algo` file which contains all the info Algobattle needs to initialize a new project folder on
the student's computer with your problem. Note that it will then not only contain the problem file, but also the
description, and the Algobattle config file.

!!! info "A peek behind the curtain"
    This file really just is a zip file containing the mentioned files that have been preprocessed slightly. The file
    extension is there to indicate that you shouldn't pack or unpack these files manually since the CLI tool expects
    them to be formatted in a precise way.

!!! tip "Web Framework"
    This file is what the web framework expects you to upload, it will then be used to run matches on the server and be
    distributed to the students.
