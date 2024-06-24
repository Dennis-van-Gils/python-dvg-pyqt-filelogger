#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test"""
# pylint: disable=missing-function-docstring

import os
import unittest

from dvg_pyqt_filelogger import FileLogger

counter = 0


class TestAll(unittest.TestCase):
    def test(self):

        # Create a temporary file for testing
        temp_file_path = "foobar.txt"
        encoding = "utf-8"

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
        log.update(
            temp_file_path, "a"
        )  # Creates file, writes header and data "0"
        log.update(temp_file_path, "a")  # Writes data "1"
        log.update(temp_file_path, "a")  # Writes data "2"
        log.stop_recording()
        log.update(temp_file_path, "a")  # Closes file

        # Read the contents of the written file
        with open(
            file=temp_file_path,
            mode="r",
            encoding=encoding,
        ) as written_file:
            file_contents = written_file.read()

        # Assert that the file contents match the expected message
        self.assertEqual(file_contents, "Header\n0\n1\n2\n")

        # Remove the temporary file
        os.remove(temp_file_path)


if __name__ == "__main__":
    unittest.main()
