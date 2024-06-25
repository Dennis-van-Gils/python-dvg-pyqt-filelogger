#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyTest

pytest --cov-report term-missing --cov=src -vv
coverage html
start htmlcov/index.html
"""
# pylint: disable=missing-function-docstring, global-statement

import os
import sys
import time
import io
from pathlib import Path

import unittest
from unittest import mock

from qtpy import QtCore
from qtpy.QtCore import Slot  # type: ignore

import numpy as np
from dvg_pyqt_filelogger import FileLogger

# Constants
FN = "foobar.txt"
ENCODING = "utf-8"

# Globals
counter = 0
signal_reply = ""


def reset_test():
    if Path(FN).is_file():
        os.remove(FN)

    global counter
    counter = 0


@Slot(str)
def process_signal_recording_started(filepath: str):
    global signal_reply
    signal_reply = f"Recording started: {filepath}"


@Slot(Path)
def process_signal_recording_stopped(filepath: Path):
    global signal_reply
    signal_reply = f"Recording stopped: {str(filepath)}"


class TestAll(unittest.TestCase):
    def test_regular(self):
        reset_test()

        def write_header():
            log.write("Header\n")

        def write_data():
            global counter
            log.write(f"{counter}\n")
            counter += 1

        def write_data_numpy():
            x = np.arange(0, 4)
            y = np.power(x, 2)
            np_data = np.column_stack((x, y))
            log.np_savetxt(np_data, "%.0f\t%.0f")

        log = FileLogger(
            write_header_function=write_header,
            write_data_function=write_data,
            encoding=ENCODING,
        )

        log.start_recording()
        log.update(FN)  # Creates file, writes header and data "0"

        # ASSERT
        self.assertEqual(log.is_recording(), True)

        time_to_sleep_in_sec = 2
        time.sleep(time_to_sleep_in_sec)
        elapsed = log.elapsed()
        pretty_elapsed = log.pretty_elapsed()

        # ASSERT
        self.assertAlmostEqual(elapsed, time_to_sleep_in_sec, places=1)
        self.assertEqual(pretty_elapsed, "0:00:02")

        log.update(FN)  # Writes data "1"
        log.flush()
        log.update(FN)  # Writes data "2"
        log.stop_recording()
        log.update(FN)  # Closes file

        # ASSERT
        self.assertEqual(log.is_recording(), False)

        log.set_write_header_function(write_header)
        log.set_write_data_function(write_data_numpy)

        log.record(True)  # Start recording
        log.update(FN)  # Reopens file, writes header and numpy data
        log.record(False)  # Stop recording
        log.update(FN)  # Closes file

        # Read the contents of the written file
        with open(file=FN, mode="r", encoding=ENCODING) as written_file:
            file_contents = written_file.read()

        # ASSERT
        self.assertEqual(
            file_contents,
            "Header\n0\n1\n2\nHeader\n0\t0\n1\t1\n2\t4\n3\t9\n",
        )

        log.close()
        os.remove(FN)

    def test_premature_quit_while_recording(self):
        reset_test()

        def write_header():
            log.write("Header\n")  # noqa: F821

        def write_data():
            global counter
            log.write(f"{counter}\n")  # noqa: F821
            counter += 1

        log = FileLogger(
            write_header_function=write_header,
            write_data_function=write_data,
            encoding=ENCODING,
        )

        log.start_recording()
        log.update(FN)  # Creates file, writes header and data "0"

        # Force delete object
        del log

        # Read the contents of the written file
        with open(file=FN, mode="r", encoding=ENCODING) as written_file:
            file_contents = written_file.read()

        # ASSERT
        self.assertEqual(file_contents, "Header\n0\n")

        os.remove(FN)

    def test_file_access_errors(self):
        reset_test()

        def write_header():
            log.write("Header\n")

        def write_data():
            global counter
            log.write(f"{counter}\n")
            counter += 1

        log = FileLogger(
            write_header_function=write_header,
            write_data_function=write_data,
            encoding=ENCODING,
        )

        # Catch terminal output
        with mock.patch("sys.stdout", new=io.StringIO()) as fake_stdout:

            # Trigger a 'FileNotFoundError' exception during log creation by
            # using the incorrect mode "r" (read-only).
            # The exception will be printed to the terminal via
            # `dvg_debug_functions.print_fancy_traceback()`.
            # ---------------------------------------------------------

            log.start_recording()
            log.update(FN, "r")  # Open non-existing file as read-only

            # ASSERT
            fake_stdout.flush()
            stdout_lines = fake_stdout.getvalue().split("\n")
            self.assertEqual(
                stdout_lines[-2].startswith("\x1b[1;31mFileNotFoundError:"),
                True,
            )

            # Correctly create file now
            log.close()
            log.start_recording()
            log.update(FN)  # Creates file, writes header and data "0"
            log.flush()

            # Trigger a 'UnsupportedOperation' exception during log data
            # writing by reopening the log file as read-only behind the scenes.
            # The exception will be printed to the terminal via
            # `dvg_debug_functions.print_fancy_traceback()`.
            log._filehandle.close()
            log._filehandle = open(file=FN, mode="r", encoding=ENCODING)

            log.update(FN)

            # ASSERT
            fake_stdout.flush()
            stdout_lines = fake_stdout.getvalue().split("\n")
            self.assertEqual(
                stdout_lines[-2].startswith("\x1b[1;31mUnsupportedOperation:"),
                True,
            )

        log.close()
        os.remove(FN)

    def test_illegal_np_savetxt(self):
        reset_test()

        def write_illegal_data_numpy():
            # Trigger Exception:
            # "ValueError: fmt has wrong number of % formats"
            log.np_savetxt([0], "%.0f\t%.0f")

        log = FileLogger(
            write_data_function=write_illegal_data_numpy,
            encoding=ENCODING,
        )

        # Catch terminal output
        with mock.patch("sys.stdout", new=io.StringIO()) as fake_stdout:

            log.start_recording()
            log.update(FN)

            # ASSERT
            fake_stdout.flush()
            stdout_lines = fake_stdout.getvalue().split("\n")
            self.assertEqual(
                stdout_lines[-2].startswith("\x1b[1;31mValueError:"),
                True,
            )

        log.close()
        os.remove(FN)

    def test_autofilename(self):
        reset_test()

        log = FileLogger(encoding=ENCODING)
        log.start_recording()
        log.update()
        log.close()

        filepath = log.get_filepath()
        print(f"Auto generated filename: {filepath}")

        # Remove the temporary file
        if filepath is not None:
            os.remove(filepath)

    def test_signals(self):
        reset_test()

        # QtWidgets are not needed for pytest and will fail a standard GitHub
        # Workflow pytest. Use QCoreApplication instead.
        # (X) app = QtWidgets.QApplication(sys.argv)
        app = QtCore.QCoreApplication(sys.argv)

        log = FileLogger(encoding=ENCODING)
        log.signal_recording_started.connect(process_signal_recording_started)
        log.signal_recording_stopped.connect(process_signal_recording_stopped)

        log.start_recording()
        log.update(FN)
        app.processEvents()

        # ASSERT
        self.assertEqual(signal_reply, f"Recording started: {FN}")

        log.stop_recording()
        log.update()
        app.processEvents()

        # ASSERT
        self.assertEqual(signal_reply, f"Recording stopped: {FN}")

        log.close()
        os.remove(FN)


if __name__ == "__main__":
    unittest.main()
