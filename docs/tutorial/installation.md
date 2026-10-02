# Installing Algobattle

The first thing we'll need to do is install the software we need to run Algobattle matches. This
means we need two things: the Docker engine and the algobattle Python package. If you're already
familiar with one or both of these you can just use the setup you've already got and everything
should work out fine. Otherwise, this page will give you a quick rundown of what you need to do.

## Installing Docker

We use Docker to manage and run the code students write, so you'll have to have it installed in
order to use Algobattle. You can get the latest version from the
[Docker website](https://docs.docker.com/get-started/get-docker/).

!!! tip

    If you're using Linux you have the choice between Docker desktop and the Linux Docker
    Engine. If you're unsure what to get, we recommend the
    [Docker Engine](https://docs.docker.com/engine/install/).

After everything is done, you can test if it installed correctly with this:

```console
docker run hello-world
```

It should print something like this:

```console
Unable to find image 'hello-world:latest' locally
latest: Pulling from library/hello-world
4f55086f7dd0: Pull complete
Digest: sha256:5e23090353324d887c48ad5e5c56d294eab81588df9605b07d1afe895f9cc8f8
Status: Downloaded newer image for hello-world:latest

Hello from Docker!
This message shows that your installation appears to be working correctly.

To generate this message, Docker took the following steps:
 1. The Docker client contacted the Docker daemon.
 2. The Docker daemon pulled the "hello-world" image from the Docker Hub.
    (amd64)
 3. The Docker daemon created a new container from that image which runs the
    executable that produces the output you are currently reading.
 4. The Docker daemon streamed that output to the Docker client, which sent it
    to your terminal.

To try something more ambitious, you can run an Ubuntu container with:
 $ docker run -it ubuntu bash

Share images, automate workflows, and more with a free Docker ID:
 https://hub.docker.com/

For more examples and ideas, visit:
 https://docs.docker.com/get-started/
```

!!! failure "Can't Access the Docker Socket on Linux"

    If you're using Linux, a common problem is that you can't run Docker without root access right
    after the install. To fix that, follow the steps to
    [add your user to the `docker` group](https://docs.docker.com/engine/install/linux-postinstall#add-your-user-to-the-docker-group).


## Installing Algobattle

Algobattle is a Python package and unfortunately Python version and dependency management is kind of
a mess. Luckily there's a great tool called uv that solves all of those hassles for us. Throughout
this tutorial, we'll show you the correct commands to use when you have it installed, but if you
prefer to manage your Python setup yourself you can just install the `algobattle-base` package
however you prefer.

!!! warning "Using the Global Python Installation"

    You might already have Python installed on your system, e.g. if you're using Linux. In
    principle, you could use that installation, but doing that often will lead to issues later down
    the line when dependencies are installed and updated. We heavily recommend that you always
    install Algobattle in a virtual environment. The easiest way to do that is by using uv.

First, we install uv from
[the official uv site](https://docs.astral.sh/uv/getting-started/installation/). You can use
whichever installation process and version you like.

Then all we need to do is run this command:

```console
uv tool install algobattle-base==4.4.2
```

This will take care of installing the correct Python version and all dependencies we need. It also
sets up everything we need so we can easily use Algobattle. You can test if everything worked by
running this:

```console
algobattle --help
```
