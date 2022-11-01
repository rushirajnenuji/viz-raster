import warnings
import os
import uuid

import numpy as np
import geopandas as gpd
import pandas as pd
from shapely.geometry import box

import rasterio
from rasterio.io import MemoryFile
from rasterio.merge import merge
from rasterio.warp import reproject, Resampling


class Raster():
    """
        Raster is effectively a wrapper around rasterio that simplifies the
        raster operations required for the viz-raster processing step. A Raster
        class should not be instantiated directly, but rather through the
        Raster.from_vector, Raster.from_rasters, or Raster.from_file methods.
        Once created, the attributes below can be accessed to get information
        about the raster. The new Raster can then be saved to a file using the
        write method.

        Attributes
        ----------
        profile : dict
            The rasterio profile for the raster.
        count : int
            The number of bands in the raster. This is equal to the number of
            descriptions in the raster.
        dtype : numpy.dtype
            The data type of the raster.
        driver : str
            The rasterio driver for the raster.
        crs : rasterio.crs.CRS
            The coordinate reference system of the raster.
        shape : tuple
            The width and height of the raster.
        descriptions : list
            A list of the raster band descriptions.
        bounds : dict
            A dictionary of the raster bounds, with keys 'left', 'right',
            'bottom', and 'top'.
        data : numpy.ndarray
            The raster data.
        summary : dict
            A dictionary of summary statistics for each band, including
            'bounds', 'min', 'max', 'mean', 'median', 'std', 'var', and 'sum'.
        path : str
            The path to the raster file, if it was opened from or saved to a
            file.
    """

    def __init__(self):
        """
            Initialize a Raster object.
        """

        # Set random names for properties that will be created temporarily
        # during rasterization. Random so that they do not conflict with any
        # existing properties.
        self.__props = {}
        for k in ['count', 'area', 'area_prop', 'row', 'col']:
            self.__props[k] = uuid.uuid4().hex

        # Map the (more descriptive) key words that can be used in the
        # statistics configuration to the (more compact) __props keys
        self.__prop_keywords = {
            'centroids_per_pixel': 'count',
            'area_within_pixel': 'area',
            'area_per_pixel_area': 'area_prop',
        }

    @classmethod
    def from_vector(
        cls,
        vector=None,
        centroid_properties=None,
        bounds=None,
        shape=(256, 256),
        stats=[
            {
                'name': 'polygon_count',
                'weight_by': 'count',
                'property': 'centroids_per_pixel',
                'aggregation_method': 'sum'
            },
            {
                'name': 'coverage',
                'weight_by': 'area',
                'property': 'area_per_pixel_area',
                'aggregation_method': 'sum'
            }
        ]

    ):
        """
            Create a Raster class from Polygons in a vector file.

            For a given vector file with Polygons as the geometry, calculate
            zonal statistics for cells in a grid of specified dimensions, and
            use these values to create pixels in a Raster.

            Note that statistics are calculated in the CRS of the vector file;
            measurements of area and centroid location may be slightly
            incorrect if the CRS is geographic and not projected, and no
            warning is given. Inaccuracies increase with increasing Polygon
            size.

            Parameters
            ----------
            vector : str or GeoDataFrame
                Required. The path to the vector file to be converted into a
                raster, or a GeoDataFrame object containing the polygons to be
                rasterized.
            centroid_properties : tuple of str
                Optional. If centroids have been pre-calculated for these
                vectors, then the name the two properties in the vector data
                that contain the x-coordinates and y-coordinates, respectively,
                of the centroids for each Polygon. If set to None, then the
                centroids are calculated from the geometry. Centroid
                coordinates are assumed be in the same CRS as the Polygon
                geometry of the vector file.
            bounds : dict
                A dictionary with keys 'left', 'right', 'bottom', and 'top'
                that specify the bounding box of the raster. If set to None,
                then the total bounds of the GeoDataFrame are used. The
                bounding box may be smaller or larger than the source vector
                data.
            shape : tuple
                A tuple of length 2 that specifies the dimensions of the raster
                in the form (height, width). The default is (256, 256).
            stats : list
                Specification of how to compute the values for each pixel in
                the new raster data. Each item in the list represents a
                statistic to be calculated and a band in the output raster. A
                list of dictionaries with the following keys:
                    name : str
                        The name of the statistic. Can be anything but must be
                        unique.
                    weight_by : str
                        The weighting method for the statistic. Options are
                        'count' and 'area'. 'count' indicates that the
                        statistic is calculated based on the number of polygons
                        in each cell (location is identified by the centroid of
                        the polygon). 'area' indicates that the statistic is
                        calculated based on the area of the polygons that cover
                        each cell.
                    property : str
                        The name of the property in the vector file to
                        calculate the statistic for. Besides the properties
                        that are available from the input vector data, the
                        following keywords can be used:
                            'centroids_per_pixel' : The number of polygons with
                                centroids that fall in the cell/pixel. (Only
                                available if weight_by is 'count')
                            'area_within_pixel' : The area of the
                                polygon that falls within a given cell/pixel,
                                in the units of the CRS. (Only available if
                                weight_by is 'area')
                            'area_per_pixel_area' : Same as
                                'area_within_pixel', but divided by the area of
                                the cell/pixel. (Only available if weight_by is
                                'area')
                    aggregation_method : str
                        The function to be applied to the property. The vector
                        data will first be grouped into cells, then the
                        aggregation method will be used to summarize the given
                        property in the cell. Method can be any method allowed
                        in the 'func' property of the panda's aggregate method,
                        e.g. 'sum', 'count', 'mean', etc.

            Returns
            -------
            raster : Raster
                A new Raster object
        """

        r = cls()

        r.centroid_properties = centroid_properties
        r.bounds = bounds
        r.shape = shape
        r.stats = stats

        r.__set_and_check_gdf(vector)
        r.__set_grid()
        r.__calculate_stats()
        raster = r.__create_raster_from_stats_df()

        # Reset the properties saved to this class during the above processing
        # steps
        # r.centroid_properties = None
        # r.bounds = None
        # r.shape = None
        # r.stats = None
        # r.gdf = None
        # r.rows = None
        # r.cols = None
        # r.cell_area = None
        # r.stats_df = None

        r.update_properties(raster)

        return r

    @classmethod
    def from_rasters(
        cls,
        rasters,
        resampling_methods=('nearest'),
        shape=None,
        bounds=None,
    ):
        """
            Create a composite raster from a list of raster input paths. The
            new raster will be reshaped to the dimensions and bounding box set
            by the `shape` and `bounds` parameters, respectively. The raster
            will be resampled using the methods specified in the
            resampling_methods parameter (one method for each band).

            All of the input rasters must have the same number of bands and the
            same CRS. If a raster path does not exist, a warning is given and
            the raster is skipped. If none of the provided rasters exist, a
            ValueError is raised.

        Parameters
        ----------
        rasters : list of str
            List paths to raster files. Rasters must all be in the same
            coordinate reference system and have the same number/type of bands.
        resampling_methods : list of str
            List of resampling methods to be applied to the rasters, one for
            each band in the rasters. If there are fewer methods than bands,
            the last method is used for all remaining bands. See rasterio's
            Resampling Methods for list of the available methods.
        shape : tuple
            A tuple of length 2 that specifies the dimensions of the output
            raster in the form (height, width). The default is (256, 256).
        bounds : dict
            A dictionary with keys 'left', 'right', 'bottom', and 'top' that
            specify the bounding box of the output raster (it may be smaller or
            greater than the bounding box of the merged datasets).

        Returns
        -------
        raster : Raster
            The rasterio DatasetReader object for the output raster. Note that
            when finished with the raster, it should be closed using
            `raster.close()`.
        """

        r = cls()

        r.shape = shape
        r.bounds = bounds

        rasters = r.__get_and_check_rasters(rasters)
        raster = r.__merge_and_resample(rasters, resampling_methods)

        r.update_properties(raster)

        return r

    @classmethod
    def from_file(cls, filename):
        """
            Create a Raster from a saved raster file.

            Parameters
            ----------
            filename : str
                The path to the raster file.

            Returns
            -------
            raster : Raster
                The rasterio DatasetReader object for the raster.
        """

        r = cls()
        raster = rasterio.open(filename)
        r.update_properties(raster)
        return r

    def update_properties(self, raster, close=True):
        """
            Take attributes of a rasterio DatasetReader object and update the
            properties of this Raster object, then close the DatasetReader.

            Parameters
            ----------
            raster : rasterio DatasetReader
                The rasterio DatasetReader object to be used to update the
                properties of this Raster object.
            close : bool
                If True, the rasterio DatasetReader object will be closed after
                the properties are updated. Default is True.
        """

        self.profile = raster.profile
        self.count = self.profile['count']
        self.dtype = self.profile['dtype']
        self.driver = self.profile['driver']
        self.crs = self.profile['crs']

        self.shape = raster.shape
        self.descriptions = raster.descriptions

        self.bounds = {}
        self.bounds['left'] = raster.bounds.left
        self.bounds['right'] = raster.bounds.right
        self.bounds['bottom'] = raster.bounds.bottom
        self.bounds['top'] = raster.bounds.top

        self.data = raster.read()

        self.summary = {
            'stat': self.descriptions,
            'bounds': [[
                self.bounds['left'],
                self.bounds['right'],
                self.bounds['bottom'],
                self.bounds['top']
            ]] * self.count,
            'min': [None] * self.count,
            'max': [None] * self.count,
            'mean': [None] * self.count,
            'median': [None] * self.count,
            'std': [None] * self.count,
            'var': [None] * self.count,
            'sum': [None] * self.count}
        for i in range(self.count):
            values = self.data[i]
            self.summary['min'][i] = values.min()
            self.summary['max'][i] = values.max()
            self.summary['mean'][i] = values.mean()
            self.summary['median'][i] = np.median(values)
            self.summary['std'][i] = values.std()
            self.summary['var'][i] = values.var()
            self.summary['sum'][i] = values.sum()

        if raster.files:
            self.path = raster.files[0]
        else:
            self.path = None

        if close:
            raster.close()

    def write(self, output_path=None):
        """
            Write a raster to a geotiff file.

        Parameters
        ----------
        output_path : str
            The path to the output file. If the file already exists, it will be
            overwritten. If the directory does not exist, it will be created.
        """

        dirname = os.path.dirname(output_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)

        prof = self.profile

        with rasterio.open(output_path, 'w', **prof) as dst:
            dst.write(self.data)
            dst.descriptions = self.descriptions

        self.path = output_path

    def grid_as_gdf(self):
        """
            Create a GeoDataFrame representing the grid defines the raster. The
            GDF comprises the grid cell geometry and the row and column
            indices. This is useful for testing and visualizing the grid.

            Returns
            -------
            gdf : geopandas.GeoDataFrame
                A GeoDataFrame with the grid cell geometry and row and column
                indices.
        """

        self.__set_grid()

        column_values = {
            'geometry': [], 'row_index': [], 'col_index': [],
        }

        for i in range(len(self.rows) - 1):
            for j in range(len(self.cols) - 1):
                column_values['geometry'].append(box(
                    minx=self.cols[j], maxx=self.cols[j + 1],
                    miny=self.rows[i], maxy=self.rows[i + 1]
                ))
                column_values['row_index'].append(i)
                column_values['col_index'].append(j)

        grid = gpd.GeoDataFrame(column_values, crs=self.gdf.crs)

        self.rows = None
        self.cols = None
        self.cell_area = None

        return grid

    def __set_and_check_gdf(self, vector=None):
        """
            Open the vector file as a GeoPandas GeoDataFrame, and set it on the
            class as a property called 'gdf' for other methods to use. Check
            that the vector file contains only polygons, that the centroid
            properties exist, and that there is a CRS.

            Parameters
            ----------
            vector : str or GeoDataFrame
                Required. The path to the vector file to be converted into a
                raster, or a GeoDataFrame object containing the polygons to be
                rasterized.
        """

        # Give error if no GDF is provided.
        if not (
            isinstance(vector, str) or
            isinstance(vector, gpd.GeoDataFrame)
        ):
            raise ValueError(
                'An input path (string) for a vector must be provided.')

        # Read the GDF.
        if isinstance(vector, str):
            self.gdf = gpd.read_file(vector)
        elif isinstance(vector, gpd.GeoDataFrame):
            self.gdf = vector
        else:
            raise ValueError(
                'The input vector must be a string or a GeoDataFrame object.')

        gdf = self.gdf

        # Check that the GDF has a CRS
        if gdf.crs is None:
            raise ValueError('The input vector file must have a CRS.')

        # Check that the geometry column is a Polygon.
        if any(gdf.geometry.geom_type != 'Polygon'):
            raise ValueError(
                'The vector file must comprise only Polygon geometries.')

        # Check that the centroid columns exist in the data frame, otherwise
        # set these column names to None (and compute them later)
        if self.centroid_properties is not None:
            x_prop = self.centroid_properties[0]
            y_prop = self.centroid_properties[1]
            if x_prop not in gdf.columns or y_prop not in gdf.columns:
                # Give a warning if the centroid column is not in the data
                # frame.
                warnings.warn(
                    'At least one of the centroid properties do not exist in '
                    'the vector data. The centroids will be computed from the '
                    'geometry.'
                )
                self.centroid_properties = None

    def __set_grid(self):
        """
            Calculates the array row and column fences, as well as the
            cell/pixel area, and sets these values on the class. Used to
            calculate the statistics for the raster. The row and column fences
            are based on the bounding box and the given height and width of the
            output raster. If a bounding box is not set, then set the bounding
            box to the bounding box of the vector file.
        """

        # Calculate the bounding box of the grid. If bounding box is not
        # provided, use the total bounds of the GDF.
        if self.bounds is None:
            bb = {}
            gdf_bb = self.gdf.total_bounds
            bb['left'], bb['bottom'], bb['right'], bb['top'] = gdf_bb
            self.bounds = bb

        # Calculate the number of rows and columns.
        self.rows = np.linspace(
            self.bounds['bottom'], self.bounds['top'], self.shape[0] + 1
        )
        # Reverse the rows so that the first row is the bottom row.
        self.rows = self.rows[::-1]
        self.cols = np.linspace(
            self.bounds['left'], self.bounds['right'], self.shape[1] + 1
        )

        # Calculate the area of a single grid cell. (Assume they are approx all
        # equal area)
        self.cell_area = abs((self.rows[0] - self.rows[1]) *
                             (self.cols[1] - self.cols[0]))

    def __calculate_stats(self):
        """
            Calculate the statistics for each cell/pixel. Set the resulting
            data frame as a property called 'stats_df' on the class. The
            stats_df is a data frame with row_index, col_index columns plus
            a column for each statistic in the 'stats' list.
        """

        # Will hold the statistics for each cell/pixel.
        stats_df = None

        # Property names for row and col index columns.
        ri = self.__props['row']
        ci = self.__props['col']

        # Create a dictionary of the aggregations to be performed (format for
        # for the pandas agg method).
        agg_dict_count = {}
        agg_dict_area = {}

        for stat in self.stats:
            prop = stat['property']
            if prop in self.__prop_keywords:
                prop = self.__props[self.__prop_keywords[prop]]
            method = stat['aggregation_method']
            agg_tuple = (prop, method)
            agg_name = stat['name']
            if stat['weight_by'] == 'count':
                agg_dict_count[agg_name] = agg_tuple
            elif stat['weight_by'] == 'area':
                agg_dict_area[agg_name] = agg_tuple

        if(len(agg_dict_count) > 0):
            # Create a dataframe with the row and column indices are assigned
            # to the polygons based on the location of their centroid.
            centroid_gdf = self.__grid_by_centroid()
            count_stats_df = centroid_gdf.groupby(
                [ri, ci], as_index=False).agg(
                **agg_dict_count).reset_index(drop=True)
            stats_df = count_stats_df

        if(len(agg_dict_area) > 0):
            # Create a second dataframe where all polygons are sliced along the
            # grid lines, and sliced polygons are assigned to the grid cell
            # they fall within.
            area_gdf = self.__grid_by_area()

            area_stats_df = area_gdf.groupby([ri, ci], as_index=False).agg(
                **agg_dict_area).reset_index(drop=True)

            if(stats_df is None):
                stats_df = area_stats_df
            else:
                stats_df = stats_df.merge(
                    area_stats_df, on=[
                        ri, ci], how='outer').reset_index(
                    drop=True)
                # Replace NA values that resulted from the merge with 0 (i.e.
                # where there is polygon coverage but no centroids, the
                # centroid count should be 0)
                stats_df.fillna(0, inplace=True)

        self.stats_df = stats_df

    def __grid_by_centroid(self):
        """
            Assign each polygon to a grid cell based on the centroid location.
            Calculate the centroid of each polygon first, if coordinates are
            not provided.

            Returns
            -------
            centroid_gdf : GeoPandas GeoDataFrame
                A copy of the input vector GeoDataFrame with three new columns:
                row_index and col_index, which indicates the cell/pixel the
                polygon's centroid is located within, and polygon_count, which
                always equals 1 and can be used to sum the number of polygons
                within a cell/pixel during the aggregation step.
        """

        # Don't modify the original GDF
        c_gdf = self.gdf.copy()
        # Add a generic column that we can use to sum the number of polygons
        # (otherwise, must use count)
        c_gdf[self.__props['count']] = 1
        x_prop = None
        y_prop = None
        cent_props = self.centroid_properties

        # Names for the row and column index columns.
        ri = self.__props['row']
        ci = self.__props['col']

        if isinstance(cent_props, tuple) or isinstance(cent_props, list):
            x_prop = self.centroid_properties[0]
            y_prop = self.centroid_properties[1]

        if isinstance(x_prop, str) and isinstance(y_prop, str):
            centroids_x = c_gdf[x_prop]
            centroids_y = c_gdf[y_prop]
        else:
            # Catch the UserWarning that is raised if centroid is calculated
            # using the a non-projected coordinate system.
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                centroids = c_gdf.centroid
            centroids_x = centroids.x
            centroids_y = centroids.y

        # Identify which grid cell each point belongs within.
        c_gdf[ci] = np.searchsorted(self.cols, centroids_x) - 1
        # Reverse arrays because rows are in descending order by
        # np.searchsorted requires ascending order.
        c_gdf[ri] = np.searchsorted(
            -self.rows, -centroids_y) - 1

        # Drop any rows that fall outside the grid.
        c_gdf = c_gdf[(c_gdf[ri] >= 0) &
                      (c_gdf[ri] < self.shape[0]) &
                      (c_gdf[ci] >= 0) &
                      (c_gdf[ci] < self.shape[1])]

        c_gdf.reset_index(inplace=True, drop=True)

        return c_gdf

    def __grid_by_area(self):
        """
            Slice each polygon in the input vector GDF along the grid lines,
            and assign the sliced polygons to the grid cell they fall within.
            Add a column for the area of each of the new polygons.

            Returns
            -------
            area_gdf : geopandas.GeoDataFrame
                A GeoDataFrame with the same columns as the original GDF, plus
                a column for the area of each polygon. The GDF will have the
                same number of rows or more than the original, depending on if
                the polygons are split.
        """

        # Row and column index columns names
        ri = self.__props['row']
        ci = self.__props['col']
        # Rasterization properties
        ar = self.__props['area_prop']
        ar_p = self.__props['area_prop']

        minx = self.cols[0]
        maxx = self.cols[-1]
        miny = self.rows[-1]
        maxy = self.rows[0]

        crs = self.gdf.crs

        row_geoms = []
        col_geoms = []

        for i in range(len(self.rows) - 1):
            row_geoms.append(box(
                minx=minx, maxx=maxx,
                miny=self.rows[i], maxy=self.rows[i + 1]
            ))

        for i in range(len(self.cols) - 1):
            col_geoms.append(box(
                minx=self.cols[i], maxx=self.cols[i + 1],
                miny=miny, maxy=maxy
            ))

        gdf_grid_rows = gpd.GeoDataFrame(geometry=row_geoms, crs=crs)
        gdf_grid_rows.reset_index(inplace=True)
        gdf_grid_rows.rename(columns={'index': ri}, inplace=True)

        gdf_grid_cols = gpd.GeoDataFrame(geometry=col_geoms, crs=crs)
        gdf_grid_cols.reset_index(inplace=True)
        gdf_grid_cols.rename(columns={'index': ci}, inplace=True)

        # Intersecting by rows, then by columns is at least 3x faster than
        # intersecting by grid cells and gives the same result.
        area_gdf_rows = self.gdf.overlay(gdf_grid_rows, how='intersection')
        area_gdf = area_gdf_rows.overlay(gdf_grid_cols, how='intersection')

        # Catch the UserWarning that is raised area is calculated using the a
        # non-projected coordinate system.
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            area_gdf[ar] = area_gdf.area

        area_gdf[ar_p] = area_gdf[ar] / self.cell_area

        area_gdf.reset_index(inplace=True, drop=True)

        return area_gdf

    def __create_raster_from_stats_df(self):
        """
            Create a raster in memory from the stats_df.

            Returns
            -------
            dataset: rasterio.io.DatasetReader
                A rasterio dataset reader object that can be used to read the
                raster data, or written to a file, etc.
        """

        stats_df = self.stats_df

        ri = self.__props['row']
        ci = self.__props['col']

        # Get the minimum int dtype for all columns TODO: Set dtype for each
        # stat. Or allow user to set dtype for each stat.
        all_columns = stats_df.columns
        index_columns = [ri, ci]
        values_columns = [x for x in all_columns if x not in index_columns]
        all_values = np.concatenate(
            [stats_df[col].values for col in values_columns])
        dtype = np.min_scalar_type(all_values)
        if(dtype == np.int64):  # Not supported
            dtype = np.int32

        # Convert the statistics data frame to a dict of arrays. ensure the
        # arrays are in the same order as that stats config
        stats_dict = {}
        for column_name in values_columns:
            stats_dict[column_name] = self.__as_array(stats_df, column_name)

        stats_names_ordered = [x['name'] for x in self.stats]
        # count is the number of arrays in the stats dict == the number of
        # bands
        count = len(stats_dict)
        # Use each array in the statistics dict to create a band in a new
        # raster. Keep the raster in memory to return.
        crs = self.gdf.crs.to_wkt()
        transform = rasterio.transform.from_bounds(
            self.bounds['left'],
            self.bounds['bottom'],
            self.bounds['right'],
            self.bounds['top'],
            width=self.shape[1],
            height=self.shape[0])

        memfile = MemoryFile()
        with memfile.open(
            driver='GTiff',
            width=self.shape[1],
            height=self.shape[0],
            count=count,
            dtype=dtype,
            crs=crs,
            transform=transform
        ) as dataset:
            # Keep band number in the same order as the stats config
            for key in stats_dict.keys():
                band_index = stats_names_ordered.index(key) + 1
                data_array = stats_dict[key]
                dataset.write(data_array, band_index)
                dataset.set_band_description(band_index, key)
        return memfile.open()

    def __as_array(
        self,
        df=None,
        values_column=None
    ):
        """
            Convert a dataframe into a 2D array that is the size of the grid
            specified in this class. Grid cells without any data will be filled
            with 0.

            Parameters
            ----------
            df : pd.DataFrame
                Dataframe with at least 3 columns: a column with the row
                indices, a column with the column indices, and a column with
                the values to return as an array.
            values_column : str
                Name of the column with the values to return as an array. If
                None, the values_column is assumed to be the last column in the
                dataframe.

            Returns
            -------
            numpy.ndarray
                Array of width grid_width and height grid_height with the
                values from df.
        """

        ri = self.__props['row']
        ci = self.__props['col']

        n_rows = len(self.rows) - 1
        n_cols = len(self.cols) - 1

        if values_column is None:
            values_column = df.columns[-1]

        all_indices = pd.MultiIndex.from_product(
            [range(n_rows), range(n_cols)],
            names=[ri, ci],
        )

        a = (
            df.set_index([ri, ci])[values_column]
            .reindex(all_indices, fill_value=0)
            .sort_index()
            .values.reshape((n_rows, n_cols))
        )

        return a

    def __get_and_check_rasters(self, rasters):
        """
            Take paths to rasters and return a list of
            rasterio.io.DatasetReader objects. Check that the rasters have the
            same number of bands, and the same CRS (required), and that the
            band descriptions at all the same (give warning if not).

            Parameters
            ----------
            rasters : list of str
                List of rasters filenames/paths to check.

            Returns
            -------
            rasters : list of rasterio.io.DatasetReader objects
                List of rasters
        """

        rasters = [r for r in rasters if r is not None]

        # Check if all elements in the rasters array are strings
        if(all(isinstance(x, str) for x in rasters)):
            paths = rasters.copy()
            rasters = []
            for path in paths:
                try:
                    rasters.append(rasterio.open(path))
                except FileNotFoundError:
                    # give warnings
                    warnings.warn('Raster file not found: {}'.format(path))
                    pass
        else:
            raise ValueError('Rasters must be a list of paths')

        # Check that the array of rasters is not empty
        if len(rasters) == 0:
            raise ValueError('No rasters provided')

        # Can't proceed if any element in the rasters array are not
        # rasterio.io.DatasetReader objects
        if(not all(isinstance(x, rasterio.io.DatasetReader) for x in rasters)):
            raise TypeError(
                'There was a problem opening at least one of the rasters.')

        # Reference raster
        ref = rasters[0]

        # Check if all elements in the rasters array have the same CRS
        if(not all(x.crs == ref.crs for x in rasters)):
            raise ValueError(
                'All rasters must have the same CRS.')

        # Check if all elements in the rasters array have the same band count
        if(not all(x.count == ref.count for x in rasters)):
            raise ValueError(
                'All rasters must have the same band count.')

        # Check if all elements in the rasters array have the same band names.
        # Warn that band names from the first will be used
        if(not all(x.descriptions == ref.descriptions for x in rasters)):
            warnings.warn(
                'Not all rasters have the same band names. Using band names ' +
                ' from the first raster.'
            )

        return rasters

    def __merge_and_resample(self, rasters, resampling_methods):
        """
            Merge the rasters into a single raster, resample the merged raster
            to the specified shape, and return the resampled raster.

            Parameters
            ----------
            rasters : list of rasterio.io.DatasetReader objects
                List of rasters to merge and resample.
            resampling_methods : list of str
                List of resampling methods to be applied to the rasters, one
                for each band in the rasters. If there are fewer methods than
                bands, the last method is used for all remaining bands. See
                Rasterio's Resampling Methods for list of the available
                methods.

            Returns
            -------
            raster : rasterio.io.DatasetReader
                Rasterio Dataset Reader with the rasters merged and resampled
                to the specified shape.
        """

        ref = rasters[0]

        descriptions = ref.descriptions
        crs = ref.crs
        count = ref.count
        dtype = ref.read().dtype
        if self.shape is None:
            self.shape = ref.shape

        output_transform = rasterio.transform.from_bounds(
            self.bounds['left'], self.bounds['bottom'],
            self.bounds['right'], self.bounds['top'],
            height=self.shape[0], width=self.shape[1]
        )

        # The 'source' data is the merged array of all the rasters
        merged_data, merge_transform = merge(rasters)
        # Create an array to hold the resampled data in the desired shape.
        # TODO: The NA values might not always be zero.
        new_array = np.zeros((count, self.shape[0], self.shape[1]), dtype)

        # Resampling each band separately, since each band may have a different
        # resampling method
        for i in range(count):
            try:
                method_i = resampling_methods[i]
            except IndexError:
                method_i = resampling_methods[-1]
            resampling_method = Resampling[method_i]

            reproject(
                source=merged_data[i],
                destination=new_array[i],
                src_transform=merge_transform,
                dst_transform=output_transform,
                src_crs=crs,
                dst_crs=crs,
                resampling=resampling_method)

        # Create the output raster as an in-memory file
        memfile = MemoryFile()
        with memfile.open(
            driver='Gtiff',
            height=self.shape[0], width=self.shape[1],
            count=count,
            dtype=dtype,
            crs=crs,
            transform=output_transform
        ) as dataset:
            dataset.write(new_array)
            dataset.descriptions = descriptions
        return memfile.open()
