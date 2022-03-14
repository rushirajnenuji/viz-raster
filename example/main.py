
import logging
import logging.config

from RasterTiler import RasterTiler

log_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file_handler': {
            'level': 'INFO',
            'filename': 'example/viz-raster-example.log',
            'class': 'logging.FileHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        '': {
            'handlers': ['file_handler'],
            'level': 'INFO',
            'propagate': True
        }
    }
}

logging.config.dictConfig(log_dict)

my_config = {
    'tms_id': 'WorldCRS84Quad',
    'tile_path_structure': ['style', 'tms', 'z', 'x', 'y'],
    'geotiff_dir': 'example/geotiffs',
    'web_tiles_dir': 'example/web-tiles',
    'web_tiles_type': '.png',
    'z_range': (0, 13),
    'tile_size': (256, 256),
    'statistics': [
        {
            'name': 'iwp_count',
            'weight_by': 'count',
            'property': 'polygon_count',
            'aggregation_method': 'sum',
            'resampling_method': 'sum',
            'val_range': [0, None],
            'palette': [
                'rgb(102 51 153 / 0.1)', '#d93fce', 'lch(85% 100 85)'
            ]
        },
        {
            'name': 'iwp_coverage',
            'weight_by': 'area',
            'property': 'grid_area_prop',
            'aggregation_method': 'sum',
            'resampling_method': 'average',
            'val_range': [0, 1],
            'palette': ['rgb(102 51 153 / 0.1)', 'lch(85% 100 85)']
        }
    ]
}

tiler = RasterTiler(my_config)

# Create geotiffs for z-level 13 through to 0 from the z-level 13
# geopackage files in the staged-vector directory.
tiler.rasterize_vectors(
    paths={
        'path': 'example/staged-vectors',
        'ext': '.gpkg',
    },
    centroid_properties=('centroid_x', 'centroid_y'),
    make_parents=True
)

# Now make web tiles from all of the geotiffs just created. For the iwp_count
# statistic, automatically calculate the max for each z-level from the geotiffs
# (because the max is set to None in the config's `val_range` for the stat).
tiler.webtiles_from_all_geotiffs()

# Check if any files were not successfully created.
tiler.get_errors()

# See the tiles that were created.
events = tiler.get_events(as_df=True)

# Compare the average amount of time to create geotiffs from vectors, to create
# geotiffs from child geotiffs, and to create web tiles from geotiffs.
events.groupby('type').agg({'total_time': 'mean'})

# See the total number of IWP polygons from Tile(x=2611, y=629, z=13)
tile_of_interest = tiler.tiles.tile(x=2611, y=629, z=13)
info_about_tile = events[events['tile'] == tile_of_interest]
info_about_tile['raster_summary'][0]['iwp_count']['sum']
