Timespan = Annotated[int, Interval(ge=0, le=(2**64 - 1) / 5)]
Machine = Annotated[int, Interval(ge=1, le=5)]


class Instance(InstanceModel):
    """The Scheduling problem class."""

    job_lengths: list[Timespan]

    @property
    def size(self) -> int:
        return len(self.job_lengths)
