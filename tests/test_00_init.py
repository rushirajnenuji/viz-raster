import logging
import logging.config

import pdgraster

import pdgstaging  # For staging


def test_init():
    """Initialize tests and show they are working."""
    assert 1 == 1


def test_rasterize():
    """Test rasterize_all produces valid tiles"""
    log_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "formatter": "standard",
                "class": "logging.StreamHandler",
            },
            "file_handler": {
                "level": "INFO",
                "filename": "example/viz-raster-example.log",
                "class": "logging.FileHandler",
                "formatter": "standard",
            },
        },
        "loggers": {
            "": {"handlers": ["file_handler"], "level": "INFO", "propagate": True}
        },
    }

    logging.config.dictConfig(log_dict)

    # A configuration that will create rasters for z-levels 6 to 13 in the
    # WGS1984Quad tms. The GeoTIFFs that are created will have two bands, and
    # the web_tiles will have two possible layers: one for each of the dicts listed
    # under statistics. The first statistic counts the number of polygons in each
    # pixel. The second calculates the proportion of each pixel that is covered by
    # polygons. This config could also be a JSON file, and the path could be passed
    # to RasterTiler.
    my_config = {
        "tms_id": "WGS1984Quad",
        "tile_path_structure": ["style", "tms", "z", "x", "y"],
        "dir_input": "example/input-data",
        # input: tiled vector files created by viz-staging
        "dir_staged": "example/staged-vectors",
        # output: where the GeoTIFFs and web tiles should be saved
        "dir_geotiff": "example/geotiffs",
        "dir_web_tiles": "example/web-tiles",
        "filename_staging_summary": "example/staging-summary.csv",
        "ext_input": ".shp",
        "ext_web_tiles": ".png",
        "z_range": (6, 13),
        "tile_size": (128, 128),
        "statistics": [
            {
                "name": "iwp_count",
                "weight_by": "count",
                "property": "centroids_per_pixel",
                "aggregation_method": "sum",
                "resampling_method": "sum",
                "val_range": [0, None],
                "palette": ["rgb(102 51 153 / 0.1)", "#d93fce", "lch(85% 100 85)"],
            },
            {
                "name": "iwp_coverage",
                "weight_by": "area",
                "property": "area_per_pixel_area",
                "aggregation_method": "sum",
                "resampling_method": "average",
                "val_range": [0, 1],
                "palette": ["rgb(102 51 153 / 0.1)", "lch(85% 100 85)"],
            },
        ],
    }

    # To stage vector files, use the TileStager. This will take the large shapefile
    # that is in the input-vectors directory and create smaller, tiled geopackage
    # files (at z-level 13) in the the staged-vectors directory.
    stager = pdgstaging.TileStager(my_config)
    stager.stage_all()

    # The tiler will create GeoTiffs and web tiles from the staged, tiled vectors.
    # Use the same config.
    tiler = pdgraster.RasterTiler(my_config)

    # Create geotiffs for z-level 13 through to 6 starting with the z-level 13
    # geopackage files in the staged-vector directory. Once complete, make .png
    # tiles for the web from all of the geotiffs just created. For the iwp_count
    # statistic, automatically calculate the max for each z-level from the geotiffs
    # (because the max is set to None in the config's `val_range` for the stat).
    tiler.rasterize_all()

    # Check if any files were not successfully created.
    errors_df = tiler.get_errors()
    assert errors_df.empty

    # See the tiles that were created.
    events = tiler.get_events()
    assert len(events) > 0
