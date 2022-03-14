# viz-raster

## PDG visualization pipeline for raster processing

Converts pre-tiled vector output from from the [PDG
viz-staging](https://github.com/PermafrostDiscoveryGateway/viz-staging) step
into a series of GeoTIFFs and web-ready image tiles at a range of zoom levels.
View the content under `example` to see the type of output produced. Most parts
of the process are configurable, including the methods used to summarize vector
data into rasters, the color palette, and the size of the tiles. See the
documentation in `ConfigManager.py` for more details.

## Running

Uses Python version `3.9` and packages listed under `requirements.txt`

1. Make sure you have Python version 3.9 installed and that you know the path
   to that version of Python (try `which python3.9`).
2. Clone this repository.
3. From within the newly created directory, create a virtual environment:
   `/usr/local/bin/python3.9 -m venv .venv` (where `/usr/local/bin/python3.9`
   is your path to version 3.9 of Python).
4. Activate the environment: `source .venv/bin/activate`.
5. Install dependencies: `pip install -r requirements.txt`.

See `example/main.py` for an example of how to convert vector tiles to raster
tiles.