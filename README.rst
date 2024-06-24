.. image:: https://img.shields.io/pypi/v/dvg-pyqt-filelogger
    :target: https://pypi.org/project/dvg-pyqt-filelogger
.. image:: https://img.shields.io/pypi/pyversions/dvg-pyqt-filelogger
    :target: https://pypi.org/project/dvg-pyqt-filelogger
.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black
.. image:: https://img.shields.io/badge/License-MIT-purple.svg
    :target: https://github.com/Dennis-van-Gils/python-dvg-pyqt-filelogger/blob/master/LICENSE.txt

DvG_PyQt_FileLogger
===================
*Provides class `FileLogger()`: A PyQt/PySide interface to handle logging data
to a file particularly well suited for multithreaded programs.*

Supports PyQt5, PyQt6, PySide2 and PySide6.

- Github: https://github.com/Dennis-van-Gils/python-dvg-pyqt-filelogger
- PyPI: https://pypi.org/project/dvg-pyqt-filelogger

Installation::

    pip install dvg-pyqt-filelogger

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

API
===


Class FileLogger
----------------

.. code-block:: python

    FileLogger(
        write_header_function: Callable | None = None,
        write_data_function: Callable | None = None,
        encoding: str = "utf-8",
    )

.. Note:: Inherits from: ``PySide6.QtCore.QObject``

    Handles logging data to a file particularly well suited for multithreaded
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

    NOTE:
        This class lacks a mutex and is hence not threadsafe from the get-go.
        As long as ``update()`` is being called from inside another mutex, such
        as a data-acquisition mutex for instance, it is safe.

    NOTE:
        By design the code in this class will continue on when exceptions occur.
        They are reported to the command line.

    Signals:
        ``signal_recording_started (str)``:
            Emitted whenever a new recording has started. Useful for, e.g.,
            updating text of a record button.

            Returns:
                The filepath (``str``) of the newly created log file.

            Type:
                ``PySide6.QtCore.Signal()``

        ``signal_recording_stopped (pathlib.Path)``:
            Emitted whenever the recording has stopped. Useful for, e.g., updating
            text of a record button.

            Returns:
                The filepath as (``pathlib.Path()``) of the newly created log file.
                You could use this to, e.g., automatically navigate to the log in
                the file explorer or ask the user for a 'save to' destination.

            Type:
                ``PySide6.QtCore.Signal()``

    Methods:
        * ``set_write_header_function(write_header_function: Callable)``
            Will change the parameter ``write_header_function`` as originally
            passed during instantiation to this new callable.

            Args:
                write_header_function (``Callable``):
                    Reference to a function that contains your specific code to
                    write a header to the log file. This will get called during
                    ``update()``.

                    The passed function can contain calls to this object's member
                    methods ``write()``, ``elapsed()`` and ``np_savetxt()``.

        * ``set_write_data_function(write_data_function: Callable)``
            Will change the parameter ``write_data_function`` as originally
            passed during instantiation to this new callable.

            Args:
                write_data_function (``Callable``):
                    Reference to a function that contains your specific code to
                    write new data to the log file. This will get called during
                    ``update()``.

                    The passed function can contain calls to this object's member
                    methods ``write()``, ``elapsed()`` and ``np_savetxt()``.

        * ``record(state: bool = True)``
            Start or stop recording as given by argument `state`. Can be called
            from any thread.

        * ``start_recording()``
            Start recording. Can be called from any thread.

        * ``stop_recording()``
            Stop recording. Can be called from any thread.

        * ``update(filepath: str = "", mode: str = "a")``
            This method will have to get called repeatedly, presumably in the
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

                        ``a``: Open for writing, appending to the end of the file if it exists.

                    Defaults: ``a``

        * ``write(data: AnyStr) -> bool``
            Write binary or ASCII data to the currently opened log file.

            By design any exceptions occurring in this method will not terminate the
            execution, but it will report the error to the command line and continue
            on instead.

            Returns True if successful, False otherwise.

        * ``np_savetxt(*args, **kwargs) -> bool``
            Write 1D or 2D array_like data to the currently opened log file. This
            method passes all arguments directly to ``numpy.savetxt()``, see
            https://numpy.org/doc/stable/reference/generated/numpy.savetxt.html.
            This method outperforms ``FileLogger.write()``, especially when large
            chunks of 2D data are passed (my test shows 8x faster).

            By design any exceptions occurring in this method will not terminate the
            execution, but it will report the error to the command line and continue
            on instead.

            Returns True if successful, False otherwise.

        * ``flush()``
            Force-flush the contents in the OS buffer to file as soon as
            possible. Do not call repeatedly, because it causes overhead.

        * ``close()``
            Close the log file.

        * ``is_recording() -> bool``
            Is the log currently set to recording?

        * ``elapsed() -> float``
            Return the time in seconds (``float``) since start of recording.

        * ``pretty_elapsed() -> str``
            Return the time as "h:mm:ss" (``str``) since start of recording.
