#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

from abc import ABC, abstractmethod


class AbstractComponent(ABC):
    """
    An app component.
    """

    @abstractmethod
    def start(self):
        """
        Start the component.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        Stop the component.
        """
        pass
