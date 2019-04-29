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

        # TODO: This is where we should read the database into the trackers

        # FIXME: Remove this later; this is Tyler's face encoding
        tyler_face = (
            -0.103433,
            0.0713784,
            0.0813356,
            -0.0747395,
            -0.157589,
            -0.0386992,
            -0.0319699,
            -0.00274016,
            0.0867231,
            -0.0220311,
            0.242471,
            0.0148122,
            -0.252416,
            -0.0551133,
            -0.0037139,
            0.0990293,
            -0.113765,
            -0.0226992,
            -0.0938466,
            -0.0400318,
            0.126524,
            0.102942,
            0.0550079,
            0.0616467,
            -0.145211,
            -0.260875,
            -0.105383,
            -0.0524487,
            0.00731247,
            -0.135143,
            0.0509941,
            0.124918,
            -0.109638,
            -0.0350157,
            0.0340424,
            0.0950269,
            -0.0593138,
            -0.0289018,
            0.215726,
            -0.0228096,
            -0.149361,
            0.0423131,
            0.0110523,
            0.264083,
            0.194999,
            0.0382402,
            0.0235397,
            -0.0508239,
            0.100998,
            -0.320135,
            0.0635357,
            0.134587,
            0.0839489,
            0.050831,
            0.0836643,
            -0.125788,
            0.0253968,
            0.212677,
            -0.222989,
            0.0768562,
            -0.0297501,
            -0.215015,
            -0.0410392,
            -0.110664,
            0.166501,
            0.0996042,
            -0.129823,
            -0.148502,
            0.147683,
            -0.152009,
            -0.145286,
            0.145061,
            -0.140681,
            -0.147379,
            -0.37368,
            0.0436715,
            0.353895,
            0.153631,
            -0.225468,
            0.0191243,
            -0.01694,
            0.0200662,
            0.0228013,
            0.0611707,
            -0.0946287,
            -0.0709029,
            -0.121012,
            0.0488099,
            0.17418,
            -0.0588228,
            -0.0645145,
            0.26763,
            0.092387,
            0.115437,
            0.0444944,
            0.0116651,
            -0.00945554,
            -0.0874052,
            -0.132031,
            0.0409098,
            0.0522451,
            -0.105967,
            -0.020343,
            0.127948,
            -0.15351,
            0.168118,
            -0.0352881,
            -0.045533,
            -0.0601219,
            -0.0499158,
            -0.139128,
            0.0365747,
            0.188973,
            -0.290735,
            0.218931,
            0.203897,
            0.0409592,
            0.125365,
            0.0873372,
            0.0437877,
            -0.0335225,
            -0.054352,
            -0.145829,
            -0.065083,
            0.144216,
            -0.0487921,
            0.0604078,
            0.0337079
        )

        # FIXME: Remove this
        self._face_tracker_a.add_identity(42, tyler_face)

        # Run the loop on this thread until it stops itself
        loop.run_forever()

        # TODO: This is where we should save from the trackers into the database

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

                # TODO: We need to drive both Cozmos back to their chargers, as the Ctrl+C or equivalent happened
                print('DRIVING TO CHARGER NOT IMPLEMENTED YET')

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
            # TODO: Swap back and forth between active and idle

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
            # TODO: Swap back and forth between active and idle (but opposite that of Cozmo A)

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
            # TODO: Is there any code for when we're on the charger? That would go here

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
                print('DRIVING TO CHARGER NOT YET IMPLEMENTED')
                print('SWAPPING THE COZMOS NOT YET IMPLEMENTED')
                break

            # Yield control to other coroutines
            await asyncio.sleep(0)

    async def _face_watcher(self, robot: cozmo.robot.Robot):
        """
        A face watcher for a Cozmo robot.

        This is responsible for watching for faces

        :param robot: The robot instance
        """

        # Enable color imaging on this robot's camera
        robot.camera.color_image_enabled = True
        robot.camera.image_stream_enabled = True

        # Pick the face tracker for this robot
        # Cozmo A gets tracker A and Cozmo B gets tracker B
        ft = None
        if robot == self._robot_a:
            ft = self._face_tracker_a
        elif robot == self._robot_b:
            ft = self._face_tracker_b

        while not self._stopping:
            # Wait for the next face tracked by the tracker
            track = await asyncio.wrap_future(ft.next_track())

            # TODO: Make Cozmo look at the face for social cue
            #   Hopefully we don't lose the track b/c motion blur, but I think I know a hack if we do

            await asyncio.sleep(0.25)  # TODO: Let motion blur settle down? Am I overestimating motion blur?

            # Request to recognize the face
            rec = await asyncio.wrap_future(ft.recognize(track.index))

            # TODO: Greet the face if rec.fid is not negative one
            #  If rec.fid is negative one, then meet the new person and store a Base64 copy of rec.ident to the DB
            #  Don't forget to then add it to the trackers with tracker_a.add_identity and tracker_b.add_identity

            # Yield control to other coroutines
            await asyncio.sleep(0)


# Do not leave the charger until we say it's okay
cozmo.robot.Robot.drive_off_charger_on_connect = False
