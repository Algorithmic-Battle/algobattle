# Advanced Features

This page is a loose collection of various more advanced features of the problem creation process.

## Submodels

So far we've just used tuples to group multiple pieces of data together. For example, we defined an edge as just a tuple
of two vertices. This works great for very simple types when it's clear what each element of the tuple means, but can
become very confusing quickly. Let's say we want to define a problem where rectangles are placed in a 2D coordinate
system. These are then defined by four integers: width, height, and x and y position. We could now define the instances
like this

```py
class Instance(InstanceModel):
    rectangles: list[tuple[int, int, int, int]]
```

but we, and more importantly our students, will then have to always remember the order we put those numbers in. To
prevent bugs caused by this we can also define a helper class that inherits from `BaseModel` in `algobattle.util`.
This will then not have the instance or solution specific stuff added, but will also allow us to create json validation
specifications just like in those classes.

```py
from algobattle.util import BaseModel


class Rectangle(BaseModel):
    x: int
    y: int
    width: int
    height: int


class Instance(InstanceModel):
    rectangles: list[Rectangle]
```

!!! warning
    The Pydantic package also exports a class called `BaseModel` which offers similar functionality. Always
    inherit from the class Algobattle provides since it includes additional settings that are important for everything
    to function correctly.

Pydantic then expects a json object at the places where you use these types with keys and values matching the attributes
found in the class. For example, a valid instance json file for the above class can look like this:

```json title="instance.json"
{
    "rectanlges": [
        {
            "x": 3,
            "y": 2,
            "width": 5,
            "height": 2
        },
        {
            "x": 0,
            "height": 17
            "width": 5,
            "y": -2,
        }
    ]
}
```

## External Dependencies

You may want to import some additional python libraries to use in your problem file, such as
[networkx](https://networkx.org/) when implementing a more complicated graph problem. To do this we not only have to add
the import statement in the `problen.py` file, but also include it in the list of dependencies in the project config.

```toml title="algobattle.toml"
[match]
problem = "Some Graph Problem"

[problem]
dependencies = [
    "networkx",
]
```

When initializing the project Algobattle will then make sure that the needed libraries are installed on the user's
machine.

## Hiding Parts of the Instance

Sometimes we want the generator to give us some data we need to verify the instance, but don't want the solver to see
this. For example, consider the problem of finding the longest path in a graph with a vertex cover (1) of a specific
size. The best way to verify that the instance graph actually contains such a vertex cover is to have it be part of the
instance data. But we want the solver to only have access to the information that it exists, not which exact vertices
are in it.
{.annotate}

1. A vertex cover is a subset of vertices such that all other vertices in the graph have an edge to a vertex in it.

We can use this using the `Field` construct from Pydantic. It is a simple marker object that lets us configure various
properties of specific fields. One of these settings is the `exclude` key, which tells Pydantic to exclude this field
when serializing the object into json. It will still be parsed and validated normally when reading json data and
creating the Python object. We can use it either as the default value of the attribute, or as `Annotated[...]` metadata.

!!! example
    In this class

    ```py
    from pydantic import Field


    class Instance(InstanceModel):
        """An instance of the Some Example problem."""

        normal_attribute: int
        hidden: float = Field(exclude=True)
        also_hidden: Annotated[str, Field(exclude=True)]
    ```

    the first attribute `normal_attribute` will be the only that is included in the output that the solver sees. All three
    attributes are required to be in the instance data the generator creates and will be available on the Python object.


!!! tip
    The `Field` specifier lets you do many more things than this! Read the excellently written
    [Pydantic documentation](https://docs.pydantic.dev/latest/concepts/fields) to see more use cases.

## Using the Algobattle Graph Classes

Since many problems use graphs as the foundation of their instances we provide several utility classes to make working
with these easier. These classes are `DirectedGraph`, `UndirectedGraph`, `EdgeWeights`, and `VertexWeights`. Using these
classes also ensures that multiple graph problems use the same formats and students won't have to worry about changing
any boilerplate code.

The easiest use case is to just inherit from `DirectedGraph` or `UndirectedGraph` instead of `InstanceModel`.
Your instance class will then behave the same as if it also included the `num_vertices` and `edges` keys which hold a
single number specifying the number of vertices in the graph (numbered `0` through `n-1`) and a list of tuples of such
vertices respectively. They will also ensure proper validation, with `DirectedGraph` accepting any graph and
`UndirectedGraph` accepting only those that contain no self loops and where edges are interpreted as being
directionless. Both graph's size is the number of vertices in it.

!!! example "Reachability"
    An implementation of the Reachability (1) problem's instance class might look
    something like this:
    {.annotate}

    1. Given a graph and two vertices in it, is there a path between them?

    ```py
    class Instance(DirectedGraph):
        """An instance of a Reachability problem."""

        start: Vertex
        end: Vertex
    ```

    Which is equivalent to

    ```py
    class Instance(InstanceModel):
        """An instance of a Reachability problem."""

        num_vertices: u64
        edges: Annotated[list[tuple[SizeIndex, SizeIndex]], UniqueItems]

        start: Vertex
        end: Vertex

        @property
        def size(self) -> int:
            """A graph's size is the number of vertices in it."""
            return self.num_vertices
    ```

!!! tip "Associated Annotation Types"
    As you can see in the example above, we also provide several types that are useful in type annotations of graph
    problems such as `Vertex`, `Edge`, or `Path`. How these function is explained in more detail in the
    [advanced annotations](annotations.md) section.

If you want the problem instance to also contain additional information associated with each vertex and/or each edge
you can use the `VertexWeights` and `EdgeWeights` mix ins. These are added as an additional parent class and must be
indexed with the type of the weights you want to use.

!!! example "Labelled Vertices and Weighted Edges"
    Say your problem wants to label each vertex with the name of a city and each edge with the distance it represents. This
    would be done like this:

    ```py
    class Instance(DirectedGraph, VertexWeights[str], EdgeWeights[float]): ...
    ```

    Both are encoded as lists of the weights where the nth entry corresponds to the weight of the nth vertex or edge.
    I.e. the above is equivalent to

    ```py
    class Instance(DirectedGraph):
        vertex_weights: Annotated[list[str], SizeLen]
        edge_weights: Annotated[list[float], EdgeLen]

        ...
    ```

!!! tip
    These classes also contain some utility methods to easily perform common graph operations. For example,
    `UndirectedGraph.edge_set` contains all edges in both directions, and the `neighbors` methods lets you quickly
    access a vertex's neighbours.

## Comparing Floats

!!! abstract
    This is a somewhat esoteric section that is not strictly needed to use Algobattle. If you're interested in the
    details this is perfect for you, but the important takeaway for everyone is that we recommend everyone to use the
    `LaxComp` class or `lax_comp` function when working with floats.

We use floats to represent real numbers, but these are limited to a certain precision (64 bits). This can lead to
annoying corner cases, finicky bugs, and teams being encouraged to put more energy into running into these than actually
solving the problem. For example, the equality `0.1 + 0.1 + 0.1 == 0.3` does not actually hold when using floats.
If a problem instance makes use of floats students can then use these inaccuracies to specifically craft instances that
can only be solved when carefully keeping track of your exact arithmetical operations and the inaccuracies they
introduce. Most of the time this is not actually what we want the focus of a problem to be on, so we'd rather students
just ignore these corner cases when working with floats and treat them as close to actual real numbers as possible.

Normally we do this by never comparing strict equality between float values and instead just checking if they are close
"enough" for our use case. This is not enough for us since teams would then just create corner case instances that rely
on the exact error bound we use. The solution then is to allow the solving team to introduce bigger errors than the
generating team. That means that the generating team cannot create instances right at the edge of precision errors since
the solver's solutions will be validated with bigger allowable errors.

This sounds complicated, but we've already implemented the hard bits in a utility class and function for you. All you
need to keep in mind is that whenever you would be doing a comparison involving equality (`==`, `<=`, or `>=`) to
instead use `LaxComp` or `lax_comp` from the `algobattle.types` module. The first acts as a wrapper that will then
safely perform these comparisons and the second performs the comparison immediately.

!!! example
    Here's several usage examples assuming the `role` variable contains the role of the team we're currently validating
    something for:

    - `#!py LaxComp(0.1 + 0.1 + 0.1, role) == 0.3`
    - `#!py LaxComp(0.2, role) <= 0.3`
    - `#!py lax_comp(0.1 + 0.1 + 0.1, "==", 0.3 role)`
    - `#!py lax_comp(0.300001, ">=", 0.3 role)`

The margins for error these introduce are absolutely tiny for all normal applications, about 10^14^ times smaller than
the values that are being compared, so they can be safely ignored by the application logic. But they are big enough to
cover any normal errors introduces by float arithmetic and thus make it safe to naively use them as though they
represent actual real numbers.

## Problems Without Witnesses

Most problems require the generator to not only create an instance, but also provide a solution for it. But we can also
create problems that expect only the instance in the generator's output. To do this, just set the corresponding argument
in the Problem constructor to `#!py False`.

```py hl_lines="6"
Problem(
    name="Instance Only Problem",
    min_size=17,
    instance_cls=Instance,
    solution_cls=Solution,
    with_solution=False,
)
```

## Custom Scoring Functions

In a match each fight (one execution of the generator followed by the other team's solver) is assigned a score. This is
a number in [0, 1] that indicates how well the solver did. Normally it is computed by just dividing the solver's
solution score by the generator's (or vice versa, if the goal is to minimize the score). This matches the usual notion
of approximation ratios.

!!! example
    When using the Independent Set (1) problem the generator created a solution with an independent set of size 5. The
    solver found one of size 4. Since the goal here is to maximize the solution size the score of this fight would be 
    `0.8`. But for Vertex Cover (2) the objective is to find the smallest vertex cover, so if the solver found one of
    size 20 and the generator of size 17, the overall score would be roughly `1.18`.
    {.annotate}

    1. Given a graph, find the biggest subset of its vertices that have no edge between any pair of them.
    2. Given a graph, find the smalles subset of vertices such that every other vertex has an edge to one in that set.

But this isn't always what we want to do. Consider the problem of finding the three shortest paths between two given
vertices in a graph, formalized like this:

```py
class Instance(DirectedGraph):
    """Instances of the 3 Shortest Paths problem."""

    start: Vertex
    end: Vertex


class Solution(SolutionModel):
    """Solutions of the 3 Shortest Paths problem."""

    paths: tuple[Path, Path, Path]  # (2)!

    @minimize
    def score(self, role: Role) -> float: ...


Problem(
    name="3 Shortest Paths",
    min_size=5,
    instance_cls=Instance,
    solution_cls=Solution,
)
```

1. For clarity, we omit the imports here.
2. You'd need additional validation logic here, but we now want to focus on just the score function.

How do we best implement the `score` function? We could just add the lengths of all the paths, or just pick the length
of the shortest or longest one. But really, what we want is for the final score to not just compare a single number
for each solution, but each path individually.

We can achieve this by providing a custom scoring function to the Problem constructor. This just is a function that
directly receives the instance and both solutions and returns a float in [0, 1]. When we do this, we can drop the
`score` method in the Solution class entirely.

```py hl_lines="14-23 30"
class Instance(DirectedGraph):
    """Instances of the 3 Shortest Paths problem."""

    start: Vertex
    end: Vertex


class Solution(SolutionModel):
    """Solutions of the 3 Shortest Paths problem."""

    paths: tuple[Path, Path, Path]


def compare_each_path(instance: Instance, generator_solution: Solution, solver_solution: Solution) -> float:
    gen_lens = sorted(len(path) for path in generator_solution.paths)  # (1)!
    sol_lens = sorted(len(path) for path in solver_solution.paths)
    ratios = [len(gen) / len(sol) for gen, sol in zip(gen_lens, sol_lens)]  # (2)!
    ratios = [min(1, max(0, num)) for num in ratios]  # (3)!
    return sum(ratios) / 3  # (4)!


Problem(
    name="3 Shortest Paths",
    min_size=5,
    instance_cls=Instance,
    solution_cls=Solution,
    score_function=compare_each_path,
)
```

1. Get each path's length and sort them.
2. Compute the ratio of each corresponding pair of paths.
3. Clamp the ratios to be in [0, 1].
4. Return the average of the ratios.

## Test Instances

When running `algobattle test` the CLI tool first tries to build and run the generator and then the solver. But in order
to be able to test run the solver, we need to provide it with an input instance. This means that if your generator does
not run successfully you also cannot test your solver. To prevent this issue, we can provide a simple test instance when
defining the problem. It will then be passed to the solver instead.

```py hl_lines="6"
Problem(
    name="Pairsum",
    min_size=4,
    instance_cls=Instance,
    solution_cls=Solution,
    test_instance=Instance(numbers=[1, 2, 3, 4]),
)
```

!!! attention "Make sure to pass a valid instance"
    This instance will not undergo the usual validation step and does not come with a solution. This means you can
    accidentally provide a test instance which can't actually be solved correctly.
