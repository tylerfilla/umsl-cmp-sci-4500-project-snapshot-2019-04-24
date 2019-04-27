#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import asyncio

import cozmo

from cozmonaut.op import Op


class OpInteract(Op):
    """
    The interactive mode operation.

    In this mode, the Cozmo robots are driven around to perform the primary goal
    of meeting and greeting people. Support is hardcoded for two Cozmo robots,
    and they are assigned the roles of Cozmo A and Cozmo B.

    TODO: Add information about how the interact
    """

    def __init__(self, args: dict):
        super().__init__(args)

        # Operation arguments
        self.args = args

    def main(self):
        # Get the event loop on this thread
        loop = asyncio.get_event_loop()

        # The serial numbers for Cozmos A and B
        serial_a = self.args['serial_a']
        serial_b = self.args['serial_b']

        print(f'Want Cozmo A to have serial number {serial_a}')
        print(f'Want Cozmo B to have serial number {serial_b}')

        # Live robot instances for Cozmos A and B
        robot_a = None
        robot_b = None

        while True:
            # Connect to next available Cozmo
            conn = None
            try:
                conn = cozmo.connect_on_loop(loop)
            except cozmo.exceptions.NoDevicesFound:
                break

            # Wait for the robot to become available
            # We must do this to read its serial number
            robot = loop.run_until_complete(conn.wait_for_robot())

            print(f'Found a robot with serial {robot.serial}')

            # Keep robot instances with desired serial numbers
            if robot.serial == serial_a:
                robot_a = robot
            if robot.serial == serial_b:
                robot_b = robot

            # If both are assigned, we're good!
            if robot_a is not None and robot_b is not None:
                print('Both Cozmo A and Cozmo B assigned')
                break

        # A list for main function coroutines
        # Coroutine objects for both the _cozmo_a_main and _cozmo_b_main async functions can go here
        # Or neither of them can go here (that depends on which serial numbers were specified and found above)
        coroutines_for_cozmo = []

        # If we assigned a robot instance to play Cozmo A...
        if robot_a is not None:
            print(f'The role of Cozmo A is being played by robot {robot_a.serial}')

            # Obtain a coroutine for Cozmo A main function
            # Add the coroutine to the above coroutine list
            coroutines_for_cozmo.append(self._cozmo_a_main(robot_a))
        else:
            print('Unable to cast the role of Cozmo A')
            return

        # If we assigned a robot instance to play Cozmo B...
        if robot_b is not None:
            print(f'The role of Cozmo B is being played by robot {robot_b.serial}')

            # Obtain a coroutine for Cozmo B main function
            # Add the coroutine to the above coroutine list
            coroutines_for_cozmo.append(self._cozmo_b_main(robot_b))
        else:
            print('Unable to cast the role of Cozmo B')
            return

        # I think this is an aptly-named variable
        # This wraps all the coroutine objects above into one task object and schedules it
        everything = asyncio.gather(
            # Expand the main coroutines list into arguments
            *coroutines_for_cozmo,
            loop=loop,
        )

        # Run everything on the loop
        loop.run_until_complete(everything)

    async def _cozmo_a_main(self, robot: cozmo.robot.Robot):
        """
        Main function for Cozmo A.

        :param robot: The robot instance
        """
        pass

    async def _cozmo_b_main(self, robot: cozmo.robot.Robot):
        """
        Main function for Cozmo B.

        :param robot: The robot instance
        """
        pass


# Do not leave the charger until we say it's okay
cozmo.robot.Robot.drive_off_charger_on_connect = False