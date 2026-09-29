# Algorithmic Battle

The lab course "Algorithmic Battle" is offered by the 
[Computer Science Theory group of RWTH Aachen University](https://tcs.rwth-aachen.de/)
since 2019. This repository contains the necessary code and
documentation to set up the lab course yourself.

In an Algorithmic Battle, pairs of teams compete against one another
in order to solve a problem of your choice, e.g. a problem from the
class NP. The teams each design a `generator`, that outputs
hard-to-solve instances for a given instance size, as well as a
`solver` that accepts an instance and outputs a solution to it as
quickly as possible.

The framework is written to be completely language-agnostic regarding
the code of the `generator` and the `solver`, as each is wrapped in a
docker container that only needs to adhere to an I/O structure of your
choice (by default, in the form of `json`-files.)

If you are interested in how to use the framework for a
lab course of your own, please consult the teaching concept in
the [documentation](https://www.algobattle.org/docs/).
# Installation and Usage
This project is developed and tested on all major operating systems.

Please consult the official [documentation](https://www.algobattle.org/docs/)
for detailed instructions on installation and usage.

# Related projects
This repository only includes the core framework for executing an
`Algorithmic Battle`. For a selection of concrete problems that you
can use to play around with the framework, have a look at the
[algobattle-problems](https://github.com/Algorithmic-Battle/algobattle-problems)
repository. These are problems that have been posed to students in
some form over the past years.

While the framework provides all essential tools to host a tournament
yourself, e.g. in the form of a lab course, you may be interested in
the [algobattle-web](https://github.com/Algorithmic-Battle/algobattle-problems)
project.  The `algobattle-web` project implements a webframework with
which you are able to comfortably manage your students teams and their
code, your problem files and their documentation as well as schedule
matches to be fought between registered student teams, using the
`algobattle` API.

# Contributing

We welcome any input on how to make this project accessible to as many
people as possible. If you have feedback regarding the usage of the
framework, the documentation or would even like to help us out with
corrections, new features, or translations, feel free to open an issue
or pull request. We have developed this project on the basis of
practical experience inside our lab courses, thus some design elements
may be unintuitive to you. Feel free to point out anything that
appears odd to you.

# Funding
The development of version `4.0.0` was funded by
[`Stiftung Innovation in der Hochschullehre`](https://stiftung-hochschullehre.de/en/) (Project 
`FRFMM-106/2022 Algobattle`) and by the [Department of Computer Science of
RWTH Aachen University](https://www.informatik.rwth-aachen.de/go/id/mxz/?lidx=1).