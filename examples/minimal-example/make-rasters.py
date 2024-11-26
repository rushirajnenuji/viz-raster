import pdgraster

minimal_config = {"tms_id": "WorldCRS84Quad", "z_range": (0, 13)}

tiler = pdgraster.RasterTiler(minimal_config)
tiler.rasterize_all()
