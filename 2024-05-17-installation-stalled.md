# installation notes

2024-05-17, prj

Got stuck in step 2 while trying to install the conda environment.
(https://bcda-aps.github.io/bluesky_training/reference/_create_conda_env.html#install-the-bluesky-environment)

Must install from staff19id account on a workstation with public access.

Actually, no conda environment could be created.  Might be due to IT maintenance.  
Checking from another network, it appears the conda server is not responding.
Try again on Monday.  Here's an attempt at a basic Python installation:

```bash
(base) staff19id@otz ~/bluesky $ conda create -n test python=3.12
Channels:
 - defaults
 - conda-forge
 - apsu
 - aps-anl-tag
Platform: linux-64
Collecting package metadata (repodata.json): / Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError('<urllib3.connection.HTTPSConnection object at 0x7f67e766d960>: Failed to establish a new connection: [Errno 101] Network is unreachable')': /aps-anl-tag/linux-64/repodata.json

\ Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ReadTimeoutError("HTTPSConnectionPool(host='conda.anaconda.org', port=443): Read timed out. (read timeout=9.15)")': /conda-forge/noarch/repodata.json

/ Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))': /apsu/linux-64/repodata.json

Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))': /conda-forge/linux-64/repodata.json

Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))': /apsu/noarch/repodata.json

\ Retrying (Retry(total=2, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ReadTimeoutError("HTTPSConnectionPool(host='conda.anaconda.org', port=443): Read timed out. (read timeout=9.15)")': /aps-anl-tag/noarch/repodata.json

\ Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ReadTimeoutError("HTTPSConnectionPool(host='conda.anaconda.org', port=443): Read timed out. (read timeout=9.15)")': /aps-anl-tag/linux-64/repodata.json

/ Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ReadTimeoutError("HTTPSConnectionPool(host='conda.anaconda.org', port=443): Read timed out. (read timeout=9.15)")': /conda-forge/noarch/repodata.json

/ Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ReadTimeoutError("HTTPSConnectionPool(host='conda.anaconda.org', port=443): Read timed out. (read timeout=9.15)")': /aps-anl-tag/noarch/repodata.json

| Retrying (Retry(total=1, connect=None, read=None, redirect=None, status=None)) after connection broken by 'ProtocolError('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))': /apsu/noarch/repodata.json

| Retrying (Retry(total=0, connect=None, read=None, redirect=None, status=None)) after connection broken by 'NewConnectionError('<urllib3.connection.HTTPSConnection object at 0x7f67e766f910>: Failed to establish a new connection: [Errno 101] Network is unreachable')': /aps-anl-tag/noarch/repodata.json

failed

CondaHTTPError: HTTP 000 CONNECTION FAILED for url <https://conda.anaconda.org/conda-forge/linux-64/repodata.json>
Elapsed: -

An HTTP error occurred when trying to retrieve this URL.
HTTP errors are often intermittent, and a simple retry will get you on your way.
'https//conda.anaconda.org/conda-forge/linux-64'
```
