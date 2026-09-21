# Docker

Algobattle uses Docker to run the programs students write. This lets us support students using any language, easily
restrict their time, space, and CPU usage, provide a safe environment, and much more.

## Basic functionality

If you haven't used Docker before, getting your head around what it's doing and what you need to do can be a bit
confusing. Luckily we do not need to understand most of its behind the scenes working and, the parts that we do need are
pretty straightforward. You can think of Docker as a virtual machine management tool, it lets you create _images_ that
basically are save files of an entire computer including the OS and everything else installed on it. We can then run
these as _containers_, independent virtual machines that start off from that save file and then run some code.

Algobattle uses such images and containers to manage the students' programs. What we actually care about when receiving
e.g. the path to a generator is not all the source files and whatever else might be in that folder, but the Docker
image that can be built using it.

Since containers run essentially as virtual machines, they are entirely separate from the host machines' OS. In
particular, they do not share a file system. This is why the programs do not see the host machines actual files and
have to read/write from the `/input` and `/output` directories. Algobattle creates the containers with special links
between the host machine's file system and these folders and then looks only at these directories.

## Dockerfiles

Dockerfiles are what Docker uses to create images. When Algobattle is told that there's a generator in `generator/`, it
will ask Docker to _build_ the Dockerfile in that folder. Docker then takes the file found at `generator/Dockerfile`
and interprets every line in it as a particular step in the build process. These steps are completed in order of their
occurrence in the Dockerfile. Once Docker has completed every step, the build is complete, and we get the finalized
image. This image will essentially look exactly like the virtual machine did after the last build step ran, plus some
special Docker metadata.

The full specification of what Dockerfiles can contain is [here](https://docs.docker.com/engine/reference/builder/), but
most of it is not super relevant for us. The most important commands are listed here:

#### The `#!Dockerfile FROM` statement

The first line of every Dockerfile has to be a `#!Dockerfile FROM` statement, the most basic example is
`#!Dockerfile FROM scratch`. This line tells Docker what to base your image off of, `#!Dockerfile FROM scratch`
means that it starts with a completely empty file system. If we do that we need to first install an operating system,
configure it enough to be usable, and then install whatever we actually want to run. We can make our Dockerfiles much
simpler by using one of the already existing images in the [_Docker Hub_](https://hub.docker.com/)
in our `#!Dockerfile FROM` statement instead. Instead of starting with an empty file system we then start with the file
system of that image.

All major operating systems have images containing a fresh installation of them on the Docker Hub. For example,
[here](https://hub.docker.com/_/alpine) is the official Alpine image, [here](https://hub.docker.com/_/ubuntu) is Ubuntu,
and [here](https://hub.docker.com/_/debian) is Debian. If you want your code to run in a clean environment with nothing
else you can use any of these as your base.

!!! warning
    In principle Docker can also run Windows OS's inside the containers, but this requires special setup on the host
    machine. In particular, every image needs to then be a Windows image, there is no way to control both Linux and
    Windows containers at the same time. We recommend course administrators configure Docker to run Linux containers
    (this is the default) and inform students that they are required to use Linux in their images.

    Talk to your course administrators if you are a student and unsure about what OS to use.

Since you want the container to execute some code you will most likely then need to install a compiler or runtime for
whatever language you're using. We can easily skip this intermediary step and instead base our image off of one that
already includes this. Most languages have officially published images that contain some Linux distro and an
installation of everything that compiler/interpreter needs to work. For example, [here](https://hub.docker.com/_/python)
is Python's and [here](https://hub.docker.com/_/rust) Rust's.

Images on the Docker Hub can also be versioned using tags. For example, the official Python image has dozens of slightly
different versions that come with different OS's, Python versions, etc. If you want to use a specific tag you need to
list it in the `#!Dockerfile FROM` statement after a colon. For example, if your code needs Python 3.10 you can write
`#!Dockerfile FROM python:3.10`.

!!! tip
    Different languages use different schemes for tagging their images. Always check the official page on the
    [Docker Hub](https://hub.docker.com/) to make sure you're getting the right version of everything.

#### Changing the `#!Dockerfile WORKDIR`

As the name suggests, `#!Dockerfile WORKDIR /some/dir` changes the current working directory. All subsequent commands
will be executed from `/some/dir`. Note that the path must be absolute. This also can also affect where the program
that runs when you start a container from the image if you change the working directory before the `#!Dockerfile CMD`
or `#!Dockerfile ENTRYPOINT` line.

#### `#!Dockerfile COPY`ing files

Now that we have a container that includes our language's runtime we also need to include our code and all other files
we may need. The `#!Dockerfile COPY` command does exactly this. For it, we just list the path to the file on the host
file system, and the path it should be at in the image. Our example has the generator code in a single file next to the
Dockerfile, so we can place it into the root directory of the image with `#!Dockerfile COPY main.py /`. Paths can be
absolute or relative, and you can specify multiple sources in a single line. You can also use a glob-like syntax to
match multiple specific files.

??? example
    All of these are valid `#!Dockerfile COPY` statements:

    - `#!Dockerfile COPY some_file.py .` results in `some_file.py` being placed in the current directory
    - `#!Dockerfile COPY some_dir target_dir/` results in every file in `some_dir` and all its subfolders being placed
        in `target_dir/`, effectively copying over the entire tree rooted at `some_dir` and rooting it at `target_dir`
    - `#!Dockerfile COPY nested/location/source.txt .` copied the source file into the current directory
    - `#!Dockerfile COPY multiple.py source.json files.txt single/target/dir/` copies both source files to the target
        directory
    - `#!Dockerfile COPY source.rs /absolute/target` copies the file into the target directory
    - `#!Dockerfile COPY *.py /` copies all Python files in the current directory into the root of the image

!!! warning "The build context"
    You cannot `#!Dockerfile COPY` files outside the directory containing the Dockerfile. That is
    `#!Dockerfile COPY ../../something ./` will not work. This is not a limitation of Algobattle but just a side effect
    of how Docker works.

!!! tip "trailing slashes"
    Notice how we sometimes specify trailing slashes even though they're not strictly needed. This is to make sure that
    Docker knows we are referring to a directory, not a file. If you just write `#!Dockerfile COPY something other`
    and `something` is a file it will place it into the current directory and rename it `other`. If you want it to
    instead keep the name and place it in the `other/` directory, you need to include the trailing slash.

#### `#!Dockerfile RUN`ning commands

You can use `#!Dockerfile RUN some shell command` to execute `#!shell some shell command` in a shell during the image
build step. This command will have access to everything that was copied into the image beforehand and anything that
previously ran commands created. Most often, this is used to install dependencies of your program.

This statement has two forms, the first `#!Dockerfile RUN some shell command`, and the other
`#!Dockerfile RUN ["some", "shell", "command"]`. For our purposes they do largely the same thing, but their differences
are explained [here](https://docs.docker.com/engine/reference/builder/#run)

#### Specifying the program `#!Dockerfile CMD`

Lastly, the container that runs from your image needs to know what it should actually do. You can specify this with the
`#!Dockerfile CMD` statement. Its arguments form some shell command that is not executed during the build step,
but when the container starts.

Similar to run this command also has the same two forms, and you can choose whichever you prefer, though the list style
syntax is usually preferred. They are explained in detail [here](https://docs.docker.com/engine/reference/builder/#cmd).

## Tips and Tricks

### Faster builds with better caching

Building docker images can take quite a long time depending on what is happening in the build. When you're developing
your programs and keep making small changes to your code before rebuilding this can be incredibly annoying. Luckily
Docker implements a cache of so-called _layers_ for us. You can think of layers as basically being break points in
between every line in your Dockerfile. Let's look at an example:

```Dockerfile
FROM python:3.11

WORKDIR /algobattle
COPY . ./
RUN pip install .

WORKDIR /
CMD [ "python", "-m", "generator" ]
```

The first layer is just the original Python base image, the next is the base image plus the change of the working
directory, then the base image plus the changed working directory, plus the copied files, etc. If you now build this
Dockerfile Docker will automatically cache every layer separately. Subsequent builds will then use these cached layers
up until the point where things have changed and thus need to be built again.

The important part here is being aware of what causes Docker to invalidate caches, and make sure that it happens as
late in the Dockerfile as possible. `#!Dockerfile COPY` commands invalidate caches whenever the files you're copying
over have changed. This means that every time you make a code change to the above code you invalidate the cache used
for the `#!Dockerfile COPY` and all subsequent commands, which means that pip has to reinstall every dependency every
time you rebuild the image. To better cache your dependencies you can install them before you copy over your code:

```Dockerfile
FROM python:3.11

WORKDIR /algobattle
COPY pyproject.toml ./
RUN pip install .
COPY . ./
RUN pip install .

WORKDIR /
CMD [ "python", "-m", "generator" ]
```

This might look slower at first glance since it's doing a lot more, and it will be slightly slower during the first
build, but if you're using dependencies that take a bit to install this will be much faster in the long run. Obviously,
the same ideas apply to other languages. To make the best use of the cache, you want your `#!Dockerfile COPY` commands
to be as selective as possible and be executed as late as possible.

!!! info "`#!Dockerfile RUN` and caching"
    The `#!Dockerfile RUN` command never invalidates the cache! Even if you are running some command that e.g. pulls
    from the web and the content of that download changes, Docker will not rerun it unless something before it created
    a cache miss. This is great most of the time since we're downloading deterministic data like dependencies, but can
    cause issues if you expect to dynamically update data.

### Building images yourself {#building-images}

Sometimes it's nice to build images yourself to debug them. You can find the full documentation on the
[Docker build page](https://docs.docker.com/engine/reference/commandline/build/), but the basics aren't as complicated
as they make it out to be! In its purest form you just run

```console
docker build path/to/build/dir
```

With a path pointing to the directory containing the Dockerfile you want to build. This will then build the image and
display a detailed log including any error messages in the console. If you want to then refer back to the image you'll
have to use its ID, which can become quite annoying, so you probably want to tag the image when you build it:

```console
docker build -t some_name path/to/build/dir
```

### Running containers yourself

You will probably also want to run containers yourself. This command is very powerful and even more complicated, if
you're feeling brave you can check out the docs on the
[Docker run page](https://docs.docker.com/engine/reference/commandline/run/). The most common style of command you will
need is

```console
docker run -ti some_name
```

This runs the container and then mirrors its stdin, stdout, and stderr to your console, effectively behaving as though
you've opened a terminal inside the running container. `some_name` needs to be the same name you gave the image when
you built it.

!!! tip "Algobattle image names"
    If you're using the `name_images` Algobattle setting (defaults to `#!toml true`) the images Algobattle creates will
    be named like `algobattle_{team_name}_{program_type}`, so e.g. `algobattle_crows_generator` or
    `algobattle_red_pandas_solver`. You can run these directly without having to build them yourself.

Since the program expects the usual Algobattle input in the `/input` directory, which will be missing if you run it
yourself, the container will most likely just crash. What's more useful is to tell Docker to use some other command
when running the container. Like this:

```console
docker run -ti some_name bash
```

This will run `some_name` but without executing the `#!Dockerfile CMD` command and running `bash` instead. So we
effectively just open a terminal inside the container and can then inspect the container, build artefacts, etc to debug
things.
