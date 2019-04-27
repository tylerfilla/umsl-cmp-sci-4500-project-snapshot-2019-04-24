#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

from cozmonaut.component.client.operation import AbstractClientOperation


class OperationFriendList(AbstractClientOperation):
    """
    The friend list operation.
    """

    def __init__(self, args: dict):
        super().__init__(args)

        # Operation arguments
        self.args = args

    def start(self):
        print('friend list')

    def stop(self):
        # TODO: Wait for all DB operations to finish, etc.
        pass
