"""Tests for pydantic parsing types."""
from typing import Annotated, Any
from unittest import TestCase, main
from unittest.util import safe_repr

from pydantic import ValidationError

from algobattle.problem import AttributeReference, InstanceModel, SelfRef
from algobattle.types import Ge, Interval, LaxComp, SizeIndex, UniqueItems
from algobattle.util import Role


class ModelCreationTests(TestCase):
    """Test that the model creation process runs smoothly."""

    def test_basic(self):
        basic_instance()

    def test_size(self):
        size_instance()

    def test_interval(self):
        interval_instance()

    def test_uniqe(self):
        unique_items_instance()


def basic_instance() -> type[InstanceModel]:
    """Create a basic instance class."""

    class TestModel(InstanceModel):
        ge_const: Annotated[int, Ge(0)]
        ge_ref: Annotated[int, Ge(AttributeReference("self", "ge_const"))]

        @property
        def size(self) -> int:
            return 0

    return TestModel


class BasicTests(TestCase):
    """Tests for the basic attribute ref based features."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.TestModel = basic_instance()
        cls.wrong_ref_instance_dict = {"ge_const": 0, "ge_ref": -1}

    def test_success(self):
        """Successfully validate a correct instance."""
        self.TestModel.model_validate({"ge_const": 0, "ge_ref": 0})

    def test_wrong_const(self):
        """Reject wrong constant comparison."""
        with self.assertRaises(ValidationError, msg="Constant comparison not rejected"):
            self.TestModel.model_validate({"ge_const": -1, "ge_ref": 0})

    def test_wrong_ref_context(self):
        """Reject a wrong instance."""
        with self.assertRaises(ValidationError):
            self.TestModel.model_validate(self.wrong_ref_instance_dict)


def size_instance() -> type[InstanceModel]:
    """Create a basic solution class."""

    class SizeModel(InstanceModel):
        items: list[int]
        index: SizeIndex

        @property
        def size(self) -> int:
            return len(self.items)

    return SizeModel


class SizeTests(TestCase):
    """Tests for the SizeIndex type."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.TestModel = size_instance()

    def test_success(self):
        """Successfully validate a correct instance."""
        self.TestModel.model_validate({"items": [1, 2, 3], "index": 1})

    def test_index_negative(self):
        """Reject negative indices immedietly."""
        with self.assertRaises(ValidationError):
            self.TestModel.model_validate({"items": [], "index": -1})

    def test_index_large(self):
        """Reject too large indices."""
        with self.assertRaises(ValidationError):
            self.TestModel.model_validate({"items": [1, 2], "index": 2})


def interval_instance() -> type[InstanceModel]:
    """Create a basic solution class with an Interval constraint."""

    class IntervalModel(InstanceModel):
        lower_bound: int
        i: Annotated[int, Interval(ge=SelfRef.lower_bound, lt=10)]

        @property
        def size(self) -> int:
            return self.i

    return IntervalModel


class IntervalTests(TestCase):
    """Tests for the Interval grouped metada."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.TestModel = interval_instance()

    def test_accept(self):
        """Accept correct instance."""
        self.TestModel.model_validate({"lower_bound": 0, "i": 5})

    def test_reject_lower(self):
        """Reject instance incorrect because of lower bound."""
        with self.assertRaises(ValidationError):
            self.TestModel.model_validate({"lower_bound": 0, "i": -1})

    def test_reject_upper(self):
        """Reject instance incorrect because of upper bound."""
        model_dict = {"lower_bound": 0, "i": 10}
        with self.assertRaises(ValidationError):
            self.TestModel.model_validate(model_dict)


def unique_items_instance() -> type[InstanceModel]:
    """Create a basic instance class with a unique items constraint."""

    class UniqueModel(InstanceModel):
        array: Annotated[list[int], UniqueItems]

        @property
        def size(self) -> int:
            return len(self.array)

    return UniqueModel


class UniqueItemsTest(TestCase):
    """Tests for the unique items decorator."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.TestModel = unique_items_instance()

    def test_success(self):
        self.TestModel.model_validate({"array": [1, 2, 3]})

    def test_rejected(self):
        with self.assertRaises(ValidationError):
            self.TestModel.model_validate({"array": [1, 2, 2]})

    def test_schema(self):
        schema = self.TestModel.model_json_schema()
        self.assertIn("uniqueItems", schema["properties"]["array"])


class LaxCompTests(TestCase):
    """Tests for the LaxComp helper."""

    def assertNotGreaterEqual(self, a: Any, b: Any, msg: str | None = None) -> None:
        if msg is None:
            msg = f"{safe_repr(a)} greater than or equal to {safe_repr(b)}"
        self.assertFalse(a >= b, msg)

    def assertNotLessEqual(self, a: Any, b: Any, msg: str | None = None) -> None:
        if msg is None:
            msg = f"{safe_repr(a)} less than or equal to {safe_repr(b)}"
        self.assertFalse(a <= b, msg)

    @classmethod
    def setUpClass(cls) -> None:
        LaxComp.absolute_epsilon = 1
        LaxComp.relative_epsilon = 0.1

    def test_equal_strict(self) -> None:
        self.assertEqual(LaxComp(0, Role.generator), 0)
        self.assertEqual(LaxComp(0, Role.solver), 0)

    def test_equal_small(self) -> None:
        self.assertEqual(LaxComp(0, Role.generator), 0.5)
        self.assertEqual(LaxComp(0, Role.solver), 0.5)

    def test_equal_medium(self) -> None:
        self.assertNotEqual(LaxComp(0, Role.generator), 1.5)
        self.assertEqual(LaxComp(0, Role.solver), 1.5)

    def test_equal_big(self) -> None:
        self.assertNotEqual(LaxComp(0, Role.generator), 2.5)
        self.assertNotEqual(LaxComp(0, Role.solver), 2.5)

    def test_equal_rel_strict(self) -> None:
        self.assertEqual(LaxComp(100, Role.generator), 100)
        self.assertEqual(LaxComp(100, Role.solver), 100)

    def test_equal_rel_small(self) -> None:
        self.assertEqual(LaxComp(100, Role.generator), 110)
        self.assertEqual(LaxComp(100, Role.solver), 110)

    def test_equal_rel_medium(self) -> None:
        self.assertNotEqual(LaxComp(100, Role.generator), 130)
        self.assertEqual(LaxComp(100, Role.solver), 130)

    def test_equal_rel_big(self) -> None:
        self.assertNotEqual(LaxComp(100, Role.generator), 160)
        self.assertNotEqual(LaxComp(100, Role.solver), 160)

    def test_greater_equal_greater(self) -> None:
        self.assertGreaterEqual(LaxComp(1, Role.generator), 0)
        self.assertGreaterEqual(LaxComp(1, Role.solver), 0)
        self.assertGreaterEqual(1, LaxComp(0, Role.generator))
        self.assertGreaterEqual(1, LaxComp(0, Role.solver))

    def test_greater_equal_strict(self) -> None:
        self.assertGreaterEqual(LaxComp(0, Role.generator), 0)
        self.assertGreaterEqual(LaxComp(0, Role.solver), 0)
        self.assertGreaterEqual(0, LaxComp(0, Role.generator))
        self.assertGreaterEqual(0, LaxComp(0, Role.solver))

    def test_greater_equal_small(self) -> None:
        self.assertGreaterEqual(LaxComp(0, Role.generator), 0.5)
        self.assertGreaterEqual(LaxComp(0, Role.solver), 0.5)
        self.assertGreaterEqual(0, LaxComp(0.5, Role.generator))
        self.assertGreaterEqual(0, LaxComp(0.5, Role.solver))

    def test_greater_equal_medium(self) -> None:
        self.assertNotGreaterEqual(LaxComp(0, Role.generator), 1.5)
        self.assertGreaterEqual(LaxComp(0, Role.solver), 1.5)
        self.assertNotGreaterEqual(0, LaxComp(1.5, Role.generator))
        self.assertGreaterEqual(0, LaxComp(1.5, Role.solver))

    def test_greater_equal_big(self) -> None:
        self.assertNotGreaterEqual(LaxComp(0, Role.generator), 2.5)
        self.assertNotGreaterEqual(LaxComp(0, Role.solver), 2.5)
        self.assertNotGreaterEqual(0, LaxComp(2.5, Role.generator))
        self.assertNotGreaterEqual(0, LaxComp(2.5, Role.solver))

    def test_greater_equal_rel_strict(self) -> None:
        self.assertGreaterEqual(LaxComp(100, Role.generator), 100)
        self.assertGreaterEqual(LaxComp(100, Role.solver), 100)
        self.assertGreaterEqual(100, LaxComp(100, Role.generator))
        self.assertGreaterEqual(100, LaxComp(100, Role.solver))

    def test_greater_equal_rel_small(self) -> None:
        self.assertGreaterEqual(LaxComp(100, Role.generator), 110)
        self.assertGreaterEqual(LaxComp(100, Role.solver), 110)
        self.assertGreaterEqual(100, LaxComp(110, Role.generator))
        self.assertGreaterEqual(100, LaxComp(110, Role.solver))

    def test_greater_equal_rel_medium(self) -> None:
        self.assertNotGreaterEqual(LaxComp(100, Role.generator), 130)
        self.assertGreaterEqual(LaxComp(100, Role.solver), 130)
        self.assertNotGreaterEqual(100, LaxComp(130, Role.generator))
        self.assertGreaterEqual(100, LaxComp(130, Role.solver))

    def test_greater_equal_rel_big(self) -> None:
        self.assertNotGreaterEqual(LaxComp(100, Role.generator), 160)
        self.assertNotGreaterEqual(LaxComp(100, Role.solver), 160)
        self.assertNotGreaterEqual(100, LaxComp(160, Role.generator))
        self.assertNotGreaterEqual(100, LaxComp(160, Role.solver))

    def test_less_equal_less(self) -> None:
        self.assertLessEqual(LaxComp(0, Role.generator), 1)
        self.assertLessEqual(LaxComp(0, Role.solver), 1)
        self.assertLessEqual(0, LaxComp(1, Role.generator))
        self.assertLessEqual(0, LaxComp(1, Role.solver))

    def test_less_equal_strict(self) -> None:
        self.assertLessEqual(LaxComp(0, Role.generator), 0)
        self.assertLessEqual(LaxComp(0, Role.solver), 0)
        self.assertLessEqual(0, LaxComp(0, Role.generator))
        self.assertLessEqual(0, LaxComp(0, Role.solver))

    def test_less_equal_small(self) -> None:
        self.assertLessEqual(LaxComp(0.5, Role.generator), 0)
        self.assertLessEqual(LaxComp(0.5, Role.solver), 0)
        self.assertLessEqual(0.5, LaxComp(0, Role.generator))
        self.assertLessEqual(0.5, LaxComp(0, Role.solver))

    def test_less_equal_medium(self) -> None:
        self.assertNotLessEqual(LaxComp(1.5, Role.generator), 0)
        self.assertLessEqual(LaxComp(1.5, Role.solver), 0)
        self.assertNotLessEqual(1.5, LaxComp(0, Role.generator))
        self.assertLessEqual(1.5, LaxComp(0, Role.solver))

    def test_less_equal_big(self) -> None:
        self.assertNotLessEqual(LaxComp(2.5, Role.generator), 0)
        self.assertNotLessEqual(LaxComp(2.5, Role.solver), 0)
        self.assertNotLessEqual(2.5, LaxComp(0, Role.generator))
        self.assertNotLessEqual(2.5, LaxComp(0, Role.solver))

    def test_less_equal_rel_strict(self) -> None:
        self.assertLessEqual(LaxComp(100, Role.generator), 100)
        self.assertLessEqual(LaxComp(100, Role.solver), 100)
        self.assertLessEqual(100, LaxComp(100, Role.generator))
        self.assertLessEqual(100, LaxComp(100, Role.solver))

    def test_less_equal_rel_small(self) -> None:
        self.assertLessEqual(LaxComp(110, Role.generator), 100)
        self.assertLessEqual(LaxComp(110, Role.solver), 100)
        self.assertLessEqual(110, LaxComp(100, Role.generator))
        self.assertLessEqual(110, LaxComp(100, Role.solver))

    def test_less_equal_rel_medium(self) -> None:
        self.assertNotLessEqual(LaxComp(130, Role.generator), 100)
        self.assertLessEqual(LaxComp(130, Role.solver), 100)
        self.assertNotLessEqual(130, LaxComp(100, Role.generator))
        self.assertLessEqual(130, LaxComp(100, Role.solver))

    def test_less_equal_rel_big(self) -> None:
        self.assertNotLessEqual(LaxComp(160, Role.generator), 100)
        self.assertNotLessEqual(LaxComp(160, Role.solver), 100)
        self.assertNotLessEqual(160, LaxComp(100, Role.generator))
        self.assertNotLessEqual(160, LaxComp(100, Role.solver))


if __name__ == "__main__":
    main()
