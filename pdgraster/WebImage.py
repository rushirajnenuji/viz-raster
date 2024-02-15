import os

from PIL import Image
import numpy as np

from . import Palette

import time
import uuid
import logging
from . import logging_config
import os
logger = logging_config.logger


class WebImage():
    """
        A Web Image class creates a PIL image from a numpy array and list of
        colors. The PIL image can be saved to a file in a format that can be
        used by web-based maps (e.g. Cesium).
    """

    def __init__(
        self,
        image_data,
        palette=Palette(['#663399', '#ffcc00'], '#ffffff00'),
        min_val=None,
        max_val=None,
        nodata_val=None
    ):
        """
            Create a WebImage object.

            Parameters
            ----------
            image_data : numpy.array, required
                The array of pixel values.
            palette: Palette, list, tuple, optional
                Either a Palette object or a list/tuple with two items. The
                first item is a list of color strings or name of a colormap,
                and the second item is the nodata color represented as a
                string. Color strings can be in any format accepted by the
                coloraide library. Colormap names can be any supported by the
                colormaps library. If not set, a color range of purple to
                yellow will be used, with a nodata color of transparent.
            min_val : float, optional
                Set a min value that is different from the min value that
                exists in the image_data. The min value will translate to the
                first color in the palette.
            max_val : float, optional
                Set a max value that is different from the max value that
                exists in the image_data. The max value will translate to the
                last color in the palette.
            nodata_val : any, optional
                Set a value that will be treated as missing data or no data.
                Pixels with this value will be set to the nodata color that is
                specified in the palette. If not set, None will be used.
        """

        # Calculate the min and max values if they are not provided
        if min_val is None or max_val is None:
            # get the min & max while ignoring the NaN values, None values, and
            # infinities. Can't test for finite values if array contains None,
            # converting to float will convert the Nones to np.nan.
            data_for_calcs = image_data.copy().astype(np.float64)
            data_for_calcs = data_for_calcs[np.isfinite(data_for_calcs)]
            data_for_calcs = data_for_calcs.flatten()
            if min_val is None:
                min_val = np.nanmin(data_for_calcs)
            if max_val is None:
                max_val = np.nanmax(data_for_calcs)

        self.min_val = min_val
        self.max_val = max_val
        self.nodata_val = nodata_val
        if isinstance(palette, (list, tuple)):
            palette = Palette(*palette)
        self.rgba_list = palette.rgba_list
        self.image_data = image_data
        self.height = image_data.shape[0]
        self.width = image_data.shape[1]
        self.image = self.to_image(image_data)

    def to_image(self, image_data):
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

        min_val = self.min_val
        max_val = self.max_val
        nodata_val = self.nodata_val
        image_data = image_data.copy()
        rgba_list = self.rgba_list
        height = self.height
        width = self.width
        image_data = image_data.astype(float)
        no_data_mask = image_data == nodata_val

        # set the nodata value to np.nan
        if(len(no_data_mask)):
            image_data[no_data_mask] = np.nan
        # convert the array from min to max to 0 to 255, and set the nodata
        # values 256. Values < min_val will be set to min_val. Values > max_val
        # will be set to max_val.
        image_data[image_data < min_val] = min_val
        image_data[image_data > max_val] = max_val
        image_data_scaled = (image_data - min_val) * \
            (255 / (max_val - min_val))
        image_data_scaled[no_data_mask] = 256
        image_data_scaled = image_data_scaled.astype(int)

        # replace each value in the matrix with the corresponding color in the
        # list of rgba values. palette. The list consists of 256 RGBA values,
        # plus a 257th value for the nodata color.
        rgba_data = [rgba_list[i] for i in image_data_scaled.flat]
        # reshape
        rgba_data = np.reshape(rgba_data, (height, width, 4))
        rgba_data = rgba_data.astype(np.uint8)

        img_pil = Image.fromarray(rgba_data, 'RGBA')
        return img_pil

    def save(self, filename):
        """
            Save the image to a file. If the file already exists, it will be
            overwritten. If the directory does not exist, it will be created.

            Parameters
            ----------
            filename : str
                The path to the file to save the image to.
        """
        # Create the directory if it doesn't exist
        dirname = os.path.dirname(filename)
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        self.image.save(filename)

    def show(self):
        """
            Display the image.
        """
        self.image.show()

    def get_image(self):
        """
            Returns the image.
        """
        return self.image
