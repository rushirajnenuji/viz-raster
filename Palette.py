import re

from coloraide import Color


class Palette():
    """
        A Palette object handles a list of colors that represent a continuous
        gradient.
    """

    default_colors = ['#FFFFFF', '#000000']

    def __init__(
        self,
        colors=None,
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
        self.update_colors(colors)

    def update_colors(self, colors):
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
        self.gradient = self.create_gradient()
        self.flat_palette = self.get_flat_palette()

    def create_gradient(self):
        """
            Create a function that takes a value between 0 and 1 and returns a
            Color object.
        """
        return Color(self.colors[0]).interpolate(self.colors[1:], space='lch')

    def get_flat_palette(self):
        """
            Create a list of 1024 integer values, where each group of four
            values represent represent red, green, blue, and alpha values for
            the corresponding pixel index. The values can be used with the PIL
            Image.putpalette function.
        """
        pal_size = 256
        pal_values = [x / pal_size for x in range(pal_size)]
        pal_rgba = [self.get_rgba(i) for i in pal_values]
        pal_flat = [item for sublist in pal_rgba for item in sublist]
        return pal_flat

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
