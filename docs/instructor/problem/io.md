# Arbitrary I/O Formats

So far we've always encoded our problem instances and solutions as json files, but Algobattle lets you also use
whatever other data types you want for your problems. This page will go through the implementation of such a problem and
explain every step in detail.

## Inheriting from Instance or Solution

To define a problem that uses json encoding we just inherit from `InstanceModel` or `SolutionModel`, these are actually
subclasses of `Instance` and `Solution` that combine their functionality with the Pydantic json parsing and data
validation. This means that if we want to use our own encoding or decoding logic, we can just inherit from the base
classes instead.

Throughout this page we will work on an example problem where instances are pictures and the task is to identify which
animal is in it. This means that we will use a json based solution and a custom encoding for the instances.
The starting point of our problem file then looks like this:

```py title="problem.py"
from typing import Literal

from algobattle.problem import Problem, Instance, SolutionModel

Animal = Literal["Cat", "Dog", "Duck", "Stingray", "Albatross", "Snake"]


class MyInstance(Instance):
    """Instances of Animal Detection."""

    ...

    @property
    def size(self) -> int: ...


class MySolution(SolutionModel[MyInstance]):
    """Solutions of Animal Detection."""

    found: Animal


Problem(
    name="Animal Detection",
    min_size=64,
    instance_cls=MyInstance,
    solution_cls=MySolution,
    with_solution=False,
)
```

??? note "Class Names"
    In this example we call our instance and solution classes different names to avoid clashes with the base classes
    from `algobattle.problem`. You could instead also import them under different names or use dotted imports.

??? note "No Generator Solution"
    The way we will implement this problem is by not requiring the generator to also submit a solution.
    This is just a choice we make for this particular example, you can also use custom data formats for problems that
    also require a generator solution.

## Implementing the Python Data

Every `MyInstance` object needs to hold the info it needs to encode the instance for the solver, score it, etc. In
our example this means that we need to somehow store the image in these Python objects and implement things like the
size property or validation and scoring methods using that. We will just use a basic
[data class](https://docs.python.org/3/library/dataclasses.html) and the
[pillow](https://pillow.readthedocs.io/en/stable/) image library.

```py title="problem.py" hl_lines="2 6 27-30"
from typing import Literal
from dataclasses import dataclass

from algobattle.problem import Problem, Instance, SolutionModel
from algobattle.util import Role
from PIL import Image


Animal = Literal["Cat", "Dog", "Duck", "Stingray", "Albatross", "Snake"]


@dataclass
class MyInstance(Instance):
    """Instances of Animal Detection."""

    image: Image.Image

    @property
    def size(self) -> int:
        return max(self.image.width, self.image.width)


class MySolution(SolutionModel[MyInstance]):
    """Solutions of Animal Detection."""

    found: Animal

    def validate_solution(self, instance: MyInstance, role: Role) -> None:
        super().validate_solution(instance, role)
        ...  # check that the correct animal is pictured


Problem(
    name="Animal Detection",
    min_size=64,
    instance_cls=MyInstance,
    solution_cls=MySolution,
    with_solution=False,
)
```

## The `Encodable` Protocol

We now need to tell Algobattle how it should encode our instances into files and how it should decode them from the
output of a program. For the first we just implement an `encode` method that takes the location on the file system where
the data needs to end up, and the role of the team that will read this data. We can either create a new folder at the
given path and then place as many files as we want in it, or create a single file at that path. You should never create
any files that aren't rooted at the given path, or are siblings of it, etc. The path we are given will have a plain
name without any file extension, the name itself cannot be changed, but an appropriate file extension should be
added.

```py hl_lines="11-13"
@dataclass
class MyInstance(Instance):
    """Instances of Animal Detection."""

    image: Image.Image

    @property
    def size(self) -> int:
        return max(self.image.width, self.image.width)

    def encode(self, target: Path, role: Role) -> None:
        full_path = target.with_suffix(".png")  # (1)!
        self.image.save(full_path)  # (2)!
```

1. Add the `.png` file extension
2. Write the image to the target location using pillow.

!!! warning "Super Call"
    Do not call `super().encode()` in this method. The `Instance` class's `encode` method is abstract and
    will just raise an error. This is different to the validation methods.

??? note "Role"
    We can use the role argument to encode data differently based on who is going to read it. Most of the time this
    argument won't be used, but it can be helpful when working with advanced battle types and problems.

The other method we need to implement is the `decode` class method. It takes a path pointing to where the program should
have placed its output and then returns a problem instance object. It also again takes the role argument and an
additional one specifying the maximum allowable size in this fight.

!!! info "Maximum Size"
    You do not need to validate that the size of the instance actually is smaller than the maximum allowed size. This
    will be done in a later step by Algobattle itself. In most use cases the `max_size` argument won't be needed, but
    it can be helpful to e.g. prevent stalling in the decoding process when trying to read abnormally large files.

```py hl_lines="15-24"
@dataclass
class MyInstance(Instance):
    """Instances of Animal Detection."""

    image: Image.Image

    @property
    def size(self) -> int:
        return max(self.image.width, self.image.width)

    def encode(self, target: Path, role: Role) -> None:
        full_path = target.with_suffix(".png")
        self.image.save(full_path)

    @classmethod
    def decode(cls, source: Path, max_size: int, role: Role) -> Self:
        full_path = source.with_suffix(".png")  # (1)!
        try:
            image = Image.open(full_path)  # (2)!
        except FileNotFoundError:
            raise EncodingError("The image file does not exist.")
        except UnidentifiedImageError:
            raise EncodingError("The image cannot be decoded.")
        return cls(image)  # (3)!
```

1. Add the same file extension we used when encoding the data.
2. Read the image using pillow.
3. Return a new object of the instance class.

!!! warning "Super Call"
    Do not call `super().decode()` in this method. The `Instance` class's `decode` method is abstract and
    will just raise an error. This is different to the validation methods.

??? note "Generator Solution"
    If your problem does use generator solutions then you do not need to decode them in this method. The path you
    receive points only to the instance data and the generator's solution will be decoded using the solution class's
    `decode` method.

When the data cannot be decoded properly or is missing you should always raise an `EncodingError` from
`algobattle.util` with appropriate error messages. This can also be in cases where you can in principle decode the
data, but it does not conform to some specification that's part of your problem. For example, when using the usual
base classes to decode json files we also apply Pydantic validation as part of this step.

!!! warning "Decoding Solutions"
    Solutions follow exactly the same encoding protocol, but additionally receive an argument on their decode method
    that contains the instance this solution is for. This means that you need to implement a `decode` method like this:

    ```py
    class ExampleSolution(Solution[ExampleInstance]):
        @classmethod
        def decode(cls, source: Path, max_size: int, role: Role, instance: ExampleInstance) -> Self: ...
    ```

## Specifying the I/O Schema

We optionally can also add a class method that specifies what exactly our instances should look like. This information
will not be used by the Algobattle framework itself, but can be used by your students. It should be a textual and
machine-readable description of what this instance's or solution's data needs to conform to. In the case of the usual
json data it is their [OpenAPI schema](https://swagger.io/specification/). What exactly this should look like depends
heavily on the data encoding techniques you are using and in many cases there simply is no reasonable schema. In those
cases it's best to just not implement this method.

This is the signature of this method:

```py
class ExampleInstance(Instance):
    @classmethod
    def io_schema(cls) -> str | None: ...
```
