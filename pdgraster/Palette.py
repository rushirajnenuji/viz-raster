import numbers
import re

import colormaps as cmaps
from coloraide import Color
from colormaps.colormap import Colormap


class Palette:
    """
    A Palette object handles a list of colors that represent a continuous
    gradient, plus a nodata color.
    """

    default_colors = ["#FFFFFF", "#000000"]
    default_nodata_color = "#ffffff00"

    def __init__(self, colors=None, nodata_color=None):
        """
        Create a Palette object.

        Parameters
        ----------
        colors : list of str, str, or colormaps.colormap.Colormap
            A list of color strings in any format accepted by the coloraide
            library (see: https://facelessuser.github.io/coloraide/color/).
            Alternatively, provide the name of a colormap from the
            colormaps library or a Colormap object (see:
            https://pratiman-91.github.io/colormaps). If not set, a color
            range of black to white will be used.
        nodata_color : str, optional
            A color string in any format accepted by the coloraide library.
            This color will be used to represent missing data or no data.
            Set to transparent by default.

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
        colors : list of str or colormaps.colormap.Colormap
            A list of color strings in any format accepted by the coloraide
            library (see: https://facelessuser.github.io/coloraide/color/),
            or a Colormap object from the colormaps library (see:
            https://pratiman-91.github.io/colormaps).
        nodata_color : str
            A color string in any format accepted by the coloraide library.
            This color will be used to represent missing data or no data.
        """
        self.colors = self.check_colors(colors)
        no_datacolor = self.check_nodata_color(nodata_color)
        self.nodata_color = self.__coloraide_to_rgba__(Color(no_datacolor))
        self.__get_color__ = self.create_get_color_method()
        self.rgba_list = self.get_rgba_list()

    def check_colors(self, colors):
        """
        Check that the colors are valid. Raise an error if not.

        Parameters
        ----------
        colors : list of str, str, or colormaps.colormap.Colormap
            The colors to check

        Returns
        -------
        list of str or colormaps.colormap.Colormap
            The colors, if they are valid. If colors was the name of a
            colormap, then the Colormap object is returned. If colors was a
            single color string, then it is returned as a list of one
            color.
        """

        if not isinstance(colors, (list, tuple, Colormap, str)):
            raise TypeError("colors must be a str, list, tuple, or Colormap object.")
        if isinstance(colors, list):
            if not all(isinstance(i, str) for i in colors):
                raise TypeError(
                    "When providing colors as a list, all elements must be " "strings."
                )
        elif isinstance(colors, str):
            try:
                colors = getattr(cmaps, colors)
            except AttributeError:
                try:
                    color = Color(colors)
                    colors = [color]
                except ValueError:
                    raise ValueError(
                        f"The given color string({colors}) is not a colormap "
                        "available in the colormaps library nor is it a valid "
                        "color string in the coloraide library. For a list "
                        "of available colormaps, see: "
                        "https://facelessuser.github.io/coloraide/color/."
                        "To see how to format a color string, see: "
                        "https://facelessuser.github.io/coloraide/color/."
                    )
        return colors

    def check_nodata_color(self, nodata_color):
        """
        Check that the nodata color is a valid color string.

        Parameters
        ----------
        nodata_color : str
            The nodata color string to check.

        Returns
        -------
        str
            The unchanged nodata color string, if it is valid.
        """
        try:
            Color(nodata_color)
        except ValueError:
            raise ValueError(
                f"The given nodata color string({nodata_color}) is not a valid"
                " color string in the coloraide library. For a list of "
                "available colors, see: "
                "https://facelessuser.github.io/coloraide/color/. "
                "To see how to format a color string, see: "
                "https://facelessuser.github.io/coloraide/color/."
            )
        return nodata_color

    def create_get_color_method(self):
        """
        Create a function that takes a value between 0 and 1 and returns a
        tuple of RGBA values (0-255) for the corresponding color. This
        method does not check that the value is between 0 and 1, and will
        not return the nodata color.
        """

        cols = self.colors

        if isinstance(cols, list):

            # The Palette is faster if we only create the coloraide method once
            self.__coloraide_method__ = Color(cols[0]).interpolate(
                cols[1:], space="lch"
            )

            def _get_color(val):
                col_obj = self.__coloraide_method__(val)
                return self.__coloraide_to_rgba__(col_obj)

        elif isinstance(cols, Colormap):

            def _get_color(val):
                val = float(val)
                return self.colors.__call__(val, bytes=True)

        return _get_color

    def get_color(self, val, type="rgba"):
        """
        Get the color for a given value between 0 and 1.

        Parameters
        ----------
        val : float
            The value to get the color for. Must be between 0 and 1. If 0 >
            val > 1, the color for the closest value will be returned. If
            val is not a number, the nodata color will be returned.
        type : str, optional
            The type of color to return. Must be one of 'rgba', 'rgb', or
            'hex'. Defaults to 'rgba'.
        Returns
        -------
        tuple of int
            A tuple of RGBA values (0-255) for the color.
        """

        if self.__get_color__ is None:
            self.__get_color__ = self.create_get_color_method()
        if not isinstance(val, numbers.Number):
            rgba = self.nodata_color
        else:
            val = max(0, min(val, 1))
            rgba = self.__get_color__(val)
        if type == "rgba":
            if len(rgba) == 3:
                rgba = rgba + (255,)
            return rgba
        elif type == "rgb":
            return rgba[:3]
        elif type == "hex":
            return self.__rgba_to_hex__(rgba)

    @staticmethod
    def __rgba_to_hex__(rgba):
        """
        Convert an RGBA tuple of values (0-255) to a hex string.

        Parameters
        ----------
        rgba : tuple or list of int
            The RGBA values to convert.

        Returns
        -------
        str
            The hex string representing the RGBA values.
        """
        return "#%02x%02x%02x%02x" % tuple(rgba)

    @staticmethod
    def __coloraide_to_rgba__(col_obj):
        """
        Convert a Color object from the coloraide library to a RGBA tuple.
        """
        col_str = col_obj.convert("srgb").to_string(precision=3, alpha=True)
        # parse the string for rgba values
        rgba = list(float(i) for i in re.findall(r"[\d\.]+", col_str))
        # Alpha should be 255 as well
        rgba[3] = rgba[3] * 255
        # Round rgba to integers
        rgba = [int(i) for i in rgba]
        return rgba

    def get_rgba_list(self, pal_size=256):
        """
        Create a list of 257 RGBA values that represent the palette,
        interpolating between the colors in the palette. The last value in
        the list is the nodata color.
        """

        pal_values = [x / pal_size for x in range(pal_size)]
        pal_rgba = [self.get_color(i) for i in pal_values]

        pal_rgba.extend([self.get_color(None)])  # nodata color
        return pal_rgba
