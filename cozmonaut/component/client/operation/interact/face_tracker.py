#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import time
from concurrent.futures import Future
from concurrent.futures.thread import ThreadPoolExecutor
from threading import Thread, Lock
from typing import List, Tuple, Dict

import PIL.Image
import cv2
import dlib
import numpy
from pkg_resources import resource_filename

# The face detector
_detector = dlib.get_frontal_face_detector()

# The face pose predictor
_predictor_serialized_file_name = resource_filename(__name__, "data/shape_predictor_68_face_landmarks.dat")
_predictor = dlib.shape_predictor(_predictor_serialized_file_name)

# The face recognition model
_model_file_serialized_file_name = resource_filename(__name__, "data/dlib_face_recognition_resnet_model_v1.dat")
_model = dlib.face_recognition_model_v1(_model_file_serialized_file_name)


class DetectedFace:
    """
    Info about a face that has been detected and tracked.
    """

    def __init__(self):
        self._index: int = 0
        self._coords: Tuple[int, int, int, int] = (0, 0, 0, 0)

    @property
    def index(self) -> int:
        """
        :return: The track index
        """
        return self._index

    @index.setter
    def index(self, value):
        """
        :param value: The track index
        """
        self._index = value

    @property
    def coords(self) -> Tuple[int, int, int, int]:
        """
        :return: The face coordinates (left, top, right, bottom)
        """
        return self._coords

    @coords.setter
    def coords(self, value: Tuple[int, int, int, int]):
        """
        :param value: The face coordinates (left, top, right, bottom)
        """
        self._coords = value


class RecognizedFace(DetectedFace):
    """
    Info about a face that has been recognized.

    All recognized faces are detected faces.
    """

    def __init__(self):
        super().__init__()
        self._fid: int = 0
        self._ident: Tuple[int, ...] = ()

    @property
    def fid(self) -> int:
        """
        :return: The face ID
        """
        return self._fid

    @fid.setter
    def fid(self, fid: int):
        """
        :param fid: The face ID
        """
        self._fid = fid

    @property
    def ident(self) -> Tuple[int, ...]:
        """
        :return: The face identity (128-dimensional vector embedding)
        """
        return self._ident

    @ident.setter
    def ident(self, value: Tuple[int, ...]):
        """
        :param value: The face identity (128-dimensional vector embedding)
        """
        self._ident = value


class FaceTracker:
    """
    A tracker for faces in a stream of images.
    """

    def __init__(self):
        # The face identities
        self._identities: Dict[int, Tuple[float, ...]] = {}
        self._identities_lock = Lock()

        # The detection thread
        # We only need one of these, as each detection operation finds all faces in a frame
        # It would make no sense to parallelize detection across multiple frames simultaneously
        self._thread_detection = None

        # A kill switch for the detection loop
        self._detection_kill = False
        self._detection_kill_lock = Lock()

        # The recognition thread pool executor
        # A thread pool executor is a step above a simple thread pool, as it has a built-in work queue
        # This allows us to submit work orders for recognizing individual faces without worrying about scheduling
        self._thread_pool_recognizers = ThreadPoolExecutor(max_workers=3)  # FIXME: Allow this to be set by the user

        # The individual face trackers
        self._trackers = {}
        self._tracker_images = {}
        self._trackers_lock = Lock()
        self._next_tracker_id = 0

        # The latest frame pending detection
        self._pending_detection = None
        self._pending_detection_flag = False
        self._pending_detection_lock = Lock()

        # The list of "next track" futures
        self._next_track_futures = []
        self._next_track_futures_lock = Lock()

    def add_identity(self, fid: int, ident: Tuple[float, ...]):
        """
        Add a new face identity to the tracker.

        :param fid: The face ID
        :param ident: The face identity (128-dimensional vector)
        """

        # Map the identity
        self._identities_lock.acquire()
        self._identities[fid] = ident
        self._identities_lock.release()

    def remove_identity(self, fid: int):
        """
        Remove a face identity from the tracker.

        :param fid: The face ID
        """

        # Unmap the identity
        self._identities_lock.acquire()
        del self._identities[fid]
        self._identities_lock.release()

    def start(self):
        """
        Start the face detector.
        """

        # Lock, clear, and unlock the detection loop kill switch
        self._detection_kill_lock.acquire()
        self._detection_kill = False
        self._detection_kill_lock.release()

        # Start the detection thread
        self._thread_detection = Thread(target=self._thread_detection_main)
        self._thread_detection.start()

    def stop(self):
        """
        Stop the face detector
        """

        # Lock, set, and unlock the detection loop kill switch
        self._detection_kill_lock.acquire()
        self._detection_kill = True
        self._detection_kill_lock.release()

        # Wait for the detection thread to die
        self._thread_detection.join()

    def update(self, image: PIL.Image):
        """
        Update with the next image in the stream.

        :param image: The next frame
        """

        # Convert to numpy matrix
        image_np = numpy.array(image)

        # Prepare the image
        # TODO: Factor this out
        image_np = cv2.pyrUp(image_np)
        image_np = cv2.medianBlur(image_np, 3)

        # Acquire trackers lock
        self._trackers_lock.acquire()

        # IDs of trackers that need pruning because faces have left us
        doomed_tracker_ids = []

        # For each registered tracker...
        for tracker_id in self._trackers.keys():
            # ...update it with the image!
            quality = self._trackers[tracker_id].update(image_np)
            self._tracker_images[tracker_id] = image_np

            # Doom the trackers with low quality tracks
            if quality < 7:  # TODO: Allow user to set this
                doomed_tracker_ids.append(tracker_id)

        # Prune the doomed trackers
        for tracker_id in doomed_tracker_ids:
            self._trackers.pop(tracker_id, None)
            self._tracker_images.pop(tracker_id, None)

        # Release trackers lock
        self._trackers_lock.release()

        # Acquire pending detection frame lock
        self._pending_detection_lock.acquire()

        # Update pending detection frame
        self._pending_detection = image
        self._pending_detection_flag = True

        # Release pending detection frame lock
        self._pending_detection_lock.release()

    def next_track(self):
        """
        Obtain a future on the next initiated face track. This does not notify
        of any preexisting tracks.

        :return: A future for the next DetectedFace object
        """

        # Create a future for the detection (they say we're not supposed to call this)
        # We will keep one copy and send another to the caller
        # Later on, after we track a new face, we'll complete the future
        future = Future()

        # Lock, append the future to, and unlock the next track futures list
        self._next_track_futures_lock.acquire()
        self._next_track_futures.append(future)
        self._next_track_futures_lock.release()

        return future

    def recognize(self, index: int):
        """
        Obtain a future on the recognition of a face track.

        :param index: The track index
        """

        # Send off a request to recognize the face in this track
        return self._thread_pool_recognizers.submit(self._recognize_main, index)

    def _thread_detection_main(self):
        """
        Main function for detecting faces.

        This runs all the time, and it picks up the latest image.
        """

        # The latest frame
        frame: PIL.Image = None

        while True:
            # Acquire lock for kill switch
            self._detection_kill_lock.acquire()

            # Test kill switch
            if self._detection_kill:
                # Unlock it and die
                self._detection_kill_lock.release()
                break

            # Kill switch is not set, so unlock it
            self._detection_kill_lock.release()

            # Lock pending frame
            self._pending_detection_lock.acquire()

            # If a pending frame is available
            if self._pending_detection_flag:
                # Save the frame
                frame = self._pending_detection

                # Clear pending frame slot
                # We've kept it for ourselves
                self._pending_detection = None
                self._pending_detection_flag = False

            # Unlock pending frame
            self._pending_detection_lock.release()

            # If we've got a frame to work with
            if frame is not None:
                # Use the image as a numpy matrix
                frame_np = numpy.array(frame)

                # Prepare the image
                # TODO: Factor this out
                frame_np = cv2.pyrUp(frame_np)
                frame_np = cv2.medianBlur(frame_np, 3)

                # Detect all faces in the image
                faces: List[dlib.rectangle] = _detector(frame_np, 1)

                # Go over all detected faces
                for face in faces:
                    # The ID of the matching outstanding tracker
                    # If we cannot make a match, then we have seen a new face (or at least a misplaced one)
                    face_id_match = None

                    # Acquire the trackers lock
                    self._trackers_lock.acquire()

                    # Loop through all outstanding trackers
                    for tracker_id in self._trackers.keys():
                        # Get the current tracker position
                        tracker_box = self._trackers[tracker_id].get_position()

                        # Tracker box coordinates
                        tb_l = int(tracker_box.left())  # left of tracker box
                        tb_r = int(tracker_box.left() + tracker_box.width())  # right of tracker box
                        tb_t = int(tracker_box.top())  # top of tracker box
                        tb_b = int(tracker_box.top() + tracker_box.height())  # bottom of track

                        # Find the center of the tracker box
                        tracker_center_x = tracker_box.left() + tracker_box.width() / 2
                        tracker_center_y = tracker_box.top() + tracker_box.height() / 2

                        # If the following two conditions hold, we have a match:
                        #  a) The face center is inside the tracker box
                        #  b) The tracker center is inside the face box

                        # Reject on (a) first
                        if face.center().x < tb_l or face.center().x > tb_r:
                            continue
                        if face.center().y < tb_t or face.center().y > tb_b:
                            continue

                        # Next, reject on (b)
                        if tracker_center_x < face.left() or tracker_center_x > face.right():
                            continue
                        if tracker_center_y < face.top() or tracker_center_y > face.bottom():
                            continue

                        # If neither (a) or (b) was rejected, we have match. Hooray!
                        face_id_match = tracker_id
                        break

                    # If no tracker match was found
                    if face_id_match is None:
                        # Create a dlib correlation tracker
                        # These are supposedly pretty sturdy...
                        new_tracker = dlib.correlation_tracker()

                        # Get next available tracker ID
                        # FIXME: For now, we don't reuse them (should we?)
                        tracker_id = self._next_tracker_id
                        self._next_tracker_id += 1

                        # Map the new tracker in
                        self._trackers[tracker_id] = new_tracker
                        self._tracker_images[tracker_id] = frame_np

                        # Add some padding to the face rectangle
                        # TODO: Make this slop configurable
                        track_left = face.left() - 10
                        track_top = face.top() - 20
                        track_right = face.right() + 10
                        track_bottom = face.bottom() + 20

                        # Start tracking the new face in full color
                        new_tracker.start_track(frame_np,
                                                dlib.rectangle(track_left, track_top, track_right, track_bottom))

                        # Info about the detected face
                        detected = DetectedFace()
                        detected.index = tracker_id
                        detected.coords = (track_left, track_top, track_right, track_bottom)

                        # Complete all the next track futures
                        self._next_track_futures_lock.acquire()
                        for future in self._next_track_futures:
                            future.set_result(detected)
                        self._next_track_futures.clear()
                        self._next_track_futures_lock.release()

                    # Release lock on trackers
                    self._trackers_lock.release()

            # Sleep for a bit
            time.sleep(0.5)

    def _recognize_main(self, index: int) -> RecognizedFace:
        """
        Main function for recognizing a face.

        This runs to completion on an as-needed basis given by a thread pool.
        """

        # Lock trackers list
        self._trackers_lock.acquire()

        # Query the latest face bounding box from the tracker
        position: dlib.rectangle = self._trackers[index].get_position()

        # Get the image that corresponds to this tracker
        image = self._tracker_images[index]

        # Unlock trackers list
        self._trackers_lock.release()

        # Predict 68 unique points on the face
        prediction = _predictor(image, dlib.rectangle(
            int(position.left()),
            int(position.top()),
            int(position.right()),
            int(position.bottom())
        ))

        # Compute the 128-dimensional vector embedding of the face
        ident = _model.compute_face_descriptor(image, prediction, 1)

        # Return info about the recognized face
        rec = RecognizedFace()
        rec.index = index
        rec.coords = position
        rec.fid = 10000  # TODO: Implement this
        rec.ident = ident
        return rec
