# Getting Started

## Getting a problem

The idea behind the Algobattle framework is that course instructors will come up with some problem
(in the theoretical computer science meaning) that students will then write code to solve. The
Algobattle program can then take the problem definition and the code from all the student teams and
score how good each team is at solving the problem.

### Problem spec files

The most common way your instructors will give you problem definitions is by uploading them to your
Algobattle website. On the specific problem's page you can then download an Algobattle problem spec
file with the `.algo` extension. This file contains all the information we need.

!!! info "A peek behind the curtain" Despite their very fancy looking extension, `.algo` files
really just zip files with a few files inside. Algobattle uses these to set up your project folders
for you, but it doesn't handle things very well if you feed it data that doesn't have that
structure, so the file extension is there to remind you that you're not meant to process these files
manually. If you're curious you can unzip them and take a look inside yourself.

### Installed problems

Another way is to install a Python package that provides one or more problems. For example, our
[Algobattle Problem](https://github.com/Algorithmic-Battle/algobattle-problems) package which
contains a selection of basic problems. We can install it with uv just like the Algobattle base
package:

```console
uv tool install --with algobattle-problems algobattle-base
```

## Setting up the workspace

Now we can set up our dev environment where we write the code to solve the problem. I'll be showing
you some folder structures throughout but obviously the exact structure and names aren't mandatory.
Let's start with a base folder which should probably contain a `.git` folder and not much else.

With the console in our base folder we can use Algobattle to initialize our project for us, you can
use either a problem spec or an installed problem for this.

/// tab | Problem spec

```console
algobattle init -p path/to/spec/file.algo
```

///

/// tab | Installed problem

```console
algobattle init -p "Problem Name"
```

///

!!! note

    This tutorial will use the Pairsum problem as an example, if you're following along your project folder will look
    slightly different depending on which problem you chose and what your course instructors decided to include with it.

Once this has run the folder should look something like this

/// tab | Problem spec

```{ .sh .no-copy }
.
└─ Pairsum
   ├─ generator/
   │  └─ Dockerfile
   ├─ results/
   ├─ solver/
   │  └─ Dockerfile
   ├─ .gitignore
   ├─ algobattle.toml
   ├─ description.md    # this file may be missing
   └─ problem.py
```

///

/// tab | Installed problem

```{ .sh .no-copy }
.
└─ Pairsum
   ├─ generator/
   │  └─ Dockerfile
   ├─ results/
   ├─ solver/
   │  └─ Dockerfile
   ├─ .gitignore
   └─ algobattle.toml
```

///

What Algobattle has done is make a new project directory specific to this problem we're working
with, and then initialized all the required files and folders in it. Let's navigate into it for the
rest of the tutorial.

```console
cd Pairsum
```

## The `algobattle.toml` config file

Project level configuration is done inside the `algobattle.toml` file so let's take a look at what's
in there already.

/// tab | Problem spec

```toml
[match]
problem = "Pairsum"
# there might be more settings here

[teams."Red Pandas"]
generator = "generator"
solver = "solver"
```

///

/// tab | Installed problem

```toml
[match]
problem = "Pairsum"

[teams."Red Pandas"]
generator = "generator"
solver = "solver"
```

///

The config file is split into a few tables, `match` specifies exactly what each Algobattle match is
going to look like. This means that you will probably never want to change things in there since you
want to develop your programs for the same conditions they're going to see during the scored matches
run on the server. Feel free to play with the `teams`, `problem`, and `project` tables as much as
you want, nothing in them affects the structure of the match or anything on the server. In
particular, the team name used here doesn't need to match the one used on your Algobattle website.
The filled in settings so far all just are paths to where Algobattle can find certain files or
folders. There's a lot more things you can configure, but we're happy with the default values for
now.

!!! tip

    If you're curious what exactly everything in here means you can read the
    [config docs](../advanced/config.md). But for now we recommend staying here since things will be
    much clearer after you're familiar with things here.

## The `problem.py` file

!!! note

    This will only exist if you used a problem spec file.

This is what Algobattle uses as the problem definition. Once you're familiar with the way Algobattle
does things you can cross-reference this to see what exactly your code needs to do. But it's also
not directly meant to be human-readable and easily understandable, in particular if you're not
familiar with Python and Pydantic.

## The `description.*` file

!!! note

    This will only exist if you used a problem spec file and your course instructors included
    it.

This is the version of the problem definition that's more fun to read. It can be whatever your
course instructors wanted to include, but most commonly is a Markdown or Pdf file.
