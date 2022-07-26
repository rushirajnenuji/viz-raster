import re
import numbers
from coloraide import Color


class Palette():
    """
        A Palette object handles a list of colors that represent a continuous
        gradient.
    """

    default_colors = ['#FFFFFF', '#000000']
    default_nodata_color = '#ffffff00'

    def __init__(
        self,
        colors=None,
        nodata_color=None
    ):
        """
            Create a Palette object.

            Parameters
            ----------
            colors : list of str, optional
                A list of color strings in any format accepted by the coloraide
                library. If not set, a color range of black to white will be
                used.
        """
        if colors is None:
            colors = self.default_colors
        if nodata_color is None:
            nodata_color = self.default_nodata_color
        self.update_colors(colors, nodata_color)

    def update_colors(self, colors, nodata_color):
        """
            Update the palette colors with a new list of colors.

            Parameters
            ----------
            colors : list of str, required
                A list of color strings in any format accepted by the coloraide
                library. If not set, a color range of black to white will be
                used.
        """
        self.colors = colors
        self.nodata_color = nodata_color
        self.gradient = self.create_gradient()
        self.rgba_list = self.get_rgba_list()

    def create_gradient(self):
        """
            Create a function that takes a value between 0 and 1 and returns a
            Color object.
        """
        cols = self.colors
        self.__gradient_vals_only = Color(
            cols[0]).interpolate(cols[1:], space='lch')

        def gradient(val):
            # if the value is anything other than a number, return the nodata
            # color
            if not isinstance(val, numbers.Number):
                return Color(self.nodata_color)
            # if the value is less than 0, return the first color
            if val < 0:
                val = 0
            # if the value is greater than 1, return the last color
            if val > 1:
                val = 1
            return self.__gradient_vals_only(val)
        return gradient

    def get_rgba_list(self, pal_size=256):
        """
            Create a list of 257 RGBA values that represent the palette,
            interpolating between the colors in the palette. The last value in
            the list is the nodata color.
        """
        pal_values = [x / pal_size for x in range(pal_size)]
        pal_rgba = [self.get_rgba(i) for i in pal_values]
        pal_rgba.extend([self.get_rgba(None)])  # nodata color
        return pal_rgba

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
