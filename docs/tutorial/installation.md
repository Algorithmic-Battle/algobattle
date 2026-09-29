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
docker --version
```

## Installing Algobattle

Algobattle is a Python package and unfortunately Python version and depenency management is kind of
a mess. Luckily there's a great tool called uv that solves all of those hassles for us.
Throughout this tutorial, we'll show you the correct commands to use when you have it installed, but
if you prefer to manage your Python setup yourself you can just install the `algobattle-base`
package however you prefer.

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
uv tool install algobattle-base
```

This will take care of installing the correct Python version and all dependencies we need. It also
sets up everything we need so we can easily use Algobattle. You can test if everything worked by
running this:

```console
algobattle --help
```
