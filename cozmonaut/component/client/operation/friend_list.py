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

    def main(self):
        print('friend list')
