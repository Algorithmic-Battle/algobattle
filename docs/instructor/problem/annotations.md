# Advanced Type Annotations

We've already seen how you can use type annotations to declare what shape the I/O data should have and perform basic
validation. This page will go over more advanced usages of type annotations that Algobattle and Pydantic provide for us.

!!! note
    While validation via type annotations can be very useful and much faster than plain python methods, they are not
    necessary for most problems.
    Everything covered here can also be done with validation methods (`validate_instance` / `validate_solution`). If
    you're more comfortable with those rather than type annotations, feel free to use them instead.

## Type Aliases

!!! note
    This section is not specific to Algobattle and just covers general Python techniques, feel free to skip it if you're
    already familiar with it.

When using complicated types our annotations can get very complicated quickly. We can simplify the code by defining
type aliases, which basically just are variables but for types. For example, consider this class

```py
class Example(InstanceModel):
    edges: list[tuple[int, int]]
    matchings: list[set[tuple[int, int]]]
```

Its attributes are rather terse and hard to understand what exactly a list of sets of tuples of integers is supposed
to represent. This can be simplified by creating a couple of type aliases. The syntax used depends a bit on your Python
version and how explicit you want (and have) to be, but they all do the same thing.

=== "3.11 implicit"

    ```py
    Edge = tuple[int, int]
    Matching = set[Edge]


    class Example(InstanceModel):
        edges: list[Edge]
        matchings: list[Matching]
    ```

=== "3.11 explicit"

    ```py
    Edge: TypeAlias = tuple[int, int]
    Matching: TypeAlias = set[Edge]


    class Example(InstanceModel):
        edges: list[Edge]
        matchings: list[Matching]
    ```

=== ">= 3.12"

    ```py
    type Edge = tuple[int, int]
    type Matching = set[Edge]


    class Example(InstanceModel):
        edges: list[Edge]
        matchings: list[Matching]
    ```

This is particularly useful if you want to reuse a type definition, or one is very long. But it's also great to tell
others reading your code what you actually intended each piece to mean by just giving things more descriptive names.
For example, the `Vertex` type in `algobattle.types` actually just is a descriptive alias for the more general
`SizeIndex`.

## Forward References

!!! note
    This section is not specific to Algobattle and just covers general Python techniques, feel free to skip it if you're
    already familiar with it.

Python files are executed from top to bottom and this also includes type hints. This means that you cannot use types
and classes that you define later in a type hint. In practice, this is not something you very often want to do in
problem definitions anyway, but it's worth keeping in mind. For example, let's say we want to specify a type which
emulates the way paths in a file system work. That is, it can either just be the name of a file, or correspond to
folder containing more files and folders. Ideally, we'd want just recursively define it like this:

=== "3.11 implicit"

    ```py
    Path = str | dict[str, Path]
    ```

=== "3.11 explicit"

    ```py
    Path: TypeAlias = str | dict[str, Path]
    ```

=== ">= 3.12"

    ```py
    type Path = str | dict[str, Path]
    ```

But at the time that the `Path` on the right-hand side gets evaluated it will be an undefined variable and thus throw
an error. We can solve that by wrapping the entire expression in a string. The Python interpreter will then not evaluate
the individual variables, but type checkers and Pydantic will still interpret them correctly. The problem then is that
if we use the implicit version type checkers think that we just mean some meaningless string and not a type hint.
Because of this we actually have to use the explicit version when quoting forward references.

=== "3.11 explicit"

    ```py
    Path: TypeAlias = "str | dict[str, Path]"
    ```

=== ">= 3.12"

    ```py
    type Path = "str | dict[str, Path]"
    ```

!!! info
    The `type` syntax introduced in 3.12 actually allows you to write this specific example without the quotes. But it
    only allows for forward references to the type you're defining itself to be unquoted, all other uses of forward
    references still need to be quoted.

You can also use quoted forward references in any other place you'd use a type hint, though for the types used in a
problem definition we can usually prevent them altogether by just reordering the code.

```py
class Example(InstanceModel):
    some_attr: "CoolNumber"


CoolNumber = int
```

## Annotated Metadata

!!! note "Type Hints and Annotations"
    Usually _type hint_ and _type annotation_ are used interchangeably, they just refer to the thing after the colon
    following an attribute name. Since this section also deals with the `Annotated[...]` type construct we will use
    type hints here when talking about the general construct to differentiate it from this specific object.

In the basic tutorial we've already seen that we can add validation to a field using `Annotated[...]` metadata. This is
a very powerful construct that is heavily used by Algobattle and Pydantic, so we'll take a deeper look at it now. In
Python type hints are not only used by linters and type checkers to make sure your code does what you want it to,
but can also be examined at runtime. This is how Pydantic (and thus Algobattle) knows what you want the json files to
look like, it sees an attribute that's been marked as an `int`, so it will expect an integer at that place of the json
file. This is a really clever method because it will automatically validate the json without us explicitly telling us
what it should do, it just gets all the info it needs from the type hints.

But sometimes we would want to tell the validator more than we can express in a type hint. For example, we might want to
only allow positive numbers, but Python does not have a type specifically for that. In earlier versions of Pydantic you
would then specify this using its `Field` specifier like this

```py
class Example(InstanceModel):
    positive_int: int = Field(gt=0)
```

where the `gt` key tells Pydantic that it should validate this field as being greater than 0. This works great when you
want to have this behaviour on only a single attribute, but leads to a lot of code duplication when you want it in more
places and lets you forget it easily.

The idea behind `Annotated[...]` is that it lets us annotate a Python type with some additional metadata that is
irrelevant for type checkers, but tells other tools like Pydantic what they should do. It receives at least two
arguments, the first of which must be a type and all the others are arbitrary metadata. This lets easily specify how
several fields should be validated with a single `Field`.

```py
PositiveInt = Annotated[int, Field(gt=0)]


class Example(InstanceModel):
    first: PositiveInt
    second: PositiveInt
    third: PositiveInt
    fourth: PositiveInt
```

The Python standard library `annotated_types` also contains a collection of basic metadata types such as `Gt`, `Ge`,
`Lt`, `Le` that Pydantic will also interpret the same way as a `Field` with the corresponding key set.

!!! example
    In this class, all attributes will be validated as an integer between 3 and 17 inclusive.

    ```py
    class Example(InstanceModel):
        first: int = Field(ge=3, lt=18)
        second: Annotated[int, Field(ge=3, lt=18)]
        third: Annotated[int, Ge(3), Lt(18)]
        fourth: Annotated[int, Interval(ge=3, lt=18)]
    ```


The `algobattle.types` module also contains versions of these that behave identically for these use cases. We will later
see some capabilities of the Algobattle metadata that neither other option can do, but for most problems you can use
whichever method you prefer.

The full list of available `Field` keys can be found in the
[Pydantic documentation](https://docs.pydantic.dev/latest/concepts/fields). The available `algobattle.types` metadata
is:

- `Gt`, `Ge`, `Lt`, `Le`, and `Interval`: All specify a constraint on numeric data. The first four provide the
    corresponding inequality and `Interval` lets you group multiple of them together by using its keyword arguments.
- `MultipleOf`: Specifies that a numeric value is a multiple of some value. E.g. a field using
    `Annotated[int, MultipleOf(2)]` validates that the number in it is even.
- `MinLen`, `MaxLen`, and `Len`: Specifies that some collection's length has the corresponding property. `Len` again
    serves to group the other two into a single object. E.g. `Annotated[set, MinLen(17)]` allows only sets that have
    at least 17 elements.
- `UniqueItems`: Specifies that a collection contains no duplicate elements. E.g. `Annotated[list, UniqueItems]`
    validates that the list contains no element twice.
- `In`: Specifies that some value is contained in a collection. E.g. `Annotated[int, In({1, 3, 17, 95})]`
    allows only 1, 3, 17, or 95.
- `IndexInto`: Specifies that a value is a valid index into some list. E.g.
    `Annotated[int, IndexInto(["a", "b", "c"])]` only allows numbers between 0 and 2.

## Attribute References

The `Field` specifiers and default metadata options cover a wide variety of use cases, but there are some validations
that cannot be done with it. For example, consider the simple problem of finding the biggest number in a list. We
can easily validate that the number actually is an element of the list with a `validate_solution` method like this:

```py
class Instance(InstanceModel):

    numbers: list[int]


class Solution(InstanceModel):

    biggest: int

    def validate_solution(self, instance: Instance, role: Role) -> None
        if self.biggest not in instance.numbers:
            raise ValidationError("The given number is not in the instance")
```

But we cannot do this with the `In` annotation metadata since there we need to provide the list of items to check
against at the time we write the type hint, but we only actually get that list when we validate the solution. The
`InstanceRef` and `SolutionRef` types in the `algobattle.problem` module fix this issue. They can be used to tell
Algobattle that we do not actually want to compare against a value we have right now, but with a value that we know
will be found in the instance or solution. Our example problem then becomes simplified to this.

```py
class Instance(InstanceModel):
    numbers: list[int]


class Solution(InstanceModel):
    biggest: Annotated[int, In(InstanceRef.numbers)]
```

!!! warning
    We cannot statically ensure that the attributes you reference actually exist on the instance or solution. This
    means that if you e.g. have a typo or change a definition without updating a reference to it, the validation step
    will throw an error at runtime even though type checkers and linters do not raise any warnings.

    You also need to make sure you always use these in contexts where the referred to value actually makes sense. For
    example, referring to an attribute of a solution when validating an instance or self-referential attributes can
    lead to issues during validation. Especially in the latter case we also cannot guarantee that an error is raised in
    cases where the references do not behave in the way you intended and instead will just fail silently.

??? info "Performance"
    Due to implementation details references to the object that is being validated itself (i.e. `SolutionRef` in a
    solution or `InstanceRef` in an instance) will lead to two separate invocations of Pydantic's validation logic.
    This is perfectly fine in basically all use cases, but when you implement very slow custom logic using it, are
    validating truly massive amounts of data (several gigabytes at a time) it can lead to slowdowns.

## Further Pydantic Features

There are many more Pydantic features that can be very useful when designing problems. They are all explained very well
in their official documentation. In particular,
[annotated validators](https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators),
[model validators](https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators),
[field specifiers](https://docs.pydantic.dev/latest/concepts/fields/),
[tagged unions](https://docs.pydantic.dev/latest/concepts/unions/#discriminated-unions),
and [custom types](https://docs.pydantic.dev/latest/concepts/types/#custom-types) are very useful for Algobattle
problems.

### Attribute Reference Validators

!!! abstract
    This is an advanced feature and will make most sense to you if you already understand 
    [annotated validators](https://docs.pydantic.dev/latest/concepts/validators/#annotated-validators).

Similar to the `algobattle.types` versions of metadata annotations, `algobattle.problem` also contains the
`AttributeReferenceValidator`. It functions just like a Pydantic `AfterValidator` (and is implemented using it), but
the validation function also receives the value of a referenced attribute.

!!! example

    If we wanted to confirm that a line of text is indented by as many spaces as are given in the instance we can
    create this annotated type:

    ```py
    def check_indentation(val: str, indent_level: int) -> str:
        if not val.startswith(" " * indent_level):
            raise ValueError


    IndentedLine = Annotated[str, AttributeReferenceValidator(check_indentation, InstanceRef.indentation)]
    ```

### Validation Context

!!! abstract
    This is an advanced feature and will make most sense to you if you already understand 
    [validation context](https://docs.pydantic.dev/latest/concepts/validators/#validation-context).

Algobattle will include certain useful data in the validation context. The full list of available keys is:

`max_size`
: Contains the maximum allowed instance size of the current fight. Will always be present.

    !!! tip

        Keep in mind that this is a different value from the current instance's size. You usually want to use the latter
        when validating data.

`role`
: Contains the role of the program whose output is currently being validated. Will always be present.

`instance`
: Contains the current instance. Optional key.

`solution`
: Contains the current solution. Optional key.

`self`
: Contains the object that is currently being validated. Optional key.

!!! warning
    Due to implementation details we sometimes need to validate data multiple times, with intermediate runs only
    receiving partial validation contexts. Because of this always make sure that you check if the keys you are
    accessing are currently present and do not raise an error if they aren't.

    When using the references to the object that is currently being validated keep in mind that you are accessing an
    intermediate representation of it that is not guaranteed to have the properties enforced by any other functions
    that rely on references to the object itself.
