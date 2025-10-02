"""Utility types used to easily define Problems."""
from collections.abc import Collection, Iterator
from dataclasses import dataclass
from functools import cache, cached_property
from itertools import pairwise
from sys import float_info
from typing import Annotated, Any, ClassVar, Generic, Literal, TypedDict, TypeVar, overload

import annotated_types as at
import pydantic._internal._validators as validators
from annotated_types import (
    BaseMetadata,
    GroupedMetadata,
    SupportsDiv,
    SupportsGe,
    SupportsGt,
    SupportsLe,
    SupportsLt,
    SupportsMod,
)
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, PydanticKnownError
from pydantic_core.core_schema import no_info_after_validator_function

from algobattle.problem import (
    AttributeReference,
    AttributeReferenceValidator,
    InstanceModel,
    InstanceRef,
    SolutionModel,
)
from algobattle.util import BaseModel, Role, ValidationError

__all__ = (
    "AlgobattleContext",
    "DirectedGraph",
    "Edge",
    "EdgeLen",
    "EdgeWeights",
    "Ge",
    "Gt",
    "Interval",
    "LaxComp",
    "Le",
    "Len",
    "Lt",
    "MaxLen",
    "MinLen",
    "MultipleOf",
    "Path",
    "SizeIndex",
    "SizeLen",
    "UndirectedGraph",
    "UniqueItems",
    "VertexWeights",
    "i16",
    "i32",
    "i64",
    "lax_comp",
    "u16",
    "u32",
    "u64",
)


class AlgobattleContext(TypedDict, total=False):
    """Reference class containing the attributes that can be present in the context dict."""

    role: Role
    """Role of the team that created/will receive this data."""
    max_size: int
    """Maximum size of the current fight this data is for."""
    self: InstanceModel | SolutionModel[InstanceModel]
    """Object currently being validated, if it is the second round of validation."""
    instance: InstanceModel
    """Instance object the solution that is being validated is for."""
    solution: SolutionModel[InstanceModel]
    """Solution object that is currently being validated."""


# * General helper types


u64 = Annotated[int, at.Interval(ge=0, lt=2**64)]
"""64 bit unsigned int."""

i64 = Annotated[int, at.Interval(ge=-(2**63), lt=2**63)]
"""64 bit signed int."""

u32 = Annotated[int, at.Interval(ge=0, lt=2**32)]
"""32 bit unsigned int."""

i32 = Annotated[int, at.Interval(ge=-(2**31), lt=2**31)]
"""32 bit signed int."""

u16 = Annotated[int, at.Interval(ge=0, lt=2**16)]
"""16 bit unsigned int."""

i16 = Annotated[int, at.Interval(ge=-(2**15), lt=2**15)]
"""16 bit signed int."""


@overload
def Gt(gt: SupportsGt) -> at.Gt:
    ...


@overload
def Gt(gt: AttributeReference) -> AttributeReferenceValidator:
    ...


def Gt(gt: SupportsGt | AttributeReference) -> at.Gt | AttributeReferenceValidator:
    """Implies that the value must be greater than the argument.

    Passing an `AttributeReferece` means that the value must be greater than the value on the referenced property of
    the instance or solution. E.g. `Gt(InstanceReference("size"))` in a solution model implies that the value must be
    greater than the size of the instance it solves.

    It can be used with any type that supports the ``>`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """
    if isinstance(gt, AttributeReference):
        return AttributeReferenceValidator(validators.greater_than_validator, gt)
    else:
        return at.Gt(gt)


@overload
def Ge(ge: SupportsGe) -> at.Ge:
    ...


@overload
def Ge(ge: AttributeReference) -> AttributeReferenceValidator:
    ...


def Ge(ge: SupportsGe | AttributeReference) -> at.Ge | AttributeReferenceValidator:
    """Implies that the value must be greater than or equal to the argument.

    Passing an `AttributeReferece` means that the value must be greater than or equal to the value on the referenced
    property of the instance or solution. E.g. `Ge(InstanceReference("size"))` in a solution model implies that the
    value must be greater than or equal to the size of the instance it solves.

    It can be used with any type that supports the ``>=`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """
    if isinstance(ge, AttributeReference):
        return AttributeReferenceValidator(validators.greater_than_or_equal_validator, ge)
    else:
        return at.Ge(ge)


@overload
def Lt(lt: SupportsLt) -> at.Lt:
    ...


@overload
def Lt(lt: AttributeReference) -> AttributeReferenceValidator:
    ...


def Lt(lt: SupportsLt | AttributeReference) -> at.Lt | AttributeReferenceValidator:
    """Implies that the value must be less than the argument.

    Passing an `AttributeReferece` means that the value must be less than the value on the referenced property of
    the instance or solution. E.g. `Lt(InstanceReference("size"))` in a solution model implies that the value must be
    less than the size of the instance it solves.

    It can be used with any type that supports the ``<`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """
    if isinstance(lt, AttributeReference):
        return AttributeReferenceValidator(validators.less_than_validator, lt)
    else:
        return at.Lt(lt)


@overload
def Le(le: SupportsLe) -> at.Le:
    ...


@overload
def Le(le: AttributeReference) -> AttributeReferenceValidator:
    ...


def Le(le: SupportsLe | AttributeReference) -> at.Le | AttributeReferenceValidator:
    """Implies that the value must be less than or equal to the argument.

    Passing an `AttributeReferece` means that the value must be less than or equal to the value on the referenced
    property of the instance or solution. E.g. `Le(InstanceReference("size"))` in a solution model implies that the
    value must be less than or equal to the size of the instance it solves.

    It can be used with any type that supports the ``<=`` operator,
    including numbers, dates and times, strings, sets, and so on.
    """
    if isinstance(le, AttributeReference):
        return AttributeReferenceValidator(validators.less_than_or_equal_validator, le)
    else:
        return at.Le(le)


@dataclass(frozen=True, kw_only=True, slots=True)
class Interval(GroupedMetadata):
    """Interval can express inclusive or exclusive bounds with a single object.

    It accepts keyword arguments ``gt``, ``ge``, ``lt``, and/or ``le``, which
    are interpreted the same way as the single-bound constraints.
    """

    gt: SupportsGt | AttributeReference | None = None
    ge: SupportsGe | AttributeReference | None = None
    lt: SupportsLt | AttributeReference | None = None
    le: SupportsLe | AttributeReference | None = None

    def __iter__(self) -> Iterator[BaseMetadata | AttributeReferenceValidator]:
        """Unpack an Interval into zero or more single-bounds."""
        if self.gt is not None:
            yield Gt(self.gt)
        if self.ge is not None:
            yield Ge(self.ge)
        if self.lt is not None:
            yield Lt(self.lt)
        if self.le is not None:
            yield Le(self.le)


@overload
def MultipleOf(multiple_of: SupportsDiv | SupportsMod) -> at.MultipleOf:
    ...


@overload
def MultipleOf(multiple_of: AttributeReference) -> AttributeReferenceValidator:
    ...


def MultipleOf(
    multiple_of: SupportsDiv | SupportsMod | AttributeReference,
) -> at.MultipleOf | AttributeReferenceValidator:
    """Specifies `value % multiple_of == 0`."""
    if isinstance(multiple_of, AttributeReference):
        return AttributeReferenceValidator(validators.multiple_of_validator, multiple_of)
    else:
        return at.MultipleOf(multiple_of)


@overload
def MinLen(min_length: Annotated[int, Ge(0)]) -> at.MinLen:
    ...


@overload
def MinLen(min_length: AttributeReference) -> AttributeReferenceValidator:
    ...


def MinLen(min_length: Annotated[int, Ge(0)] | AttributeReference) -> at.MinLen | AttributeReferenceValidator:
    """Implies minimum inclusive length, i.e. `len(value) >= min_length`."""
    if isinstance(min_length, AttributeReference):
        return AttributeReferenceValidator(validators.min_length_validator, min_length)
    else:
        return at.MinLen(min_length)


@overload
def MaxLen(max_length: Annotated[int, Ge(0)]) -> at.MaxLen:
    ...


@overload
def MaxLen(max_length: AttributeReference) -> AttributeReferenceValidator:
    ...


def MaxLen(max_length: Annotated[int, Ge(0)] | AttributeReference) -> at.MaxLen | AttributeReferenceValidator:
    """Implies maximum inclusive length, i.e. `len(value) <= max_length`."""
    if isinstance(max_length, AttributeReference):
        # pydantic impl is currently bugged
        def max_length_validator(x: Any, max_length: Any) -> Any:
            if not (len(x) <= max_length):
                raise PydanticKnownError(
                    "too_long",
                    {"field_type": "Value", "max_length": max_length, "actual_length": len(x)},
                )
            return x

        return AttributeReferenceValidator(max_length_validator, max_length)
    else:
        return at.MaxLen(max_length)


@dataclass(frozen=True, slots=True)
class Len(GroupedMetadata):
    """Implies `min_length <= len(value) <= max_length`.

    Upper bound may be omitted or ``None`` to indicate no upper length bound.
    """

    min_length: Annotated[int, Ge(0)] | AttributeReference = 0
    max_length: Annotated[int, Ge(0)] | AttributeReference | None = None

    def __iter__(self) -> Iterator[BaseMetadata | AttributeReferenceValidator]:
        """Unpack a Len into one or more single-bounds."""
        if self.min_length != 0:
            yield MinLen(self.min_length)
        if self.max_length is not None:
            yield MaxLen(self.max_length)


class UniqueItems:
    """Specifies that the collection should contain no duplicates.

    Can only annotate Collection types.
    """

    @staticmethod
    def __get_pydantic_core_schema__(source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        def _func(collection: Collection[Any]) -> Collection[Any]:
            if len(collection) != len(set(collection)):
                raise ValueError("Value contains duplicate elements")
            return collection

        return no_info_after_validator_function(_func, handler(source_type))

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        schema = handler(core_schema)
        schema["uniqueItems"] = True
        return schema


def In(attribute: AttributeReference) -> AttributeReferenceValidator:
    """Specifies that the value should be `in` some collection."""

    def validator(val: Any, attr: Any) -> Any:
        if val not in attr:
            raise ValueError(f"Value is not contained in collection {attribute}.")
        return val

    return AttributeReferenceValidator(validator, attribute)


KeyOf = In
"""Specifies that the value should be the key of the referenced dict."""


class IndexInto:
    """Specifies that the value is a valid index into the Sequence.

    May be used an annotation to another type like this: `index: Annotated[i16, IndexInto(SelfRef.list)]`,
    or as a bare type annotation `index: IndexInto[SelfRef.list]`.
    """

    def __new__(cls, attribute: AttributeReference) -> AttributeReferenceValidator:
        def validator(val: Any, attr: Any) -> Any:
            validators.greater_than_or_equal_validator(val, 0)
            validators.less_than_validator(val, len(attr))
            return val

        return AttributeReferenceValidator(validator, attribute)

    @classmethod
    def __class_getitem__(cls, key: AttributeReference, /) -> Annotated:
        def validator(val: Any, attr: Any) -> Any:
            validators.less_than_validator(val, len(attr))
            return val

        return Annotated[int, at.Ge(0), AttributeReferenceValidator(validator, key)]


# * Algobattle specific types


SizeIndex = Annotated[u64, at.Ge(0), Lt(InstanceRef.size)]
"""Specifies that the field is a valid index into a instance.size length sequence, i.e. 0 <= i < instance.size."""


class SizeLen:
    """Specifies that the collection has length `instance.size`.

    Can only annotate Sized types.
    """

    @staticmethod
    def _func(v: Any, size: int) -> Any:
        """Validates that the collection has length `instance.size`."""
        if len(v) != size:
            raise ValueError("Value does not have length `instance.size`")
        return v

    _validator = AttributeReferenceValidator(_func, InstanceRef.size)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return cls._validator.__get_pydantic_core_schema__(source_type, handler)


# * Graph classes


Vertex = SizeIndex
"""Type for vertices, encoded as numbers `0 <= v < instance.num_vertices`."""


Edge = Annotated[int, IndexInto[InstanceRef.edges]]
"""Type for edges, encoded as indices into `instance.edges`."""


def path_in_graph(path: list[Vertex], edge_set: set[tuple[Vertex, Vertex]]):
    """Checks that a path actually exists in the graph."""
    for edge in pairwise(path):
        if edge not in edge_set:
            raise ValueError(f"The edge {edge} does not exist in the graph.")


Path = Annotated[list[Vertex], AttributeReferenceValidator(path_in_graph, InstanceRef.edge_set)]


class DirectedGraph(InstanceModel):
    """Base instance class for problems on directed graphs."""

    num_vertices: u64
    edges: Annotated[list[tuple[SizeIndex, SizeIndex]], UniqueItems]

    @property
    def size(self) -> int:
        """A graph's size is the number of vertices in it."""
        return self.num_vertices

    @cached_property
    def edge_set(self) -> set[tuple[Vertex, Vertex]]:
        """The set of edges in this graph."""
        return set(self.edges)

    @cache # noqa: B019
    def neighbors(self, vertex: Vertex, direction: Literal["all", "outgoing", "incoming"] = "all") -> set[Vertex]:
        """The neighbors of a vertex."""
        res = set[Vertex]()
        if direction in {"all", "outgoing"}:
            res |= {v for (u, v) in self.edges if u == vertex}
        if direction in {"all", "incoming"}:
            res |= {v for (v, u) in self.edges if u == vertex}
        return res


class UndirectedGraph(DirectedGraph):
    """Base instance class for problems on undirected graphs."""

    def validate_instance(self):
        """Validates that the graph is well formed and contains no self loops.

        Also brings it into a normal form where every edge {u, v} occurs exactly once in the list.
        I.e. `[(0, 1), (1, 0), (1, 2)]` is accepted as valid and normalised to `[(0, 1), (1, 2)]`.
        """
        super().validate_instance()
        if any(u == v for u, v in self.edges):
            raise ValidationError("Undirected graph contains self loops.")

        edge_set = set(self.edges)
        if any(edge[::-1] in edge_set for edge in self.edges):
            raise ValidationError("Undirected graph contains back and forth edges between two vertices.")

    @cached_property
    def edge_set(self) -> set[tuple[Vertex, Vertex]]:
        """The set of edges in this graph.

        Normalized to contain every edge in both directions.
        """
        return set(self.edges) | {(v, u) for (u, v) in self.edges}

    @cache # noqa: B019
    def neighbors(self, vertex: Vertex, direction: Literal["all", "outgoing", "incoming"] = "all") -> set[Vertex]:
        """The neighbors of a vertex."""
        # more efficient specialization

        return {v for (u, v) in self.edge_set if u == vertex}


class EdgeLen:
    """Specifies that the collection has the same length as `instance.edges`.

    Can only annotate Sized types.
    """

    @staticmethod
    def _func(v: Any, edges: list[tuple[int, int]]) -> Any:
        """Validates that the collection has the same length as `instance.edges`."""
        if len(v) != len(edges):
            raise ValueError("Value does not have the same length as `instance.edges`")
        return v

    _validator = AttributeReferenceValidator(_func, InstanceRef.edges)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        return cls._validator.__get_pydantic_core_schema__(source_type, handler)


Weight = TypeVar("Weight")


class EdgeWeights(DirectedGraph, BaseModel, Generic[Weight]):
    """Mixin for graphs with weighted edges."""

    edge_weights: Annotated[list[Weight], EdgeLen]

    @cached_property
    def edges_with_weights(self) -> Iterator[tuple[tuple[Vertex, Vertex], Weight]]:
        """Iterate over all edges and their weights."""
        return zip(self.edges, self.edge_weights, strict=True)

    @cache # noqa: B019
    def weight(self, edge: Edge | tuple[Vertex, Vertex]) -> Weight:
        """Returns the weight of an edge.

        Raises KeyError if the given edge does not exist.
        """
        if isinstance(edge, tuple):
            try:
                edge = self.edges.index(edge)
            except ValueError as e:
                if isinstance(self, UndirectedGraph):
                    try:
                        edge = self.edges.index((edge[1], edge[0]))
                    except ValueError as e:
                        raise KeyError from e
                else:
                    raise KeyError from e

        return self.edge_weights[edge]


class VertexWeights(DirectedGraph, BaseModel, Generic[Weight]):
    """Mixin for graphs with weighted vertices."""

    vertex_weights: Annotated[list[Weight], SizeLen]

    @cached_property
    def vertices_with_weights(self) -> Iterator[tuple[Vertex, Weight]]:
        """Iterate over all edges and their weights."""
        return enumerate(self.vertex_weights)


@dataclass(frozen=True, slots=True)
class LaxComp:
    """Helper class to make forgiving float comparisons easy.

    When comparing floats for equality there often are frustrating edge cases introduced by its imprecisions. This can
    lead to matches not being decided by which team generates better instances, but by who can craft the most finnicky
    floating point values. This class lets you easily sidestep these problems.

    It implements comparison operations by adding a small epsilon that covers an allowable range of imprecision. The
    solving team will receive twice the epsilon that the generating team was given. This means that the generator cannot
    try to exploit imprecision issues since the solver has a bigger tolerance to play with.

    !!! example "Usage"
        ```py
            LaxComp(some_val ** 2, role) <= comparison_val
        ```
    """

    value: float
    """The value that can be relaxed in the comparison."""
    role: Role
    """Role of the program whose output is currently being validated."""

    relative_epsilon: ClassVar[float] = 128 * float_info.epsilon
    absolute_epsilon: ClassVar[float] = float_info.min

    def __eq__(self, other: object, /) -> bool:
        if isinstance(other, (float, int, bool)):
            other = float(other)
            diff = abs(self.value - other)
            norm = min(abs(self.value) + abs(other), float_info.max)
            factor = 1 if self.role == Role.generator else 2
            return diff <= factor * max(self.absolute_epsilon, norm * self.relative_epsilon)
        else:
            return NotImplemented

    def __le__(self, other: float, /) -> bool:
        return self.value <= other or self == other

    def __ge__(self, other: float, /) -> bool:
        return self.value >= other or self == other


def lax_comp(value: float, cmp: Literal["<=", "==", ">="], other: float, role: Role) -> bool:
    """Helper function to explicitly use the `LaxComp` comparison mechanism.

    Args:
        value: First value to compare.
        cmp: Comparison to perform, one of "<=", "==", or ">=".
        other: Other value to compare.
        role: Role of the program the values are being validated for.

    Returns:
        Result of the comparison.
    """
    val = LaxComp(value, role)
    match cmp:
        case "<=":
            return val <= other
        case "==":
            return val == other
        case ">=":
            return val >= other
