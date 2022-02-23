# import logging
# import logging.config
from raster import RasterTiler

# Set up logging (TODO: move to config file)

# log_dict = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'standard': {
#             'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
#         },
#     },
#     'handlers': {
#         'default': {
#             'level': 'INFO',
#             'formatter': 'standard',
#             'class': 'logging.StreamHandler',
#         },
#         'file_handler': {
#             'level': 'INFO',
#             'filename': 'viz-staging.log',
#             'class': 'logging.FileHandler',
#             'formatter': 'standard'
#         }
#     },
#     'loggers': {
#         '': {
#             'handlers': ['file_handler'],
#             'level': 'INFO',
#             'propagate': True
#         }
#     }
# }

# logging.config.dictConfig(log_dict)

# Example:
tiler = RasterTiler(
    input_dir='',
    output_dir='',
    tms_identifier='WGS1984Quad',  # <- Must match staged files
    max_zoom=13  # <- This must be the level of the staged files
)

tiler.make_tiles()
