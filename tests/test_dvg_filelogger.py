#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PyTest

pytest --cov-report term-missing --cov=src -vv
coverage html
start htmlcov/index.html
"""
# pylint: disable=missing-function-docstring

import os
import unittest
import time
from pathlib import Path

from dvg_pyqt_filelogger import FileLogger

counter = 0


class TestAll(unittest.TestCase):
    def test(self):
        fn = "foobar.txt"
        encoding = "utf-8"
        mode = "a"
        time_to_sleep_in_sec = 2

        if Path(fn).is_file():
            os.remove(fn)

        def write_header():
            log.write("Header\n")

        def write_data():
            global counter
            log.write(f"{counter}\n")
            counter += 1

        log = FileLogger(
            write_header_function=write_header,
            write_data_function=write_data,
            encoding=encoding,
        )

        log.start_recording()
        log.update(fn, mode)  # Creates file, writes header and data "0"

        # ASSERT
        self.assertEqual(log.is_recording(), True)

        time.sleep(time_to_sleep_in_sec)
        elapsed = log.elapsed()
        pretty_elapsed = log.pretty_elapsed()

        # ASSERT
        self.assertAlmostEqual(elapsed, time_to_sleep_in_sec, places=1)
        self.assertEqual(pretty_elapsed, "0:00:02")

        log.update(fn, mode)  # Writes data "1"
        log.flush()
        log.update(fn, mode)  # Writes data "2"
        log.stop_recording()
        log.update(fn, mode)  # Closes file

        # ASSERT
        self.assertEqual(log.is_recording(), False)

        log.record(True)  # Start recording
        log.update(fn, mode)  # Reopens file, writes header and data "3"
        log.record(False)  # Stop recording
        log.update(fn, mode)  # Closes file

        # Read the contents of the written file
        with open(file=fn, mode="r", encoding=encoding) as written_file:
            file_contents = written_file.read()

        # ASSERT
        self.assertEqual(file_contents, "Header\n0\n1\n2\nHeader\n3\n")

        # Remove the temporary file
        os.remove(fn)


if __name__ == "__main__":
    unittest.main()
