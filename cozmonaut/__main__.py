#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import time

from cozmonaut.component.client import ComponentClient, ClientOperation
from cozmonaut.component.client.operation.interact import OperationInteractMode

if __name__ == '__main__':
    # Arguments for Cozmo interactions
    args = {
        'mode': OperationInteractMode.only_a,
        'serial_a': '45a18821',
        'serial_b': None,  # No second Cozmo yet
    }

    # Create client component and prime it to launch the "interact" operation with above arguments
    comp = ComponentClient(ClientOperation.interact, args)

    # Start client component
    comp.start()

    # Wait to simulate running other stuff
    # TODO: This is where we can run the text-to-speech input (ncurses?), install ^C handler, etc.
    time.sleep(600)

    # Stop client component
    comp.stop()
