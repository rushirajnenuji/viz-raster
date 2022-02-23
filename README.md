# viz-raster

## PDG visualization pipeline for raster processing

Input for the raster process should be the output from the [PDG viz-staging](https://github.com/PermafrostDiscoveryGateway/viz-staging) step.

## Running

Uses Python version `3.9` and packages listed under `requirements.txt`

1. Make sure you have Python version 3.9 installed and that you know the path to that version of Python (try `which python3.9`).
2. Clone this repository.
3. From within the newly created directory, create a virtual environment: `/usr/local/bin/python3.9 -m venv .venv` (where `/usr/local/bin/python3.9` is your path to version 3.9 of Python).
4. Activate the environment: `source .venv/bin/activate`.
5. Install dependencies: `pip install -r requirements.txt`.
6. Run: `python main.py -i /path/to/input/shapefiles -o /path/to/output/directory`.