#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

from enum import Enum

from cozmonaut.component import AbstractComponent
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
        self.op_name = op_name
        self.op_args = op_args

    def start(self):
        # Create the relevant operation instance
        op = None
        if self.op_name == ClientOperation.friend_list:
            op = OperationFriendList(self.op_args)
        elif self.op_name == ClientOperation.friend_remove:
            op = OperationFriendRemove(self.op_args)
        elif self.op_name == ClientOperation.interact:
            op = OperationInteract(self.op_args)

        op.main()

    def stop(self):
        pass
