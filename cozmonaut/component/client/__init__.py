#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

from enum import Enum

from cozmonaut.component import AbstractComponent
from cozmonaut.component.client.operation import AbstractClientOperation
from cozmonaut.component.client.operation.friend_list import OperationFriendList
from cozmonaut.component.client.operation.friend_remove import OperationFriendRemove
from cozmonaut.component.client.operation.interact import OperationInteract


class ClientOperation(Enum):
    """
    A named client operation.

    This enum specifies symbols for each of the supported client operations.
    """

    friend_list = 1
    friend_remove = 2
    interact = 3


class ComponentClient(AbstractComponent):
    """
    The client component.

    This is responsible for the major client functionality of the application
    in the form of so-called client operations. The operation is specified in
    the constructor, and the operation is run on a background thread when the
    component, itself, is started.
    """

    def __init__(self, op_name: ClientOperation, op_args: dict):
        self._op_name = op_name
        self._op_args = op_args

        self._op = None

    def start(self):
        # Create the relevant operation instance
        if self._op_name == ClientOperation.friend_list:
            self._op = OperationFriendList(self._op_args)
        elif self._op_name == ClientOperation.friend_remove:
            self._op = OperationFriendRemove(self._op_args)
        elif self._op_name == ClientOperation.interact:
            self._op = OperationInteract(self._op_args)

        # Start the operation
        self._op.start()

    def stop(self):
        # Stop the operation
        self._op.stop()
