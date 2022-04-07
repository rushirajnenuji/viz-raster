import os

from PIL import Image
import numpy as np

from . import Palette


class WebImage():
    """
        A Web Image class creates a PIL image from a numpy array and list of
        colors. The PIL image can be saved to a file in a format that can be
        used by web-based maps (e.g. Cesium).
    """

    def __init__(
        self,
        image_data,
        palette=Palette(['rgb(102 51 153 / 0.1)', 'lch(85% 100 85)']),
        min_val=None,
        max_val=None
    ):
        """
            Create a WebImage object.

            Parameters
            ----------
            image_data : numpy.array, required
                The array of pixel values.
            palette: Palette or list of str, optional
                Either a Palette object or a list of color strings in any
                format accepted by the coloraide library. The RGBA values that
                comprise this palette will be mapped linearly to the pixel
                values in the image_data.
            min_val : float, optional
                Set a min value that is different from the min value that
                exists in the image_data. The min value will translate to the
                first color in the palette.
            max_val : float, optional
                Set a max value that is different from the max value that
                exists in the image_data. The max value will translate to the
                last color in the palette.

        """
        if min_val is None:
            min_val = np.min(image_data)
        if max_val is None:
            max_val = np.max(image_data)
        self.min_val = min_val
        self.max_val = max_val
        if isinstance(palette, list):
            palette = Palette(palette)
        self.palette = palette.flat_palette
        self.image = self.to_image(image_data)

    def to_unit8(self, values):
        """
            Takes an array of values and scales it to 0-255. The min and max
            values are used to first rescale the values to the range [0, 1].
            Any numbers greater than the max will be set to 255 in the output,
            and any numbers less than the min will be set to 0.

            Parameters
            ----------
            values : numpy.array
                The array of values to be scaled.

            Returns
            -------
            numpy.array
                An array of np.uint8 values.
        """

        # Normalize the array so that it's between 0 and 1
        values = (values - self.min_val) / (self.max_val - self.min_val)
        # Make sure the array is between 0 and 255
        values = np.where(values > 1, 1, values)
        values = np.where(values < 0, 0, values)
        # Convert the array to uint8
        values = values * 255
        values = values.astype(np.uint8)
        return values

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

        image_data = self.to_unit8(image_data)
        img_pil = Image.fromarray(image_data, 'P')
        img_pil.putpalette(self.palette, rawmode='RGBA')
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
        if not os.path.exists(dirname):
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
