# Introduction

!!! abstract "Brush up on the basics"
    This page assumes you're already familiar with the basics of how Algobattle works. If that's not you yet, you can
    read up on it in the [student tutorial](../../tutorial/getting_started.md).

In each Algobattle course the student teams are given a few problems that they will then need to solve. This means that
we need to first come up with what those problems are and then how to tell Algobattle about them.

## Using a Prebuilt Problem

The fastest way to get up and running is to use one of the problems we've already developed in the
[Algobattle Problems](https://github.com/Algorithmic-Battle/algobattle-problems) repository. These contain everything you need to
use them in a course and have been tested already. But of course half the fun is coming up with your own ideas and
tailoring the problems to your students!

## Coming up with a Problem Idea

Before we start to write any code, we need to come up with the abstract problem that students should solve. 
For this, it may be easiest to first review what a problem actually is. Abstractly it's just a specification of
instances and solutions, and a mapping of instances to valid solutions. But of course, that doesn't really tell us much.
What's more helpful is to look at some examples of well known problems:

- Satisfiability. Given a formula of propositional logic (e.g. `(A ∨ ¬C) ∧ (¬A ∨ B)`), determine if there is some truth
    assignment to the variables that make it true.

- Reachability. Given a graph and two vertices `v`, `w` in it, determine if there is some path from `v` to `w`.

- Independent Set. Given a graph, compute the largest set of its vertices that have no edges between any two of them.

- Subset Sum. Given a list of numbers and a target, determine if there is some subset of the list that sums to the
    target.

- Pairsum. Given a list of numbers, find two pairs `a, b` and `c, d` of numbers in it that have the same sum
    `a + b = c + d`.

We can see that each of these uses some fairly common mathematical structure (a formula, a graph, a list of numbers,
etc.) to specify instances and then specifies some goal that the solver needs to achieve. Sometimes this can be a simple
yes or no answer, but it can also be a more complicated solution.

!!! warning "Validation vs Verification"
    We use the terms _validation_ and _verification_ to refer to two distinct things. To validate an instance or
    solution is to check whether it is, in principle, valid and well-formed. For example, in the Subset Sum problem
    the validation process confirms that the instance is indeed a properly formatted list of numbers and a target or
    that the solution is a subset of the numbers in the instance that was given. On the other hand verification actually
    checks whether a solution correctly solves the given instance.

    Put shortly: `Otters` is an _invalid_ solution to `5 + 3`, `17` is _valid_ but does not pass _verification_, and
    `8` is the actually correct solution that is _valid_ and passes _verification_.

## Conceptual Requirements

Algobattle is very flexible, so we can let our creativity run almost completely free here! But there still are some
considerations that make some types of problems more well-suited for Algobattle framework. Essentially, we are
interested in two characteristics, both which revolve around the solutions of a problem:

1. It is fairly fast (say, at most quadratic asymptotic runtime) to check if a proposed instance or solution is valid.
    This does not impact most problems since the requirements for valid instances and solutions are very direct and
    easy to verify. But there are some tricky cases where a simple sounding requirement ends up being costly to
    validate.

2. The solution of an instance can be verified significantly faster than it would take to actually solve it.
    In particular, the solution should contain all the information needed to determine if it is correct. Problem
    solutions that are simple yes or no answers or that rely on hard to compute outside information are hard to verify
    quickly and thus should be avoided.

Both are soft requirements which you can technically ignore. This may, however, impact your match runtime significantly.
The validation and verification process does not have a built-in timeout, meaning that if you try to solve an instance
during it, the framework will not continue until this solution was found or an error is encountered.

There is no restriction on the data encoding format that problems use. We only enforce that all data is passed in the
form of files, regardless of their encoding or even how many a single instance/solution uses. However, almost all
problems we use in our courses use a single `.json` file since this is such a universally supported file format, there
is great support built into Algobattle itself, and you can encode most things into it fairly well. For a deeper dive
into how `json` or other I/O formats work, have a look at the [I/O Section](io.md).

## Phrasing Problems for Algobattle

We can now look back at the problems defined above to see if they're suited for Algobattle and how we can best phrase
them. In particular, let's look at the Satisfiability and Independent Set problems.

Satisfiability instances are very easy and fast to validate since you just need to do some basic syntax checks.
Solutions are yes or no answers, also trivial to validate. But verifying them is hard. There is currently no known
algorithm that can do this efficiently, meaning we would have to spend a lot of time solving every instance.
A better way to phrase this problem would be to instead ask for the variable assignment itself, not just whether it
exists. Then you can simply fill in the truth values and confirm that the formula evaluates to true. However, this
does not work for the negative case where no such assignment exists.

Independent Set uses a graph for its instances, which have various common and simple to validate encodings. Algobattle
even comes with an easy-to-use one built in. Solutions are more complicated than just a yes or a no, but it still is no
issue to check that a set of vertices does not have any edges between them. But there is a different problem with
verifying the solutions, we can't easily know if a proposed independent set actually is the biggest.

Both of these can be solved in the same way. By having each instance come with a valid solution. In the case of
Satisfiability we then guarantee that there is indeed some satisfying variable assignment. And for Independent Set we
slightly relax our problem so that we don't ask for _the biggest_ independent set but just one that is at least as big
as the one we already know exists. Since this very commonly what we want it is the default in Algobattle. We do this by
having the generator also output a solution in addition to the instance. You can change this behaviour when creating
your problem later.

## Formalizing the Problem

Now that we have the broad idea of how our problem should work we need to formalize it so that Algobattle can work with
it. To do this we [make a problem file](problem_file.md).
