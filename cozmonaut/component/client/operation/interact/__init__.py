#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import asyncio
import threading
from enum import Enum

import cozmo

from cozmonaut.component.client.operation import AbstractClientOperation
from cozmonaut.component.client.operation.interact.face_tracker import FaceTracker


class OperationInteractMode(Enum):
    """
    A mode for interaction with Cozmo(s).
    """

    both = 0  # Run both Cozmos interactively
    only_a = 1  # Only run Cozmo A interactively
    only_b = 2  # Only run Cozmo B interactively


class OperationInteract(AbstractClientOperation):
    """
    The interactive mode operation.

    In this mode, the Cozmo robots are driven around to perform the primary goal
    of meeting and greeting people. Support is hardcoded for two Cozmo robots,
    and they are assigned the roles of Cozmo A and Cozmo B.

    TODO: Add information about how they interact with passersby and themselves
    """

    def __init__(self, args: dict):
        self._args = args

        # Control variables for the component
        # This is at the level of the command-line app hosting us
        self._should_stop = False
        self._stopping = False
        self._thread = None

        # Control variables for the robots
        # This is at the level of interacting with passersby
        self._swap = False  # TODO: This is the "global" flag from the whiteboard
        self._convo = False  # TODO: Conversation flag
        self._cd = 0  # TODO: Conversation identifier (better name?)

        # The live robot instances
        self._robot_a = None
        self._robot_b = None

        # The face trackers for the respective robots
        self._face_tracker_a = FaceTracker()
        self._face_tracker_b = FaceTracker()

    def start(self):
        # Start operation thread
        self._thread = threading.Thread(target=self.main)
        self._thread.start()

    def stop(self):
        # Set the kill switch
        self._should_stop = True

        # Wait for the thread to die
        # This also waits for the Cozmos to park, potentially
        self._thread.join()

    def main(self):
        # Create an event loop on this thread
        loop = asyncio.new_event_loop()

        # The mode of interaction
        mode = self._args.get('mode')

        # The serial numbers for Cozmos A and B
        serial_a = self._args.get('serial_a')
        serial_b = self._args.get('serial_b')

        print(f'Want Cozmo A to have serial number {serial_a or "(unknown)"}')
        print(f'Want Cozmo B to have serial number {serial_b or "(unknown)"}')

        while True:
            # Connect to next available Cozmo
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
                self._robot_a = robot
            if robot.serial == serial_b:
                self._robot_b = robot

            # If both are assigned, we're good!
            if self._robot_a is not None and self._robot_b is not None:
                print('Both Cozmo A and Cozmo B assigned')
                break

        # A list for main function coroutines
        # Coroutine objects for both the _cozmo_a_main and _cozmo_b_main async functions can go here
        # Or neither of them can go here (that depends on which serial numbers were specified and found above)
        coroutines_for_cozmo = []

        # If we assigned a robot instance to play Cozmo A...
        if self._robot_a is not None:
            print(f'The role of Cozmo A is being played by robot {self._robot_a.serial}')

            # Obtain a coroutine for Cozmo A main function
            # Add the coroutine to the above coroutine list
            coroutines_for_cozmo.append(self._cozmo_a_main(self._robot_a))
        else:
            print('Unable to cast the role of Cozmo A')

            # If the current mode requires Cozmo A to be assigned
            # The two modes that require this are "only_a" and "both"
            if mode == OperationInteractMode.only_a or mode == OperationInteractMode.both:
                print('Refusing to continue because Cozmo A was not assigned')
                return
            else:
                print('Continuing without Cozmo A...')

        # If we assigned a robot instance to play Cozmo B...
        if self._robot_b is not None:
            print(f'The role of Cozmo B is being played by robot {self._robot_b.serial}')

            # Obtain a coroutine for Cozmo B main function
            # Add the coroutine to the above coroutine list
            coroutines_for_cozmo.append(self._cozmo_b_main(self._robot_b))
        else:
            print('Unable to cast the role of Cozmo B')

            # If the current mode requires Cozmo B to be assigned
            # The two modes that require this are "only_b" and "both"
            if mode == OperationInteractMode.only_b or mode == OperationInteractMode.both:
                print('Refusing to continue because Cozmo B was not assigned')
                return
            else:
                print('Continuing without Cozmo B...')

        # This wraps everything into one task object and schedules it on the loop
        asyncio.gather(
            # The operation watchdog (tells us when to call it quits)
            self._watchdog(),

            # Expand the main coroutines list into arguments
            *coroutines_for_cozmo,

            # Use the new loop
            loop=loop,
        )

        # Start the face trackers
        self._face_tracker_a.start()
        self._face_tracker_b.start()

        # Run the loop on this thread until it stops itself
        loop.run_forever()

        # Stop the face trackers
        self._face_tracker_a.stop()
        self._face_tracker_b.stop()

    async def _watchdog(self):
        """
        The operation watchdog.

        This looks out for the "kill switch" set by another thread. If it is
        set, we safe the robots and clean up gracefully.
        """

        while not self._stopping:
            # If the kill switch is set but we're not stopping yet
            if self._should_stop and not self._stopping:
                # We're stopping now
                self._stopping = True

                while True:
                    # TODO: We need to wait for both Cozmos to return to their chargers
                    # TODO: Either add another global boolean or upgrade self._swap to a three-state int (where zero means none active, etc.)
                    print(
                        'Drive to charger not implemented yet (_watchdog in cozmonaut/component/client/operation/__init__.py ...)')

                    # Yield control to other coroutines
                    await asyncio.sleep(0)

                # Politely ask the loop to stop
                loop = asyncio.get_event_loop()
                loop.call_soon(loop.stop)

            # Yield control to other coroutines
            await asyncio.sleep(0)

    async def _cozmo_a_main(self, robot: cozmo.robot.Robot):
        """
        Main function for Cozmo A.

        :param robot: The robot instance
        """

        # Register to receive camera frames from this robot
        robot.camera.add_event_handler(cozmo.robot.camera.EvtNewRawCameraImage, self._cozmo_a_on_new_raw_camera_image)

        # Schedule a battery watcher for this robot onto the loop
        coro_batt = asyncio.ensure_future(self._battery_watcher(robot))

        # Schedule a face watcher for this robot onto the loop
        coro_face = asyncio.ensure_future(self._face_watcher(robot))

        # Loop for Cozmo A
        while not self._stopping:
            # Yield control to other coroutines
            await asyncio.sleep(0)

        # Wait for face coroutine to stop
        await coro_face

        # Wait for battery coroutine to stop
        await coro_batt

    def _cozmo_a_on_new_raw_camera_image(self, evt: cozmo.robot.camera.EvtNewRawCameraImage, **kwargs):
        """
        Event handler for Cozmo A's raw camera image event.

        This function is not asynchronous, so go fast!

        :param evt: The event instance
        """

        # Send the image off to face tracker A
        self._face_tracker_a.update(evt.image)

    async def _cozmo_b_main(self, robot: cozmo.robot.Robot):
        """
        Main function for Cozmo B.

        :param robot: The robot instance
        """

        # Register to receive camera frames from this robot
        robot.camera.add_event_handler(cozmo.robot.camera.EvtNewRawCameraImage, self._cozmo_b_on_new_raw_camera_image)

        # Schedule a battery watcher for this robot onto the loop
        coro_batt = asyncio.ensure_future(self._battery_watcher(robot))

        # Schedule a face watcher for this robot onto the loop
        coro_face = asyncio.ensure_future(self._face_watcher(robot))

        # Loop for Cozmo B
        while not self._stopping:
            # Yield control to other coroutines
            await asyncio.sleep(0)

        # Wait for face coroutine to stop
        await coro_face

        # Wait for battery coroutine to stop
        await coro_batt

    # TODO: THE ACTIVE AND IDLE FUNCTIONS BELOW ARE NOT BEING CALLED YET

    async def _cozmo_common_active(self, robot: cozmo.robot.Robot):
        """
        The active subroutine for a Cozmo robot.

        This is where the waypoint loop code should go.

        :param robot: The robot instance
        """

        while not self._stopping:
            # TODO: Waypoint code

            # Yield control to other coroutines
            await asyncio.sleep(0)

    async def _cozmo_common_idle(self, robot: cozmo.robot.Robot):
        """
        The idle subroutine for a Cozmo robot.

        This is where the idling-on-charger code should go.

        :param robot: The robot instance
        """

        while not self._stopping:
            # TODO: This is code that needs to run while on the charger

            # Yield control to other coroutines
            await asyncio.sleep(0)

    def _cozmo_b_on_new_raw_camera_image(self, evt: cozmo.robot.camera.EvtNewRawCameraImage, **kwargs):
        """
        Event handler for Cozmo B's raw camera image event.

        This function is not asynchronous, so go fast!

        :param evt: The event instance
        """

        # Send the image off to face tracker B
        self._face_tracker_b.update(evt.image)

    async def _battery_watcher(self, robot: cozmo.robot.Robot):
        """
        A battery watcher for a Cozmo robot.

        This is responsible for watching the battery potential on a robot object
        and returning the robot to the charger.

        :param robot: The robot instance
        """

        while not self._stopping:
            # If battery potential is below the recommended "low" level
            if robot.battery_voltage < 3.5:
                # TODO: Drive the robot back to charge and swap the next one in
                print('THE BATTERY IS LOW')
                break

            # Yield control to other coroutines
            await asyncio.sleep(0)

    async def _face_watcher(self, robot: cozmo.robot.Robot):
        """
        A face watcher for a Cozmo robot.

        This is responsible for watching for faces

        :param robot:
        """

        # Enable color imaging on this robot's camera
        robot.camera.color_image_enabled = True
        robot.camera.image_stream_enabled = True

        while not self._stopping:
            # Yield control to other coroutines
            await asyncio.sleep(0)


# Do not leave the charger until we say it's okay
cozmo.robot.Robot.drive_off_charger_on_connect = False
