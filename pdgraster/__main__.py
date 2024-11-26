import argparse
import logging
import logging.config

from pdgraster import RasterTiler

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Rasterizes staged vector tiles for the PDG viz tiling " "pipeline"
    )
    parser.add_argument(
        "-c",
        "--config",
        help="Path to configuration JSON file",
        default="config.json",
        type=str,
    )

    args = parser.parse_args()

    tiler = RasterTiler(args.config)
    tiler.rasterize_all()

    logging.info("Done")
    logging.shutdown()
    exit(0)
