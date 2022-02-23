from datetime import datetime
import logging
import os
import re

from coloraide import Color
import geopandas as gpd
import numpy as np
import morecantile
import pandas as pd
from PIL import Image

from common import get_tile_path, polygon_from_bb

logger = logging.getLogger(__name__)


class RasterTiler():
    """
        Creates tiled raster images representing summary statistics for the
        staged input vector data.
    """

    def __init__(
        self,
        input_dir=None,
        input_ext='.shp',
        output_dir=None,
        output_ext='.png',
        tms_identifier='WorldCRS84Quad',  # <- Must match staged files
        max_zoom=13,  # <- This must be the level of the staged files
        min_zoom=0,
        tile_size=256,
        tile_path_structure=['z', 'x', 'y'],  # <- Must match staged files
        colors=['rgb(102 51 153 / 0.1)', 'lch(85% 100 85)']
    ):
        """
            Initialise the tiler.

            Parameters
            ----------
            input_dir : str
                The path to the directory containing the staged input vector
                files. These are the files that have already been run through
                the PDG viz-staging process.
            input_ext : str
                The extension of the input files, including the dot. For
                example, '.shp'.
            output_dir : str
                The directory to save the output to.
            output_ext : str
                The extension of the image tiles, including the dot. For
                example, '.png'.
            tms_identifier : str
                The identifier for the TMS system, which must match the
                identifier used in the PDG viz-staging process. For example,
                'WorldCRS84Quad'.
            max_zoom : int
                The highest-level detail of the tiles to create. This must be
                the same as the zoom level of the staged files.
            min_zoom : int
                The minimum zoom level to process. This is the lowest-level
                detail of the tiles to create. Must be an integer <= max_zoom
                and >= 0.
            tile_size : int
                The height and width of the resulting tile images, in pixels.
            tile_path_structure : list
                A list of strings that represent the directory structure of
                last segment of the path that uses the x (TileCol), y
                (TileRow), and z (TileMatrix) indices of the tile. By default,
                the path will be in the format of
                {TileMatrix}/{TileCol}/{TileRow}.ext, configured as ['z', 'x',
                'y'].
            colors : list
                A list of strings that represent colors in a linear gradient
                that will be used to color the tiles based on the calculated
                summary statistics. The strings can be in any formated
                supported by the coloraide library. See
                https://facelessuser.github.io/coloraide/color/ for more
                information.
        """
        self.input_dir = input_dir
        self.input_ext = input_ext
        self.output_dir = output_dir
        self.output_ext = output_ext
        self.tms_identifier = tms_identifier
        self.max_zoom = max_zoom
        self.min_zoom = min_zoom
        self.width = tile_size
        self.height = tile_size
        self.tile_path_structure = tile_path_structure

        self.set_palette(colors)

        # Create the TileMatrixSet for the output tiles
        self.tms = morecantile.tms.get(tms_identifier)

        # Set a variable that will hold the list of next level tiles to create
        self.parent_tiles_to_make = []
        self.current_zoom = self.max_zoom

    def set_palette(self, colors):
        """
            Create the color palette for the image and set it on this object.
            The palette is a flattened list rgb values between 0 and 255, used
            for the PIL putpalette function.
        """
        # This creates a function that takes a value between 0 and 1 and
        # returns a Color object. Required for the get_rgba function.
        self.gradient = Color(colors[0]).interpolate(colors[1:], space='lch')

        # Create a palette list for the PIL putpalette function. Because we are
        # creating RGBA images, the list should be 1024 elements long.
        pal_size = 256
        pal_values = [x / pal_size for x in range(pal_size)]
        pal_rgba = [self.get_rgba(i) for i in pal_values]
        pal_flat = [item for sublist in pal_rgba for item in sublist]
        self.palette = pal_flat

    def get_rgba(self, val):
        """
            Returns a colour based on the tiler's colour palette, given a value
            between 0 and 1. The colour is represented as a list of four values
            giving the intensity of red, green, blue, and alpha respectively,
            each intensity between 0 and 255.

            Parameters
            ----------
            val : float
                A value between 0 and 1.
        """
        col = self.gradient(val)
        # to_string is the best method to get values into 255
        col_str = col.convert('srgb').to_string(precision=3, alpha=True)
        # parse the string for rgba values
        rgba = list(float(i) for i in re.findall(r'[\d\.]+', col_str))
        # Alpha should be 255 as well
        rgba[3] = rgba[3] * 255
        # Round rgba to integers
        rgba = [int(i) for i in rgba]
        return rgba

    def make_tiles(self):
        """
            Create raster tiles from all of the staged vector files in the
            input directory.
        """

        # Create the output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        # Keep a list of the tiles created
        tile_created = []

        # This function is called once for each level of zoom. Check whether we
        # are making the highest level zoom tiles directly from the input
        # files, or whether we are making composite tiles from previously saved
        # pixel values
        if self.current_zoom == self.max_zoom:
            # Make the tiles for the highest level of zoom directly from the
            # (staged) input files.
            for path in self.get_input_paths():
                # Read in the data
                gdf = self.get_data(path)
                # Determine which tile we are working with
                tile = self.parse_tile_string(gdf.tile[0])
                pixel_values = self.get_pixel_values_from_gdf(gdf, tile)
                self.save_tile(pixel_values, tile)
                tile_created.append(tile)
        else:
            # Make tiles from the previously processed zoom level
            for tile in self.parent_tiles_to_make:
                pixel_values = self.get_pixel_values_from_children(tile)
                if pixel_values is not None:
                    self.save_tile(pixel_values, tile)
                    tile_created.append(tile)

        # Clear the list of parent tiles to make
        self.parent_tiles_to_make = []

        # Set the parent tiles to make from the tiles just created
        next_zoom = self.current_zoom - 1
        if (next_zoom >= self.min_zoom) and (next_zoom >= 0):
            for tile in tile_created:
                self.parent_tiles_to_make += self.get_parent_tiles(tile)
            # Make sure all the parent tiles we listed are unique
            self.parent_tiles_to_make = list(
                set(self.parent_tiles_to_make)
            )
            self.current_zoom = next_zoom
            self.make_tiles()

    def get_input_paths(self):
        """
            Get the paths for all of the input data files
        """
        # Log the start of the process, the input directory, and time how long
        # it takes to get the paths
        logger.info(
            f'Getting vector file input paths from directory: {self.input_dir}'
        )
        start_time = datetime.now()

        input_paths = []
        for root, dirs, files in os.walk(self.input_dir):
            for file in files:
                if file.endswith(self.input_ext):
                    path = os.path.join(root, file)
                    input_paths.append(path)

        # Log the end time, the total time, and the number of paths found
        logger.info(
            f'Found {len(input_paths)} paths in {datetime.now() - start_time}'
        )

        self.input_paths = input_paths[0]
        return input_paths

    def get_tile_path(self, tile=None, type='input'):
        """
            Returns the path to the tile.

            Parameters
            ----------
            tile : morecantile.Tile
                The tile to get the path for.
            type : str
                The type of path to get. Can be 'input', 'output', or
                'pixel_values'.
        """
        if type == 'input':
            ext = self.input_ext
            prefix = self.input_dir
        elif type == 'output':
            ext = self.output_ext
            prefix = self.output_dir
        elif type == 'pixel_values':
            ext = '.csv'
            prefix = os.path.join(self.output_dir, 'pixel_values')
        return get_tile_path(
            prefix=prefix,
            tms=self.tms,
            tile=tile,
            path_structure=self.tile_path_structure,
            ext=ext
        )

    def get_data(self, path=None):
        """
            Reads in a GeoDataFrame from a file.

            Parameters
            ----------
            path : str
                The path to the file.

            Returns
            -------
            data : GeoDataFrame
                The data read in from the file.
        """
        if path is None:
            return
        start_time = datetime.now()
        gdf = gpd.read_file(path)
        logger.info(f'Read data in {datetime.now() - start_time}')
        return gdf

    def parse_tile_string(self, tile_str):
        """
            Parse the morecantile tile string to get the x, y, and z values.
            Takes a string in the format Tile(x=6, y=10, z=4) and returns the
            x, y, and z values as a list.

            Parameters
            ----------
            tile_str : str
                A string in the format Tile(x=6, y=10, z=4) as used by the
                morecantile library.

            Returns
            -------
            list
                A list of the x, y, and z values.
        """
        regex = re.compile(r'(?<=x=)\d+|(?<=y=)\d+|(?<=z=)\d+')
        x, y, z = [int(i) for i in regex.findall(tile_str)]
        tile = morecantile.Tile(x, y, z)
        return tile

    def get_pixel_values_from_gdf(self, gdf, tile):
        """
            Summarize a GeoDataFrame and return pixel values that can be used
            to create a raster image. Currently the pixel values represent the
            relative area covered by polygons in each pixel. Eventually this
            the summary statistic that is calculated will be configurable.

            Parameters
            ----------
            gdf : GeoDataFrame
                The GeoDataFrame containing the pixel values.
            tile : morecantile.Tile
                The tile that the gdf represents.

            Returns
            -------
            pixel_values : numpy.ndarray
                The pixel values for the tile
        """
        # Create a grid for the tile
        grid = self.make_pixel_grid(tile)
        # Calculate the area per cell.
        # TODO: Make the summary statistic configurable
        pixel_values = self.calculate_area_per_cell(grid, gdf)
        return pixel_values

    def get_pixel_values_from_children(self, tile):
        """
            Get the pixel values for a tile based the mean of the pixel values
            from the children tiles.

            Parameters
            ----------
            tile : morecantile.Tile
                The tile to get the pixel values for.

            Returns
            -------
            pixel_values : pandas.DataFrame
                The pixel values for the tile, represented as a DataFrame with
                a column for pixel_row and pixel_col indices, as well as a
                column for the calculated pixel value.
        """

        # Identify the four sub-tiles that make up this tile
        child_tiles = self.get_child_tiles(tile)
        pixel_values = None

        for child_tile in child_tiles:

            # Get the previously pixel values (if any)
            path = self.get_tile_path(child_tile, 'pixel_values')

            if os.path.exists(path):

                sub_pixel_values = pd.read_csv(path)

                # Identify the position of this tile within the parent; add the
                # tile width and tile height to pixel column and row indices as
                # required for downsampling.
                if child_tile.x % 2 != 0:
                    sub_pixel_values['pixel_col'] += self.width
                if child_tile.y % 2 != 0:
                    sub_pixel_values['pixel_row'] += self.height

                # Add the pixel values to the composite
                if pixel_values is None:
                    pixel_values = sub_pixel_values
                else:
                    pixel_values = pd.concat(
                        (pixel_values, sub_pixel_values), axis=0
                    )

        # Downsample the pixel values using the average. Combine every two
        # pixel rows and every two pixel cols.
        pixel_values['pixel_row'] = [int(i // 2)
                                     for i in pixel_values['pixel_row']]
        pixel_values['pixel_col'] = [int(i // 2)
                                     for i in pixel_values['pixel_col']]
        # TODO: Make the summary statistic configurable. For now, just use the
        # mean. For count data, use the sum.
        pixel_values = pixel_values.groupby(
            ['pixel_row', 'pixel_col'], as_index=False
        ).agg({'frac_covered': 'mean'})

        return pixel_values

    def make_pixel_grid(self, tile):
        """
            Makes a grid that covers the area of a tile. The grid is
            represented as a GeoDataFrame where each row has a pixel column
            index, pixel row index, and a square polygon geometry that covers
            what will be a single pixel in the eventual raster image. The size
            of the grid is determined by the tile size configured on this
            tiler.

            Parameters
            ----------
            tile : morecantile.Tile
                The tile to create the pixel grid for.

            Returns
            -------
            pixel_grid : geopandas.GeoDataFrame
                The pixel grid for the tile.
        """

        width = self.width
        height = self.height

        # Bounding box of the tile
        bb = self.tms.bounds(tile)

        # np.linspace divides the tile between left and right into
        # `p_width` equal spaces. Returns the array of coordinates in cols
        # Same for rows with `p_height`.
        cols = np.linspace(bb.left, bb.right, num=width + 1)
        rows = np.linspace(bb.bottom, bb.top, num=height + 1)

        polygons = []
        pixel_rows = []
        pixel_cols = []
        for i in range(0, width):
            for j in range(0, height):
                # create a polygon
                polygon = polygon_from_bb(north=rows[j], south=rows[j + 1],
                                          east=cols[i], west=cols[i + 1])
                # add the polygon to the list of polygons
                polygons.append(polygon)
                # add the pixel coordinates to the list of pixel coordinates
                pixel_rows.append(j)
                pixel_cols.append(i)

        grid = gpd.GeoDataFrame({
            'geometry': polygons,
            'pixel_row': pixel_rows,
            'pixel_col': pixel_cols
        }).set_crs(self.tms.crs)
        return grid

    def calculate_area_per_cell(self, grid, gdf):
        """
            Calculate the area of each cell in the grid.

            Parameters
            ----------
            grid : GeoDataFrame
                The grid of pixels.
            gdf : GeoDataFrame
                The data to calculate the area of.

            Returns
            -------
            grid : GeoDataFrame
                The grid with the area of each cell added.
        """

        start_time = datetime.now()

        # keep only the 'geometry' column of gdf
        geoms = gdf[['geometry']]
        # Slice the polygons where they intersect with the grid lines, and
        # assign the pixel row and pixel column to each resulting polygon
        geoms = geoms.overlay(grid, how='intersection')
        # Get the area of the smaller polygons, as a fraction of the grid cell
        # size. By definition each grid cell is the same size.
        cell_area = grid.geometry[0].area
        geoms['frac_covered'] = geoms.area / cell_area
        # Calculate the total fraction covered per grid cell
        summary = geoms.groupby(
            ['pixel_row', 'pixel_col'], as_index=False
        ).agg({'frac_covered': 'sum'})
        summary['pixel_row'] = summary['pixel_row'].astype(np.int64)
        summary['pixel_col'] = summary['pixel_col'].astype(np.int64)

        logger.info(
            f'Calculated area per cell in {datetime.now() - start_time}'
        )

        return summary

    def array_from_df(
        self,
        df=None,
        rows_column='row',
        columns_column='column',
        values_column='values',
        n_rows=256,
        n_cols=256
    ):
        """
        Arguments:
        ----------
        df : pd.DataFrame

        rows_column : str

        columns_column : str

        n_rows : int

        n_cols: int

        example dataframe:

            row  column    values
            0    0       0 -1.390359
            1    0       1 -2.283228
            2    1       0  0.166112
            3    2       0  0.631024
            4    2       1  0.774443
            5    2       2  1.045875

        example_output:
        >>> array_from_df(df, n_rows=4, n_cols=4)
        array([[ 1.98124795, -0.43509489,  0.        ,  0.        ],
            [-0.4570742 ,  0.        ,  0.        ,  0.        ],
            [ 0.86123529,  0.79919129, -1.86013893,  0.        ],
            [ 0.        ,  0.        ,  0.        ,  0.        ]])

        """

        all_indices = pd.MultiIndex.from_product(
            [range(n_rows), range(n_cols)],
            names=[rows_column, columns_column],
        )

        a = (
            df.set_index([rows_column, columns_column])[values_column]
            .reindex(all_indices, fill_value=0)
            .sort_index()
            .values.reshape((n_rows, n_cols))
        )

        return a

    def to_unit8(self, values, min, max):
        """
            Takes an array of values and scales it to 0-255. The min and max
            values are used to first rescale the values to the range [0, 1].
            Any numbers greater than the max will be set to 255 in the output,
            and any numbers less than the min will be set to 0.

            Parameters
            ----------
            values : numpy.array
                The array of values to be scaled.

            max : float
                The maximum value in the array.

            min : float
                The minimum value in the array.

            Returns
            -------
            numpy.array
                An array of np.uint8 values.
        """
        # Normalize the array so that it's between 0 and 1
        values = (values - min) / (max - min)
        # Make sure the array is between 0 and 255
        values = np.where(values > 1, 1, values)
        values = np.where(values < 0, 0, values)
        # Convert the array to uint8
        values = values * 255
        values = values.astype(np.uint8)
        return values

    def save_tile(self, pixel_values, tile):
        """
            Save the pixel values to a CSV file, convert them to an image array
            and save the result as a raster image.

            Parameters
            ----------
            pixel_values : pandas.DataFrame
                A dataframe with a pixel_row, pixel_col, and values column.
            tile : morecantile.Tile
                The tile that the pixel values belong to.
        """
        # Save the pixel_values
        self.save_pixel_values(pixel_values, tile)
        # Create and save the image
        image = self.create_image(pixel_values)
        self.save_image(image, tile)

    def create_image(self, pixel_values):
        """
            Create a PIL image from the pixel values.

            Parameters
            ----------
            pixel_values : pandas.DataFrame
                A dataframe with a pixel_row, pixel_col, and values column.

            Returns
            -------
            PIL.Image
                A PIL image.
        """
        pixel_values['pixel_val'] = self.to_unit8(
            pixel_values['frac_covered'], 0, 1
        )

        image_data = self.array_from_df(
            df=pixel_values,
            rows_column='pixel_row',
            columns_column='pixel_col',
            values_column='pixel_val',
            n_rows=self.height,
            n_cols=self.width
        )

        img_pil = Image.fromarray(image_data, 'P')
        img_pil.putpalette(self.palette, rawmode='RGBA')

        return img_pil

    def save_image(self, image, tile):
        """
            Save an image to disk using the standard path structure for the
            given tile.

            Parameters
            ----------
            image : PIL.Image
                The image to be saved.

            tile : morecantile.Tile
                The tile that the image belongs to.
        """
        # Get the output path
        output_path = self.get_tile_path(tile, 'output')
        output_dir = os.path.dirname(output_path)

        # Create the directory if it doesn't exist
        if not (os.path.exists(output_dir)):
            os.makedirs(output_dir, exist_ok=True)

        # Save the image
        image.save(output_path)

    # TODO: For now, we're just saving the pixel values to a CSV file. It would
    # be better to save the pixel values to a geotiff or a spatial database.
    def save_pixel_values(self, pixel_values, tile):
        """
            Save the summary of pixel values to disk.

            Parameters
            ----------
            pixel_values : pd.DataFrame
                The pixel_values data to be saved. A data frame with the
                pixel_row and pixel_col integers as columns, and the
                pixel_values as values.

            tile : morecantile.Tile
                The tile that the summary data belongs to.
        """
        pixel_values_path = self.get_tile_path(tile, 'pixel_values')
        # Make the directory if it doesn't exist yet
        output_dir = os.path.dirname(pixel_values_path)
        # Create the directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        pixel_values.to_csv(pixel_values_path, index=False)

    def get_parent_tiles(self, tile):
        """
            Get the 1-zoom-level-up parent tile (or tiles) that cover a given
            tile.

            Parameters
            ----------
            tile : morecantile.Tile
                    A tile object from the morecantile library.

            Returns
            -------
            list
                    A list of morecantile.Tile objects.
        """
        # Get the bounding box of the tile
        bbox = self.tms.bounds(tile)
        north = bbox.top
        east = bbox.right
        south = bbox.bottom
        west = bbox.left
        zoom = tile.z
        tiles = []
        for t in self.tms.tiles(west, south, east, north, [zoom - 1]):
            tiles.append(t)
        return tiles

    def get_child_tiles(self, tile):
        """
            Get the 1-zoom-level-down children tiles that a given tile
            comprises. Assumes every parent tile comprises 4 children tiles.

            Parameters
            ----------
            tile : morecantile.Tile
                    A tile object from the morecantile library.

            Returns
            -------
            list
                    A list of morecantile.Tile objects.
        """

        x2 = tile.x * 2
        y2 = tile.y * 2

        child_z = tile.z + 1
        child_x = (x2, (x2 + 1))
        child_y = (y2, (y2 + 1))

        tiles = []

        for x in child_x:
            for y in child_y:
                tile = morecantile.Tile(x, y, child_z)
                tiles.append(tile)

        return tiles
