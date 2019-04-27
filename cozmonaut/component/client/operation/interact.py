#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import asyncio
import functools

import cozmo

from cozmonaut.component.client.operation import AbstractClientOperation


class OperationInteract(AbstractClientOperation):
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
        serial_a = self.args.get('serial_a', '')
        serial_b = self.args.get('serial_b', '')

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

            # If the current mode requires Cozmo A to be assigned
            if self.args['mode'] == 'only_a' or self.args['mode'] == 'a_and_b':
                print('Refusing to continue because Cozmo A was not assigned')
                return
            else:
                print('Continuing without Cozmo A...')

        # If we assigned a robot instance to play Cozmo B...
        if robot_b is not None:
            print(f'The role of Cozmo B is being played by robot {robot_b.serial}')

            # Obtain a coroutine for Cozmo B main function
            # Add the coroutine to the above coroutine list
            coroutines_for_cozmo.append(self._cozmo_b_main(robot_b))
        else:
            print('Unable to cast the role of Cozmo B')

            # If the current mode requires Cozmo B to be assigned
            if self.args['mode'] == 'only_b' or self.args['mode'] == 'a_and_b':
                print('Refusing to continue because Cozmo B was not assigned')
                return
            else:
                print('Continuing without Cozmo B...')

        # This wraps all the coroutine objects above into one task object and schedules it
        asyncio.gather(
            # Expand the main coroutines list into arguments
            *coroutines_for_cozmo,
            loop=loop,
        )

        # Run the loop forever
        loop.run_forever()

    async def _cozmo_a_main(self, robot: cozmo.robot.Robot):
        """
        Main function for Cozmo A.

        :param robot: The robot instance
        """

        # Enable color imaging on this robot's camera
        robot.camera.color_image_enabled = True
        robot.camera.image_stream_enabled = True

        # Register to receive camera frames from this robot
        robot.camera.add_event_handler(cozmo.robot.camera.EvtNewRawCameraImage,
                                       functools.partial(self._on_new_raw_camera_image, robot))

        # Schedule a battery watchdog for this robot onto the loop
        asyncio.ensure_future(self._battery_watchdog(robot))

        # TODO: Add control stuffs for robot A
        while True:
            # Yield control
            await asyncio.sleep(0)

    async def _cozmo_b_main(self, robot: cozmo.robot.Robot):
        """
        Main function for Cozmo B.

        :param robot: The robot instance
        """

        # Enable color imaging on this robot's camera
        robot.camera.color_image_enabled = True
        robot.camera.image_stream_enabled = True

        # Register to receive camera frames from this robot
        robot.camera.add_event_handler(cozmo.robot.camera.EvtNewRawCameraImage,
                                       functools.partial(self._on_new_raw_camera_image, robot))

        # Schedule a battery watchdog for this robot onto the loop
        asyncio.ensure_future(self._battery_watchdog(robot))

        # TODO: Add control stuffs for robot B
        while True:
            # Yield control
            await asyncio.sleep(0)

    def _on_new_raw_camera_image(self, robot: cozmo.robot.Robot, evt: cozmo.robot.camera.EvtNewRawCameraImage,
                                 **kwargs):
        """
        Event handler for a robot's "new raw camera image" event.

        This function is not asynchronous, so do not block on any I/O.

        :param robot: The robot instance
        :param evt: The event instance
        """

        pass

    async def _battery_watchdog(self, robot: cozmo.robot.Robot):
        """
        A battery watchdog for either Cozmo A or B.

        This is responsible for watching the battery potential on a robot object
        instance

        :param robot: The robot instance
        """

        while True:
            # If battery potential is below the recommended "low" level
            if robot.battery_voltage < 3.5:
                # TODO: Drive the robot back to charge and swap the next one in
                print('THE BATTERY IS LOW')
                break

            # Yield control
            await asyncio.sleep(0)


# Do not leave the charger until we say it's okay
cozmo.robot.Robot.drive_off_charger_on_connect = False
