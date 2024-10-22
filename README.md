# Model Package for Bluesky Instrument Minimal Installation

Model of a Bluesky Data Acquisition Instrument in console, notebook, & queueserver.

## Installation
Clone the repository
```bash
git clone git@github.com:grace227/bluesky-mic.git
cd bluesky_mic
```

Set up the development environment.

```bash
export ENV_NAME=bs_model_env
conda create -y -n $ENV_NAME python=3.11 pyepics
conda activate $ENV_NAME
pip install -e ."[all]"
```

## IPython console
To start the bluesky instrument session in a ipython execute the below command in a terminal
```bash
ipython
```
Inside the ipython console execute
```py
from mic_instrument.startup import *
```

## Jupyter notebook

Start JupyterLab, a Jupyter notebook server, or a notebook, VSCode.

Start the data acquisition:

```py
from mic_instrument.startup import *
```

## Sim Plan Demo
To run some simulated plans that ensure the installation worked as expected please run the below inside an ipython session or a jupyter notebook after starting the data acquisition
```py
RE(sim_print_plan())
RE(sim_count_plan())
RE(sim_rel_scan_plan())
```

See this [example](./docs/source/demo.ipynb).

## Configuration files
The files that can be configured to adhere to your preferences are:
- `configs/iconfig.yml` - configuration for data collection
- `configs/logging.yml` - configuration for session logging to console and/or files
- `qs/qs-config.yml`    - contains all configuration of the QS host process. See the [documentation](https://blueskyproject.io/bluesky-queueserver/manager_config.html) for more details of the configuration.

## queueserver

The queueserver has a host process that manages a RunEngine. Client sessions
will interact with that host process.

### Run a queueserver host process

Use the queueserver host management script to start the QS host process.  The below option stops the server (if it
is running) and then starts it.  This is the usual way to (re)start the QS host
process. Using the below command the process runs in the background.

```bash
./qs/qs_host.sh restart
```

For a good practice, it will be good to double check if the qs is running after executing the command above with the following command
```bash
./qs/qs_host.sh status
```

### Run a queueserver client GUI
To run the gui client for the queueserver you can use the below command inside the terminal
```bash
queue-monitor &
```

### Shell script explained

A [shell script](./qs/qs_host.sh) is used to start the QS host process. Below are all the command options, and what they do.
```bash
(bstest) $ ./qs/qs_host.sh help
Usage: qs_host.sh {start|stop|restart|status|checkup|console|run} [NAME]

    COMMANDS
        console   attach to process console if process is running in screen
        checkup   check that process is running, restart if not
        restart   restart process
        run       run process in console (not screen)
        start     start process
        status    report if process is running
        stop      stop process

    OPTIONAL TERMS
        NAME      name of process (default: bluesky_queueserver-)
```

Alternatively, run the QS host's startup comand directly within the `qs/`
subdirectory.

```bash
cd ./qs
start-re-manager --config=./qs-config.yml
```

## Testing

Use this command to run the test suite locally:
```bash
pytest -vvv --lf ./src
```

# Warnings
##  For the Bluesky Queueserver.

The QS host process writes files into the qs directory. This directory can be
relocated. However, it should not be moved into the instrument package since
that might be installed into a read-only directory.

# OLD Stuff
## Installation Instructions

The following line will install the isn_bs_instrument in the enviornment and it doesn't require public network access

```
pip install -e .
```

### With Queserver
Check if a queueserver instance is running already using the:

```
screen -ls
```

If there is an Redis process occupying the tcp port, use the following command to find the running redis and terminate it

```
ps aux | grep redis
kill -9 process_id
```


To start (it only launches the Redis server)

```bash
./scripts/bs_qs_screen_starter.sh run
```

To view the Bluesky Queue GUI:

```
queue-monitor &
```
