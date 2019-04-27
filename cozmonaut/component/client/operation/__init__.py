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
    def start(self):
        """
        Start the operation synchronously.
        """

    @abstractmethod
    def stop(self):
        """
        Stop the operation synchronously.
        """
