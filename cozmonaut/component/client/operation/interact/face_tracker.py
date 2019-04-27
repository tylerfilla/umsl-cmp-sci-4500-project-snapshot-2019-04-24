#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import PIL.Image


class FaceTracker:
    """
    A tracker for faces in a stream of images.
    """

    def update(self, image: PIL.Image):
        """
        Update the tracker with the next image in the stream.

        :param image: The next frame
        """
