#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import asyncio
import threading
from enum import Enum

import PIL.Image
import cozmo
import cv2

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
        # Start the face trackers
        self._face_tracker_a.start()
        self._face_tracker_b.start()

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

        loop = asyncio.new_event_loop()

        asyncio.gather(
            self._recorder(),
            self._face_thing(),
            loop=loop,
        )

        loop.run_forever()

        # Stop the face trackers
        self._face_tracker_a.stop()
        self._face_tracker_b.stop()

    async def _recorder(self):
        # Open first video capture device
        self._cap = cv2.VideoCapture(0)

        while not self._stopping:
            # Handle a frame
            await self._on_frame()

            # Yield control to other coroutines
            await asyncio.sleep(0)

        loop = asyncio.get_event_loop()
        loop.call_soon(loop.stop)

    async def _on_frame(self):
        # Get the next frame
        ret, frame = self._cap.read()

        # Convert to Cozmo format
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (320, 240))

        # Update tracker
        self._face_tracker_a.update(PIL.Image.fromarray(frame))

        # Preview the output
        cv2.imshow('Output', frame)

        # Poll window and stop on Q down
        if cv2.waitKey(1) == ord('q'):
            self._stopping = True

    async def _face_thing(self):
        while not self._stopping:
            # Wait for the next tracked face
            track = await asyncio.wrap_future(self._face_tracker_a.next_track())

            # TODO: Make Cozmo look at the face for social cue
            #   Hopefully we don't lose the track b/c motion blur, but I think I know a hack if we do

            await asyncio.sleep(0.25)  # Let motion blur settle down? Am I overestimating motion blur?

            # Request to recognize the face
            rec = await asyncio.wrap_future(self._face_tracker_a.recognize(track.index))

            # TODO: Greet the face if rec.fid is not negative one
            #  If rec.fid is negative one, then meet the new person and store a Base64 copy of rec.ident to the DB
            #  Don't forget to then add it to the trackers with tracker_a.add_identity and tracker_b.add_identity

            # Yield control to other coroutines
            await asyncio.sleep(0)

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
