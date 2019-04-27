#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

from cozmonaut.op.interact import OpInteract

if __name__ == '__main__':
    # TODO: Add a command-line interface (something with git-like subcommands would be nice)
    op = OpInteract({
        'mode': 'only_a',
        'serial_a': '45a18821',
        'serial_b': '???',
    })
    op.main()
