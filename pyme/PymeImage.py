from __future__ import annotations
from PIL import Image
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype
from PIL.Image import new, BICUBIC
from typing import Union, Sequence, Iterable, Optional, Tuple
import requests


class PymeImage(object):
    def __init__(self, image: Image.Image):
        """
        A wrapper around a Pillow Image instance equipped with abstract methods to make the creation of memes easier.

        :param image: The Pillow Image instance that the PymeImage should wrap
        """
        self._image = image

    def __getattr__(self, item):
        if item == "_img":
            raise AttributeError()
        return getattr(self._image, item)

    @property
    def image(self):
        """
        Represents the image that teh PymeImage instance wraps.

        :return: Instance of Pillow's PIL.Image.Image
        """
        return self._image

    def _center_image(self, bbox: Sequence[int]) -> Tuple[int, int, int, int]:
        """
        Determines a bounding box inside the given bounding box that would center the given image in that area
        :param bbox: The box inside which to place the image
        :return: A box that is inside the given box but centered
        """
        width_bbox = bbox[2] - bbox[0]
        height_bbox = bbox[3] - bbox[1]

        width_img = self._image.width
        height_img = self._image.height

        return (
            bbox[0] + (width_bbox - width_img) // 2,
            bbox[1] + (height_bbox - height_img) // 2,
            bbox[0] + (width_bbox + width_img) // 2,
            bbox[1] + (height_bbox + height_img) // 2
        )

    def add_padding(self, left: int = 0, top: int = 0, right: int = 0, bottom: int = 0) -> None:
        """
        Adds padding to the Pyme wrapped image

        :param left: Padding on the left side
        :param top: Padding on the top
        :param right: Padding on the right side
        :param bottom: Padding on the bottom
        """
        # Skip if all values are 0
        if not any([left, top, right, bottom]):
            return

        result = self._image.copy()
        new_size = [result.width, result.height]
        paste_coords = [0, 0]

        if left > 0:
            paste_coords[0] = left
            new_size[0] += left
        if top > 0:
            paste_coords[1] = top
            new_size[1] += top
        if right > result.width:
            new_size[0] += right - result.width
        if bottom > result.height:
            new_size[1] += bottom - result.height
        
        background = Image.new("RGBA", new_size, (255, 255, 255, 255))
        background.paste(result, paste_coords, result)
        self._image = background

    def draw_image(self, image: Union[Image.Image, PymeImage], bbox: Sequence[Union[int, float]]) -> None:
        """
        Draws an image onto the image inside the PymeImage Wrapper inside a bounding box.

        :param image: The image to be drawn.
        :param bbox: A bounding box of length 4 that dictates where the image should be placed.
        Both images are adjusted according to this box.
        The drawn image is resized and the wrapped image gets padding if the coordinates are in negative or beyond max.
        """
        # Stop executing early in case of errors to save performance
        if len(bbox) != 4:
            raise ValueError("Bounding box requires 4 arguments")

        # Get values needed for later
        width = self.width
        height = self.height

        # If bbox is an array of percentages, calculate the absolute values
        if isinstance(bbox[0], float):
            bbox = (
                int(bbox[0] * width),
                int(bbox[1] * height),
                int(bbox[2] * width),
                int(bbox[3] * height)
            )

        # Adding padding if any is needed
        if bbox[0] < 0 or bbox[1] < 0 or bbox[2] > width or bbox[3] > height:
            self.add_padding(abs(bbox[0]), abs(bbox[1]), bbox[2], bbox[3])

        # Check whether the image is wrapped in PymeImage
        if isinstance(image, PymeImage):
            image = image.image

        # Adjust size of the image to be drawn
        new_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
        image = PymeImage(image).resize(new_size, keep_ratio=True).image

        # Paste the image
        paste_coords = [
            bbox[0] if bbox[0] > 0 else 0,
            bbox[1] if bbox[1] > 0 else 0,
            bbox[2],
            bbox[3]
        ]
        paste_coords = PymeImage(image)._center_image(paste_coords)
        try:
            self._image.paste(image, paste_coords[:2], image)
        except ValueError:
            self._image.paste(image, paste_coords[:2])

    def draw_text(self, text: str, bbox: Sequence[Union[int, float]]) -> None:
        """
        Draws given text on self at given coordinates.

        :param text: The text to be drawn.
        :param bbo: A Sequence of Bounding box coordinates to draw text in.
        Can be either Percentages via floats or pixels via ints.
        :exception ValueError: If bbox has the wrong length.
        """
        # Check Sequence length to prevent IndexErrors
        if len(bbox) != 4:
            raise ValueError("Bounding box requires 4 arguments")

        # Get the impact font
        impact_font = truetype("Impact", 50)

        # Measure the area that the text should be drawn on with a dummy ImageDraw
        size = Draw(new("RGBA", (1, 1))).multiline_textbbox((0., 0.), text, impact_font, stroke_width=4)
        size = [int(i) for i in size[2:]]

        # Create the area that the text should be drawn on
        text_background = new("RGBA", size, (0, 0, 0, 0))

        # Draw text onto the text_background
        text_background_draw = Draw(text_background)
        text_background_draw.multiline_text((0, 0), text, (255, 255, 255, 255), impact_font, stroke_width=4, stroke_fill=(0, 0, 0, 255))

        # Draw image containing text onto original image
        self.draw_image(text_background, bbox)

    def resize(self, size: Tuple[int, int], resample: int = BICUBIC, box: Optional = None,
               reducing_gap: Optional = None, keep_ratio: bool = False) -> PymeImage:
        """
        A wrapper around the Pillow resize function that adds a keep ratio parameter.

        :param size: A 2-tuple dictating the new width and height of the image.
        :param resample: The resample method to use to resize the image.
        :param box: A bounding box that describes an area inside the image to be resized.
        :param reducing_gap: pply optimization by resizing the image in two steps.
        First, reducing the image by integer times using :py:meth:`~PIL.Image.Image.reduce`.
        Second, resizing using regular resampling.
        The last step changes size no less than by ``reducing_gap`` times.
        ``reducing_gap`` may be None (no first step is performed) or should be greater than 1.0.
        The bigger ``reducing_gap``, the closer the result to the fair resampling.
        The smaller ``reducing_gap``, the faster resizing.
        With ``reducing_gap`` greater or equal to 3.0,
        the result is indistinguishable from fair resampling in most cases.
        The default value is None (no optimization)
        :param keep_ratio: Determines whether or not the imae should keep its original ratio.
        The image will be resized to the point that both sides are equal or smaller than the given ones.
        :return: An instance of the PymeImage wrapper to be used for chaining
        """
        if keep_ratio:
            width = self.width
            height = self.height

            width_quotient = size[0] / width
            height_quotient = size[1] / height

            if width_quotient < height_quotient:
                new_width = int(width * width_quotient)
                new_height = int(height * width_quotient)
                self._image = self._image.resize((new_width, new_height), resample, box, reducing_gap)
            else:
                new_width = int(width * height_quotient)
                new_height = int(height * height_quotient)
                self._image = self._image.resize((new_width, new_height), resample, box, reducing_gap)
        else:
            self._image = self._image.resize(size, resample, box, reducing_gap)
        return self

    @classmethod
    def from_url(cls, url: str) -> PymeImage:
        """
        Returns a PymeImage that wraps around the Pillow image from a given URL.

        :param url: Url to pull from.
        :return: Resulting PymeImage Wrapper.
        """
        img: Image.Image = Image.open(requests.get(url, stream=True).raw)
        return cls(img)

    @classmethod
    def open(cls, fp, mode: str = "r", formats: Optional[Iterable] = None) -> PymeImage:
        """
        Utilizes Pillows built-in open function to create an instance of Image and package it in a PymeImage.
        For more details check PIL.Image.open

        :param fp: The file to be opened as a filename, pathlib.Path of file object.
        :param mode: The mode, if given this argument must be "r".
        :param formats: An Iterable of formats to try and interpret the file in.
        :return: An instance of PymeImage that wraps a Pillow Image.
        """
        return cls(Image.open(fp, mode, formats))

