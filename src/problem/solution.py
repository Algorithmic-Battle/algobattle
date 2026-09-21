Timespan = Annotated[int, Interval(ge=0, le=(2**64 - 1) / 5)]
Machine = Annotated[int, Interval(ge=1, le=5)]


class Solution(SolutionModel[Instance]):
    """A solution to a Job Shop Scheduling problem."""

    assignments: Annotated[list[Machine], SizeLen]

    @minimize
    def score(self, instance: Instance, role: Role) -> float:
        finish_time = [0] * 5
        for duration, machine in zip(instance.job_lengths, self.assignments):
            finish_time[machine - 1] += duration * machine
        return max(finish_time)
