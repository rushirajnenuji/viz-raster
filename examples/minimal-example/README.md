# Minimal Example

This is a minimal example of the pdgraster package that is useful for
development and testing. The input data is pre-staged so only the rasterization
steps are run.

Steps:

1. Clone this repository
   ```bash
   git clone https://github.com/PermafrostDiscoveryGateway/viz-raster
   ```
2. Change to the examples/minimal-example directory
   ```bash
    cd viz-raster/examples/minimal-example
    ```
3. Start up a virtual environment
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install the package in development mode
   ```bash
   pip install -e ../../
   ```
   - **Note**: You might need to install `libspatialindex` or
   `libspatialindex-dev` on your system if you have not already done so.
   - **Note**: You may also need to install `pdgstaging` from github: `pip install git+https://github.com/PermafrostDiscoveryGateway/viz-staging`
6. Run the example
   ```bash
   python make-rasters.py
   ```
