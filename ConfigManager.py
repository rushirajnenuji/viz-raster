import json


class ConfigManager():
    """
        A Config Manager is a tool that simplifies working with the tiling
        configuration. The tiling configuration specifies which TileMatrixSet
        (tms) to use, how to summarize vector data into raster values, which
        z-range to create tiles for, etc.

        (TODO: fully document the config object)

        The config object is a dictionary with the following properties:
            - tms_id (str): The ID of the TMS to use. Must much a TMS
                supported by the morecantile library.
            - tile_path_structure (list of str): The path structure to use for
              the tiles.
            - geotiff_dir (str): The directory to write & read geotiff files.
            - web_tiles_dir (str): The directory to save the web tiles to.
            - web_tiles_type (str): The extension to use for the web tiles,
              e.g. '.png'.
            - z_range (tuple of int): The range of z levels to use, e.g. (0,
              13).
            - tile_size (tuple of int): The size of the tiles to use, e.g.
              (256, 256).
            - statistics (list of dict): A list of statistics and options to
              use to convert vector data into raster data. For each item in the
              list, a separate band will be created in geotiff files, and a
              separate layer will be created for web tiles. The statistics list
              is a list of dictionaries. Each dictionary contains the following
              properties:
                - name: The name of the statistic.
                - weight_by: The property to weight the statistic by.
                - property: The property to use for the statistic.
                - aggregation_method: The aggregation method to use. See the
                    Raster.py documentation for more info.
                - resampling_method: The resampling method to use when
                    combining raster data from child tiles into parent tiles.
                - val_range: A min and max value for the statistic. This is
                    used for consistency when mapping the color palette to the
                    pixel values during web tile image generation.
                - palette: A list of colors to use for the color palette (for
                    web-tiles)
                - z_config: A dict of config options specific to each z-level.
                  Currently, only setting a val_range is supported. Eventually,
                  this could be used to set z-specific tile sizes and color
                  palettes.


        Note: When a min or max value within a val_range is set to None, then
            a min or max value will be calculated for the each z-level for
            which geotiffs are created.

        Example config:
        ---------------

        {
          "tms_id": "WorldCRS84Quad",
          "tile_path_structure": [ "tms", "style", "z", "x", "y"],
          "geotiff_dir": "home/my-geotiffs",
          "web_tiles_dir": "home/my-web-tiles",
          "web_tiles_type": ".png",
          "z_range": [ 0, 13],
          "tile_size": [256,256],
          "statistics": [
            {
              "name": "polygon_count",
              "weight_by": "count",
              "property": "polygon_count",
              "aggregation_method": "sum",
              "resampling_method": "sum",
              "val_range": [0, None],
              "palette": ["#ffffff", "#000000"]
            },
            {
              "name": "coverage",
              "weight_by": "area",
              "property": "grid_area_prop",
              "aggregation_method": "sum",
              "resampling_method": "average",
              "val_range": [0,1],
              "palette": ["red", "blue"],
              "z_config": {
                0: {
                  "val_range": [0,0.5],
                }, ...
              }
            }
          ]
        }

    """

    def __init__(self,
                 config={  # Default config
                     'tms_id': 'WorldCRS84Quad',
                     'tile_path_structure': ('tms', 'stat', 'z', 'x', 'y'),
                     'geotiff_dir': 'geotiff',
                     'web_tiles_dir': 'web_tiles',
                     'web_tiles_type': '.png',
                     'z_range': (0, 13),
                     'tile_size': (256, 256),
                     'statistics': [
                         {
                             'name': 'polygon_count',
                             'weight_by': 'count',
                             'property': 'polygon_count',
                             'aggregation_method': 'sum',
                             'resampling_method': 'sum',
                             'val_range': [0, None],
                         },
                         {
                             'name': 'coverage',
                             'weight_by': 'area',
                             'property': 'grid_area_prop',
                             'aggregation_method': 'sum',
                             'resampling_method': 'average',
                             'val_range': [0, 1]
                         }
                     ]
                 }
                 ):
        """
            Parameters
            ----------
            config : dict or str
                The tiling config object or a path to a JSON file containing
                the tiling config object.
        """
        if isinstance(config, str):
            config = self.read(config)
        self.config = config
        # Save a copy of the original config object, since we will be modifying
        # it
        self.original_config = config.copy()

    def write(self, filename):
        """
            Save the configuration to a JSON file.

            Parameters
            ----------
            filename : str
                The file to save to.
        """
        with open(filename, 'w') as f:
            json.dump(self.config, f, indent=4)

    def read(self, filename):
        """
            Load the configuration from a file.

            Parameters
            ----------
            filename : str
                The file to load from.

            Returns
            -------
            config : dict
                The configuration dictionary.
        """
        with open(filename, 'r') as f:
            config = json.load(f)
        return config

    def set(self, key, value):
        """
            Add a property to the config object.

            Parameters
            ----------
            key : str
                The key to add.
            value : any
                The value to add.
        """
        self.config[key] = value

    def get(self, key):
        """
            Get a property from the config object.

            Parameters
            ----------
            key : str
                The key to get.

            Returns
            -------
            any
                The property.
        """
        return self.config.get(key)

    def get_property_names(self):
        """
            Get all property names from the config object.

            Returns
            -------
            list
                The property names.
        """
        return list(self.config.keys())

    def get_property_values(self):
        """
            Get all property values from the config object.

            Returns
            -------
            list
                The property values.
        """
        return list(self.config.values())

    def get_min_z(self):
        """
            Get the minimum z level. (The lowest resolution level)
        """
        return self.get('z_range')[0]

    def get_max_z(self):
        """
            Get the maximum z level. (The highest resolution level)
        """
        return self.get('z_range')[1]

    def get_palettes(self):
        """
            Get all palettes from the config object.

            Returns
            -------
            list
                The palettes.
        """
        return [stat.get('palette') for stat in self.config['statistics']]

    def get_stat_names(self):
        """
            Get all statistic names from the config object.

            Returns
            -------
            list
                The statistic names.
        """
        return [stat['name'] for stat in self.config['statistics']]

    def get_stat_count(self):
        """
            Return the number of statistics.

            Returns
            -------
            int
                The number of statistics.
        """
        return len(self.config['statistics'])

    def get_stat_config(self, stat=None):
        """
            Get the configuration for a statistic.

            Parameters
            ----------
            statistic : str
                The statistic name.

            Returns
            -------
            dict
                The statistic configuration.
        """
        stats_list = self.config['statistics']
        # Find the stat in stat_list that has the given name
        for stat_config in stats_list:
            if stat_config['name'] == stat:
                return stat_config
        # If no stat with that name is found, return None
        return None

    def get_resampling_methods(self):
        """
            Return a list of resampling methods names from all the
            statistics.

            Returns
            -------
            list
                A list of resampling methods.
        """
        resampling_methods = []
        for stat in self.config['statistics']:
            resampling_methods.append(stat['resampling_method'])
        return resampling_methods

    def get_value_range(self, stat=None, z=None, sub_general=False):
        """
            Get the value range for a statistic at a particular z level. If no
            z level is specified or if there is no value range set for the
            given z level, the general value range for the statistic (at all
            z-levels) is returned.

            Parameters
            ----------
            stat : str
                The statistic name.
            z : int
                The z level.
            sub_general : bool
                When the value range for the given z-level doesn't exist,
                whether or not to substitute it with the general value range.
                If False, None is returned when the value range doesn't exist.
                If True, the general value range is returned if the value range
                for the given z-level doesn't exist.
            Returns
            -------
            tuple or None
                The value range, or None if there is no value range set.
        """
        stat_config = self.get_stat_config(stat)
        if stat_config is None:
            raise ValueError('Statistic not found: {}'.format(stat))

        z_config = stat_config.get('z_config')
        general_val_range = stat_config.get('val_range')

        if z is None:
            return general_val_range
        if z_config is None or z_config.get(z) is None:
            if sub_general:
                return general_val_range
            else:
                return None
        return z_config[z].get('val_range')

    def create_value_range(self, stat=None, z=None, overwrite=False):
        """
            Create a value range for a statistic at a particular z level and
            return it. If no z level is specified, a general value range for
            the statistic will be created. If the value range already exists
            and overwrite is False, the existing value range will be returned.

            Parameters
            ----------
            stat : str
                The statistic name.
            z : int
                The z level.
            overwrite : bool
                Whether to overwrite an existing value range if it exists.
                Default is False.

            Returns
            -------
            list
                The value range.
        """
        stat_config = self.get_stat_config(stat)
        if z is None:
            val_range = stat_config.get('val_range')
            if val_range is None or overwrite:
                val_range = stat_config['val_range'] = [None, None]
            return val_range
        z_config = stat_config.get('z_config')
        if z_config is None:
            z_config = stat_config['z_config'] = {}
        if z_config.get(z) is None:
            z_config[z] = {}
        val_range = z_config[z].get('val_range')
        if val_range is None or overwrite:
            val_range = z_config[z]['val_range'] = [None, None]
        return val_range

    def get_min(self, stat=None, z=None, sub_general=False):
        """
            Get the minimum value for a statistic at a particular z level. If
            no z level is specified, the general minimum value for the
            statistic (at all z-levels) is returned.

            Parameters
            ----------
            stat : str
                The statistic name.
            z : int
                The z level.
            sub_general : bool
                When the min for the given z-level doesn't exist, whether or
                not to substitute it with the general min for the statistic. If
                False, None is returned when the min doesn't exist. If True,
                the general min is returned if the min for the given z-level
                doesn't exist. Default is False.

            Returns
            -------
            float or None
                The minimum value, or None if there is no minimum value set.
        """
        value_range = self.get_value_range(stat, z, sub_general)
        if value_range is None:
            return None
        min_val = value_range[0]
        if min_val is None and sub_general:
            min_val = self.get_value_range(stat, None)[0]
        return min_val

    def get_max(self, stat=None, z=None, sub_general=False):
        """
            Get the maximum value for a statistic at a particular z level. If
            no z level is specified, the general maximum value for the
            statistic (at all z-levels) is returned.

            Parameters
            ----------
            statistic : str
                The statistic name.
            z : int
                The z level.
            sub_general : bool
                When the max for the given z-level doesn't exist, whether or
                not to substitute it with the general max for the statistic. If
                False, None is returned when the max doesn't exist. If True,
                the general max is returned if the max for the given z-level
                doesn't exist. Default is False.

            Returns
            -------
            float or None
                The maximum value, or None if there is no maximum value set.
        """
        value_range = self.get_value_range(stat, z, sub_general)
        if value_range is None:
            return None
        max_val = value_range[1]
        if max_val is None and sub_general:
            max_val = self.get_value_range(stat, None)[1]
        return max_val

    def set_min(self, value, stat=None, z=None):
        """
            Set the minimum value for a statistic at a particular z level. If
            no z level is specified, the general minimum value for the
            statistic (at all z-levels) is set.

            Parameters
            ----------
            value : float
                The minimum value.
            stat : str
                The statistic name.
            z : int
                The z level.
        """
        # Since overwrite is false, if the value range already exists, this
        # will return it
        value_range = self.create_value_range(stat, z)
        value_range[0] = value

    def set_max(self, value, stat=None, z=None):
        """
            Set the maximum value for a statistic at a particular z level. If
            no z level is specified, the general maximum value for the
            statistic (at all z-levels) is set.

            Parameters
            ----------
            value : float
                The maximum value.
            stat : str
                The statistic name.
            z : int
                The z level.
        """
        # Since overwrite is false, if the value range already exists, this
        # will return it
        value_range = self.create_value_range(stat, z)
        value_range[1] = value

    def max_missing(self, stat, z, sub_general=False):
        """
            Whether the maximum value for a statistic at a particular z level
            is missing. A maximum value is missing if no value is set for the
            given z-level and statistic. If sub_general is True, then the
            maximum value is missing only if there is also not a maximum value
            set for the statistic (independently of the z-level).

            Parameters
            ----------
            stat : str
                The statistic name.
            z : int
                The z level.
            sub_general : bool
                When the max for the given z-level doesn't exist, whether or
                not substituting with the general max for that stat is allowed.

            Returns
            -------
            bool
                Whether the maximum value is missing.
        """
        value_range = self.get_value_range(stat, z, sub_general)
        if value_range is None:
            return True
        return value_range[1] is None

    def min_missing(self, stat, z, sub_general=False):
        """
            Whether the minimum value for a statistic at a particular z level
            is missing. A minimum value is missing if no value is set for the
            given z-level and statistic. If sub_general is True, then the
            minimum value is missing only if there is also not a minimum value
            set for the statistic (independently of the z-level).

            Parameters
            ----------
            stat : str
                The statistic name.
            z : int
                The z level.
            sub_general : bool
                When the min for the given z-level doesn't exist, whether or
                not substituting with the general min for that stat is allowed.

            Returns
            -------
            bool
                Whether the minimum value is missing.
        """
        value_range = self.get_value_range(stat, z, sub_general)
        if value_range is None:
            return True
        return value_range[0] is None

    def get_raster_config(self):
        """
            Return a list of statistic configs for the
            Raster.from_vector method. Example of returned config
            looks like:
                [
                    {
                        'name': 'polygon_count',
                        'weight_by': 'count',
                        'property': 'polygon_count',
                        'aggregation_method':'sum'
                    }, {
                        'name': 'coverage',
                        'weight_by': 'area',
                        'property': 'grid_area_prop',
                        'aggregation_method': 'sum'
                    }
                ]

            Returns
            -------
            list
                A list of dicts containing the configuration for each statistic
                to use in the Raster.raster_from_vector method.
        """
        raster_config_keys = (
            'name',
            'weight_by',
            'property',
            'aggregation_method')
        config = []
        for stat_config in self.config['statistics']:
            config.append(
                {k: stat_config[k] for k in raster_config_keys}
            )
        return config

    def get_path_manager_config(self):
        """
            Return a config formated for the TilePathManager class

            Returns
            -------
            dict
                A dict containing the configuration for the Tile Path Manager
                class. Example:
                    {
                        'tms_id: 'WorldCRS84Quad',
                        'path_structure': ['style', 'tms', 'z', 'x', 'y'],
                        'base_dirs': {
                            'geotiff': {
                                'path': 'geotiff',
                                'ext': '.tif'
                            },
                            'web_tiles': {
                                'path': 'web_tiles',
                                'ext': '.png'
                            }
                        }
        """
        return {
            'tms_id': self.get('tms_id'),
            'path_structure': self.get('tile_path_structure'),
            'base_dirs': {
                'geotiff': {
                    'path': self.get('geotiff_dir'),
                    'ext': '.tif'
                },
                'web_tiles': {
                    'path': self.get('web_tiles_dir'),
                    'ext': self.get('web_tiles_type')
                }
            }
        }

    def update_ranges(self, new_ranges):
        """
            Update the value ranges for the statistics, only if there is a min
            or max missing for a given z-level. A min or max is deemed to be
            missing if there is not one set for the stat-z-level combination,
            and there is not a general value set for the stat (independently of
            z).

            Parameters
            ----------
            new_ranges : dict
                A dict of new value ranges for z-level within each statistic.
                Example:
                    {
                        'polygon_count': {
                            '0': (0.8, None), '1': (0, 5),
                    } ...
        """
        for stat, zs in new_ranges.items():
            for z, val_range in zs.items():
                if(self.min_missing(stat, z, True)):
                    self.set_min(val_range[0], stat, z)
                if(self.max_missing(stat, z, True)):
                    self.set_max(val_range[1], stat, z)

    def list_updates(self):
        """
            Compare what has changed between the original config and the
            updated config

            Returns
            -------
            list
                A list of strings describing what has changed.
        """
        current_config = self.config
        original_config = self.original_config
        updates = []

        # which keys have changed
        for key in current_config:
            curr_val = current_config[key]
            old_val = original_config[key]
            if key not in original_config:
                updates.append(f'{key} added')
            elif curr_val != old_val:
                # if the value is a dict, compare the keys
                if isinstance(curr_val, dict):
                    for subkey in curr_val:
                        if subkey not in old_val:
                            updates.append(f'{key}->{subkey} added')
                        elif curr_val[subkey] != old_val[subkey]:
                            updates.append(
                                f'{key}->{subkey} changed from '
                                f'{old_val[subkey]} to '
                                f'{curr_val[subkey]}')
                else:
                    updates.append(
                        f'{key} changed from {old_val} to '
                        f'{curr_val}')

        # which keys have been removed
        for key in original_config:
            if key not in current_config:
                updates.append(f'{key} removed')

        return updates
