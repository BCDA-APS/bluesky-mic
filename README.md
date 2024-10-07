# aps_bs_instrument_template
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