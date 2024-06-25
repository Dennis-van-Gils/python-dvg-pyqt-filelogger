#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provides class `FileLogger()`: A PyQt/PySide interface to handle logging data
to a file particularly well suited for multithreaded programs.

Example usage
-------------

The following are snippets of code, not a full program.

.. code-block:: python

    from qtpy import QtWidgets as QtWid
    from dvg_pyqt_filelogger import FileLogger

    # Main/GUI thread
    # ---------------

    class MainWindow(QtWid.QWidget):
        def __init__(
            self,
            log: FileLogger,
            parent=None,
            **kwargs
        ):
            super().__init__(parent, **kwargs)

            # Create a record button
            self.record_button = QtWid.QPushButton("Click to start recording to file")
            self.record_button.setCheckable(True)
            self.record_button.clicked.connect(lambda state: log.record(state))

    class YourDataGeneratingDevice:
        reading_1 = 0.0

    device = YourDataGeneratingDevice()

    def write_header_to_log():
        log.write("elapsed [s]\treading_1\n")

    def write_data_to_log():
        log.write(f"{log.elapsed():.3f}\t{device.reading_1:.4f}\n")

    log = FileLogger(
        write_header_function=write_header_to_log,
        write_data_function=write_data_to_log
    )

    log.signal_recording_started.connect(
        lambda filepath: window.record_button.setText(
            f"Recording to file: {filepath}"
        )
    )
    log.signal_recording_stopped.connect(
        lambda: window.record_button.setText(
            "Click to start recording to file"
        )
    )

    window = MainWindow(log)

    # Data acquisition and/or logging thread
    # --------------------------------------

    # New data got acquired
    device.reading_1 = 20.3

    # Must be called whenever new data has become available
    log.update()
"""
__author__ = "Dennis van Gils"
__authoremail__ = "vangils.dennis@gmail.com"
__url__ = "https://github.com/Dennis-van-Gils/python-dvg-pyqt-filelogger"
__date__ = "25-06-2024"
__version__ = "1.4.0"

from typing import Union, Callable, IO
from io import IOBase
from pathlib import Path
import datetime

from qtpy import QtCore
from qtpy.QtCore import Signal, Slot  # type: ignore
import numpy as np

from dvg_debug_functions import print_fancy_traceback as pft


class FileLogger(QtCore.QObject):
    """Handles logging data to a file particularly well suited for multithreaded
    programs where one thread is writing data to the log and the other thread
    (the main/GUI thread) requests starting and stopping of the log, e.g.,
    by the user pressing a button.

    The methods ``start_recording()``, ``stop_recording()`` and ``record(bool)``
    can be directly called from the main/GUI thread.

    In the logging thread you repeatedly need to call ``update()``. This method
    takes cares of the state machine behind ``FileLogger`` and will perform the
    appropiate action, such as creating a file on disk, creating the header or
    writing new data to the log.

    Args:
        write_header_function (``Callable``, optional):
            Reference to a function that contains your specific code to write a
            header to the log file. This will get called during ``update()``.

            The passed function can contain calls to this object's member
            methods ``write()``, ``elapsed()`` and ``np_savetxt()``.

            Default: ``None``

        write_data_function (``Callable``, optional):
            Reference to a function that contains your specific code to write
            new data to the log file. This will get called during ``update()``.

            The passed function can contain calls to this object's member
            methods ``write()``, ``elapsed()`` and ``np_savetxt()``.

            Default: ``None``

        encoding (``str``, optional):
            Encoding to be used for the log file.

            Default: "utf-8"

    NOTE:
        This class lacks a mutex and is hence not threadsafe from the get-go.
        As long as ``update()`` is being called from inside another mutex, such
        as a data-acquisition mutex for instance, it is safe.

    NOTE:
        By design the code in this class will continue on when exceptions occur.
        They are reported to the command line.
    """

    signal_recording_started = Signal(str)
    """Emitted whenever a new recording has started. Useful for, e.g., updating
    text of a record button.

    Returns:
        The filepath (``str``) of the newly created log file.
    """

    signal_recording_stopped = Signal(Path)
    """Emitted whenever the recording has stopped. Useful for, e.g., updating
    text of a record button.

    Returns:
        The filepath (``pathlib.Path()``) of the newly created log file. You
        could use this to, e.g., automatically navigate to the log in the file
        explorer or ask the user for a 'save to' destination.
    """

    def __init__(
        self,
        write_header_function: Union[Callable, None] = None,
        write_data_function: Union[Callable, None] = None,
        encoding: str = "utf-8",
    ):
        super().__init__(parent=None)

        self._write_header_function = write_header_function
        self._write_data_function = write_data_function

        self._filepath: Union[Path, None] = None
        self._filehandle: Union[IO, None] = None
        self._mode = "a"
        self._encoding = encoding

        self._timer = QtCore.QElapsedTimer()
        self._start = False
        self._stop = False
        self._is_recording = False

    def __del__(self):
        if isinstance(self._filehandle, IOBase) and self._is_recording:
            self._filehandle.close()

    def set_write_header_function(self, write_header_function: Callable):
        """Will change the parameter ``write_header_function`` as originally
        passed during instantiation to this new callable.

        Args:
            write_header_function (``Callable``):
                Reference to a function that contains your specific code to
                write a header to the log file. This will get called during
                ``update()``.

                The passed function can contain calls to this object's member
                methods ``write()``, ``elapsed()`` and ``np_savetxt()``.
        """
        self._write_header_function = write_header_function

    def set_write_data_function(self, write_data_function: Callable):
        """Will change the parameter ``write_data_function`` as originally
        passed during instantiation to this new callable.

        Args:
            write_data_function (``Callable``):
                Reference to a function that contains your specific code to
                write new data to the log file. This will get called during
                ``update()``.

                The passed function can contain calls to this object's member
                methods ``write()``, ``elapsed()`` and ``np_savetxt()``.
        """
        self._write_data_function = write_data_function

    @Slot(bool)
    def record(self, state: bool = True):
        """Start or stop recording as given by argument `state`. Can be called
        from any thread."""
        if state:
            self.start_recording()
        else:
            self.stop_recording()

    @Slot()
    def start_recording(self):
        """Start recording. Can be called from any thread."""
        self._start = True
        self._stop = False

    @Slot()
    def stop_recording(self):
        """Stop recording. Can be called from any thread."""
        self._start = False
        self._stop = True

    def update(self, filepath: str = "", mode: str = "a"):
        """This method will have to get called repeatedly, presumably in the
        thread where logging is required, e.g., the data-generation thread.
        This method takes cares of the state machine behind ``FileLogger`` and
        will perform the appropriate action, such as creating a file on disk,
        creating the header or writing new data to the log.

        Args:
            filepath (``str``):
                Location of the log file in case it has to be created or opened
                for write access.

                Default: ``"{yyMMdd_HHmmss}.txt"`` denoting the current date and time.

            mode (``str``, optional):
                Mode in which the log file is to be opened, see ``open()`` for
                more details. Most common options:

                    ``w``: Open for writing, truncating the file first.

                    ``a``: Open for writing, appending to the end of the
                           file if it exists.

                Defaults: ``a``
        """
        if self._start:
            if filepath == "":
                filepath = (
                    QtCore.QDateTime.currentDateTime().toString("yyMMdd_HHmmss")
                    + ".txt"
                )

            self._filepath = Path(filepath)
            self._mode = mode

            # Reset flags
            self._start = False
            self._stop = False

            if self._create_log():
                self.signal_recording_started.emit(filepath)
                self._is_recording = True
                if self._write_header_function is not None:
                    self._write_header_function()
                self._timer.start()

            else:
                self._is_recording = False

        if self._is_recording and self._stop:
            self.signal_recording_stopped.emit(self._filepath)
            self._timer.invalidate()
            self.close()

        if self._is_recording:
            if self._write_data_function is not None:
                self._write_data_function()

    def _create_log(self) -> bool:
        """Create/open the log file and keep the file handle open.

        Returns True if successful, False otherwise.
        """
        if not isinstance(self._filepath, Path):
            pft("Invalid file path.")
            return False

        try:
            self._filehandle = open(
                file=self._filepath,
                mode=self._mode,
                encoding=self._encoding,
            )
        except Exception as err:  # pylint: disable=broad-except
            pft(err, 3)
            return False

        return True

    def write(self, data: Union[str, bytes]) -> bool:
        """Write binary or ASCII data to the currently opened log file.

        By design any exceptions occurring in this method will not terminate the
        execution, but it will report the error to the command line and continue
        on instead.

        Returns True if successful, False otherwise.
        """
        if not isinstance(self._filehandle, IOBase):
            pft("Invalid file handle.")
            return False

        try:
            self._filehandle.write(data)
        except Exception as err:  # pylint: disable=broad-except
            pft(err, 3)
            return False

        return True

    def np_savetxt(self, *args, **kwargs) -> bool:
        """Write 1D or 2D array_like data to the currently opened log file. This
        method passes all arguments directly to ``numpy.savetxt()``, see
        https://numpy.org/doc/stable/reference/generated/numpy.savetxt.html.
        This method outperforms ``FileLogger.write()``, especially when large
        chunks of 2D data are passed (my test shows 8x faster).

        By design any exceptions occurring in this method will not terminate the
        execution, but it will report the error to the command line and continue
        on instead.

        Returns True if successful, False otherwise.
        """
        if not isinstance(self._filehandle, IOBase):
            pft("Invalid file handle.")
            return False

        try:
            np.savetxt(self._filehandle, *args, **kwargs)
        except Exception as err:  # pylint: disable=broad-except
            pft(err, 3)
            return False

        return True

    @Slot()
    def flush(self):
        """Force-flush the contents in the OS buffer to file as soon as
        possible. Do not call repeatedly, because it causes overhead.
        """
        if isinstance(self._filehandle, IOBase):
            self._filehandle.flush()

    def close(self):
        """Close the log file."""
        if isinstance(self._filehandle, IOBase) and self._is_recording:
            self._filehandle.close()

        self._start = False
        self._stop = False
        self._is_recording = False

    def get_filepath(self) -> Union[Path, None]:
        """Return the filepath (``pathlib.Path`` | ``None``) of the log."""
        return self._filepath

    def is_recording(self) -> bool:
        """Is the log currently set to recording?"""
        return self._is_recording

    def elapsed(self) -> float:
        """Return the time in seconds (``float``) since start of recording."""
        return self._timer.elapsed() / 1e3

    def pretty_elapsed(self) -> str:
        """Return the time as "h:mm:ss" (``str``) since start of recording."""
        return str(datetime.timedelta(seconds=int(self.elapsed())))
