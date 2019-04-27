#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

from abc import ABC, abstractmethod


class AbstractClientOperation(ABC):
    """
    A client operation.
    """

    @abstractmethod
    def __init__(self, args: dict):
        """
        Initialize the operation with arguments.

        Each specific operation accepts different arguments, so see the
        documentation of a specific operation for such information.

        :param args: The operation arguments
        """
        pass

    @abstractmethod
    def main(self):
        """
        The operation main function.
        """
        pass
