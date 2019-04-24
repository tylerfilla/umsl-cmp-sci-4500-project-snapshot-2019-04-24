#!/usr/bin/env python3

#
# Cozmonaut
# Copyright 2019 The Cozmonaut Contributors
#

import asyncio
import threading

import cozmo
import cv2
import dlib
import face_recognition
import numpy

# The camera frame counter
frame_counter = 0

# Open the face classifier
face_classifier = cv2.CascadeClassifier('haarcascade_frontalface_alt.xml')

# The outstanding face trackers
face_trackers = {}

# Identities assigned to outstanding face trackers
face_tracker_identities = {}

# The next face tracker ID to assign
next_tracker_id = 0

# Encodings of all known faces
known_face_encodings = []

# Names of all known faces
known_face_names = []


def recognize(image, tracker_id):
    """
    Perform face recognition on the ID'd tracker.

    @param image The face image in OpenCV BGR format
    @param tracker_id The target tracker
    """

    global face_trackers
    global face_tracker_identities
    global known_face_encodings
    global known_face_names

    # Convert to RGB
    image_rgb = image[:, :, ::-1]

    # Find tighter bounds on the face
    locations = face_recognition.face_locations(image_rgb)
    encodings = face_recognition.face_encodings(image_rgb, locations)

    if len(encodings) != 1:
        print('Failed to recognize face! Untracking...')

        # Kill the tracker so maybe we can get a better look
        del face_trackers[tracker_id]
        return

    # First and only encoding
    encoding = encodings[0]

    # Compare against known faces
    matches = face_recognition.compare_faces(known_face_encodings, encoding)

    # Get name associated with first match
    if True in matches:
        print('This is a known face!')

        first_match_index = matches.index(True)

        # Identify the face tracker
        face_tracker_identities[tracker_id] = known_face_names[first_match_index]

        return

    print('Hmm... Never seen this face before!')
    known_face_encodings.append(encoding)
    known_face_names.append(f'{tracker_id}')
    face_tracker_identities[tracker_id] = f'{tracker_id}'


def on_new_raw_camera_image(evt, **kwargs):
    """
    Handler for camera frames.

    This algorithm is heavily inspired by this script:
    https://github.com/gdiepen/face-recognition/blob/master/track multiple faces/demo - track multiple faces.py
    """

    global frame_counter
    global face_classifier
    global face_trackers
    global face_tracker_identities
    global next_tracker_id

    # Increment frame counter
    frame_counter += 1

    # Wrap the frame into a numpy array for OpenCV
    frame = numpy.array(evt.image)

    # Convert from RGB to BGR
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    # IDs of trackers that need pruning because faces have left us
    doomed_tracker_ids = []

    # Loop through all outstanding trackers
    for tracker_id in face_trackers.keys():
        # Update the current tracker position
        tracker_quality = face_trackers[tracker_id].update(frame)

        # Doom the trackers with low quality tracks
        if tracker_quality < 7:
            doomed_tracker_ids.append(tracker_id)

    # Prune the doomed trackers
    for tracker_id in doomed_tracker_ids:
        face_trackers.pop(tracker_id, None)

    # Every five frames, run a detection
    if frame_counter % 5 == 0:
        # Convert frame to grayscale for face detection
        frame_grayscale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect all faces in the frame
        faces = face_classifier.detectMultiScale(frame_grayscale, 1.3, 5)

        # Loop through bounding boxes of detected faces
        for face_box in faces:
            # Face box coordinates
            fb_l = int(face_box[0])  # left of face box
            fb_r = int(face_box[0] + face_box[2])  # right of face box
            fb_t = int(face_box[1])  # top of face box
            fb_b = int(face_box[1] + face_box[3])  # bottom of face box

            # Find the center of the bounding box
            # We'll compare this with the trackers below
            face_center_x = face_box[0] + face_box[2] / 2  # left (0) plus half width (2)
            face_center_y = face_box[1] + face_box[3] / 2  # top (1) plus half height (3)

            # The ID of the matching outstanding tracker
            # If we cannot make a match, then we have seen a new face
            face_id_match = None

            # Loop through all outstanding trackers
            for tracker_id in face_trackers.keys():
                # Get the current tracker position
                tracker_box = face_trackers[tracker_id].get_position()

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
                if face_center_x < tb_l or face_center_x > tb_r:
                    continue
                if face_center_y < tb_t or face_center_y > tb_b:
                    continue

                # Next, reject on (b)
                if tracker_center_x < fb_l or tracker_center_x > fb_r:
                    continue
                if tracker_center_y < fb_t or tracker_center_y > fb_b:
                    continue

                # If neither (a) or (b) was rejected, we have match. Hooray!
                face_id_match = tracker_id
                break

            # If no tracker match was found
            if face_id_match is None:
                print('Detected a new face! Recognizing...')

                # Create a dlib correlation tracker
                # These are supposedly pretty sturdy...
                new_tracker = dlib.correlation_tracker()

                # Get next available tracker ID
                # FIXME: For now, we don't reuse them
                tracker_id = next_tracker_id
                next_tracker_id += 1

                # Map the new tracker in
                face_trackers[tracker_id] = new_tracker

                # Add some padding to the face rectangle
                fb_l -= 10
                fb_t -= 20
                fb_r += 10
                fb_b += 20

                # Start tracking the new face in full color
                new_tracker.start_track(frame, dlib.rectangle(fb_l, fb_t, fb_r, fb_b))

                # Spin up a thread to recognize the person
                # TODO: Maybe we should periodically try to re-recognize the person
                thread = threading.Thread(target=recognize, args=(frame[fb_t:fb_b, fb_l:fb_r], tracker_id))
                thread.start()

                # FIXME: Diagnostic
                cv2.imshow(f'Tracker {tracker_id}', frame[fb_t:fb_b, fb_l:fb_r])

    # Upscale the frame before annotating it
    frame = cv2.pyrUp(frame)

    # Loop through all outstanding trackers
    # This time we're just drawing our rectangles
    for tracker_id in face_trackers.keys():
        # Get the current tracker position
        tracker_box = face_trackers[tracker_id].get_position()

        # Tracker box coordinates
        tb_l = int(tracker_box.left())  # left of tracker box
        tb_r = int(tracker_box.left() + tracker_box.width())  # right of tracker box
        tb_t = int(tracker_box.top())  # top of tracker box
        tb_b = int(tracker_box.top() + tracker_box.height())  # bottom of tracker box

        # Draw the rectangle
        cv2.rectangle(frame, (2 * tb_l, 2 * tb_t), (2 * tb_r, 2 * tb_b), (255, 0, 0))

        # If the track has a recognized identity
        if tracker_id in face_tracker_identities.keys():
            identity = face_tracker_identities[tracker_id]

            # Print identity
            cv2.putText(frame, f'ID {identity}', (2 * tb_l, 2 * tb_b), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 0), 2)
        else:
            # Print wait message
            cv2.putText(frame, 'Recognizing...', (2 * tb_l, 2 * tb_b), cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 0), 2)

    # Show the annotated frame
    # TODO: Remove this in production
    cv2.imshow('Output', frame)
    if cv2.waitKey(1) == ord('q'):
        exit(0)


async def connection_main(conn: cozmo.conn.CozmoConnection):
    """
    The main function for a Cozmo SDK connection.
    """

    # Wait for the connected robot to become ready
    robot: cozmo.robot.Robot = await conn.wait_for_robot()

    # Enable color imaging on the robot
    robot.camera.color_image_enabled = True
    robot.camera.image_stream_enabled = True

    # Register event handler for camera frames
    robot.camera.add_event_handler(cozmo.robot.camera.EvtNewRawCameraImage, on_new_raw_camera_image)

    # TODO: Real robot code replaces this loop
    while True:
        await asyncio.sleep(0)


if __name__ == '__main__':
    # Do not automatically drive off the charger
    cozmo.robot.Robot.drive_off_charger_on_connect = False

    # Get an event loop for this thread
    loop = asyncio.get_event_loop()

    # Connect to Cozmo SDK on this loop
    # The Cozmo SDK will run the loop for a little bit to establish the connection
    conn = cozmo.connect_on_loop(loop)

    # Schedule our main connection coroutine on the event loop
    main_task = asyncio.ensure_future(connection_main(conn))

    # Run the event loop until the main connection function is done
    loop.run_until_complete(main_task)
