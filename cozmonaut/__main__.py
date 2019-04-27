#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import time

from cozmonaut.component.client import ComponentClient, ClientOperation

if __name__ == '__main__':
    # Arguments for Cozmo interactions
    args = {
        'mode': 'only_a',  # TODO: Replace this with an enum
        'serial_a': '45a18821',
        'serial_b': '',  # No second Cozmo yet
    }

    # Create client component and prime it to launch the "interact" operation with above arguments
    comp = ComponentClient(ClientOperation.interact, args)

    # Start client component
    comp.start()

    # Wait to simulate running other stuff
    time.sleep(5)

    # Stop client component
    comp.stop()
