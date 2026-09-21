# Problems

If you're currently a student in an Algobattle lab course, you've probably wondered how exactly the problems work, found
weird behaviour that you think might be a bug, or wanted to find out the exact file format it will accept. This page
teaches you how to get all that info from just the files you've already got in your Algobattle project folder!

!!! note
    This page goes over the anatomy of an Algobattle problem and how you can get what you're looking for from your
    project folder. This means it's mainly aimed at students who are trying to get more familiar with the course or a
    particular problem they're dealing with and course instructors who want to get an overview over how they work.
    If you instead are a course instructor looking to make a problem from scratch the
    [instructor tutorial](../instructor/problem/intro.md) has more detailed info on that process.

## Overall Structure

A typical problem file looks something like this

```py title="problem.py"
{!> problem/problem.py !}
```

What exactly the problems we discuss here are about is not important for this guide. If you're still curious you can
find them all in our
[Algobattle problems](https://github.com/Benezivas/algobattle-problems/) repo with
additional explanations. We will now go through this file and explain what each section does.

## The Instance Class

This class defines what each instance of the problem will look like. It both tells you what your generator needs to
create and what input your solver will receive. At the top of the class you will find a block of attribute definitions.
In our case this is only a single line.

```py hl_lines="1 8"
{!> problem/instance.py !}
```

This tells us that each instance's json file contains a single key, `job_lengths`, which maps to a list of Timespans.
As we can see from the type alias above the class definition, a Timespan just is an integer between 0 and
(2^64^ - 1) / 5. What that means is that if you're programming your generator you must ensure to not output any numbers
that do not fall in this range, and when implementing your solver you can safely assume that all inputs you will receive
are in it.

### Instance Size

The instance size is defined by the `size` property.

```py hl_lines="10-12"
{!> problem/instance.py !}
```

!!! note
    You should not include a `size` key in your instances. It will be computed from other attributes of the instance.

### Additional Validation

Some problem instances, like this one for the Hikers problem, also include a `validate_instance` method.

```py
class HikersInstance(InstanceModel):
    """The Hikers instance class."""

    hikers: list[tuple[u64, u64]]

    @property
    def size(self) -> int:
        """The instance size is the number of hikers."""
        return len(self.hikers)

    def validate_instance(self) -> None:
        super().validate_instance()
        if any(min_size > max_size for min_size, max_size in self.hikers):
            raise ValidationError("One hiker's minimum group size is larger than their maximum group size.")
```

This method contains further code that validates which inputs are allowable and which aren't. If you generate an
instance that causes this method to raise an error, your instance will be considered invalid, and you will lose the
fight.

## The Solution Class

This class is very similar to the instance class, except it specifies what solutions look like. In our case we again
have a single attribute and thus the solutions contain only a single key.

```py hl_lines="2 8"
{!> problem/solution.py !}
```

This time we not only use an alias to specify the allowable range of integer values, but also the `SizeLen` marker which
means that the number of `assignments` must be exactly the same as the instance's size.

### Solution Score

Most solutions also have a `score` method. This tells Algobattle what the goal of this problem is and how to weigh
different solutions.

```py hl_lines="10-15"
{!> problem/solution.py !}
```

The decorator at the top can either be `maximize` or `minimize` and tells us if bigger or smaller score values are
considered to be better. The function then computes some non-negative real number based on the instance and solution,
this will be this solutions' score. Each fight in a battle will receive a single score, that will be calculated by
comparing the solution score of the generator's and solver's solutions.

In our example the score just is the longest time a machine takes to complete all jobs. If in the generator's solution
all machines complete their jobs in 10 units, but the solver's solution takes 12, the fight's score will be
approximately 0.83.

### Additional Validation

Just like instances can undergo extra validation, so can solutions. They use the `validate_solution` method for this.

```py hl_lines="6-13"
class Solution(SolutionModel[HikersInstance]):
    """A solution to a Hikers problem."""

    assignments: dict[Hiker, u64]

    def validate_solution(self, instance: HikersInstance, role: Role) -> None:
        super().validate_solution(instance, role)
        group_sizes = Counter(self.assignments.values())

        for hiker, group in self.assignments.items():
            min_size, max_size = instance.hikers[hiker]
            if not (min_size <= group_sizes[group] <= max_size):
                raise ValidationError("A Hiker is not happy with their assignment!")

    @maximize
    def score(self, instance: HikersInstance, role: Role) -> float:
        return len(self.assignments)
```

## The Problem Constructor

The last part of the problem file actually creates the problem.

```py hl_lines="36-41"
{!> problem/problem.py !}
```

It contains the name of the problem and references to the two classes we discussed. It also specifies what the smallest
reasonable size of this problem is. In our case an instance should contain at least one job for each machine, so the
minimum size of this problem is 5.
