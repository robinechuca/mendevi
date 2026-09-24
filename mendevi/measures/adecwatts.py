# Copyright (C) 2026 Robin Richard and Thomas Maugey and Anne-Cecile Orgerie
# SPDX-License-Identifier: GPL-3.0-or-later

"""Get the power consumption of as usb plugded ADEC WATTS wattmeters."""

import math
import queue
import struct
import threading
import time

import serial  # uv pip install pyserial
from serial.tools.list_ports import comports

HEADER: bytes = b"\xfe\xfd\xfc\xfb"  # comes from adecwatts c code 'read_device_values'
BAUD: int = 921600
STEP = 2.0**-32.0  # time counter step time


class ADECWattmeter(threading.Thread):
    """Extract the activity of a ADEC-WATTS wattmeter connected to serial usb port.

    Examples
    --------
    >>> from mendevi.measures.adecwatts import ADECWattmeter
    >>> with ADECWattmeter(no_fail=True) as usage:
    ...     pass
    ...
    >>>

    """

    def __init__(self, port: str | None = None, *, no_fail: bool = False) -> None:
        """Initialize the usage context.

        Parameters
        ----------
        port : str, default=autodetect
            The port to listen on. In gerenal it is "/dev/ttyUSB0".
            By default, it is autodetected using :py:meth`guess_port`.
        no_fail : bool, default=False
            If False, raise RuntimeError if it fails to get the ADEC measure.
            Otherwise (if True), return None instead of failing.

        """
        assert isinstance(no_fail, bool), no_fail

        super().__init__(daemon=True)

        if port is None:
            try:
                port = self.guess_port()
            except RuntimeError:
                if not no_fail:
                    raise
        else:
            assert isinstance(port, str), port.__class__.__name__

        self._signal_queue = queue.Queue()
        self._stop_flag = False
        self.port = port
        self.res: dict | None = {"ts": [], "u_rms": [], "i_rms": [], "p_eff": []} if port else None

    def _find_header(self, port: serial.Serial) -> float:
        """Read the stream until it encounters the header."""
        buffer: bytes = self._read_port(port, len(HEADER))
        while buffer != HEADER:
            buffer = buffer[1:] + self._read_port(port)
        return time.time()

    def _read_frame(self, port: serial.Serial) -> dict[str]:
        """Read a full frame after the header has been consumed."""
        # get frame informations from header
        data = self._read_port(port, 24)
        (
            frame_size,  # payload size (uint16 le)
            _,  # frame id number (uint16 le)
            delta,  # delay since previous frame, unit 2**-32 s (uint32)
            samplecount,  # number of accumulated sample (uint32)
            u1s_cum,  # sum of the u1**2 tensions (float32)
            u2s_cum,  # sum of the u2**2 tensions (float32)
            u3s_cum,  # sum of the u3**2 tensions (float32)
        ) = struct.unpack("<HHIIfff", data)
        # print(frame_size, frame_id, delta, u1s_cum, u2s_cum, u3s_cum)
        if frame_size < 30:
            msg = f"the frame size is absurde {frame_size}"
            raise ValueError(msg)
        if samplecount == 0:
            msg = "the first frame (samplecount=0) has to be rejected"
            raise ValueError(msg)

        # frame crc verification
        data += self._read_port(port, frame_size-21)  # contains crc
        checksum = data[0]  # faster than functools.reduce(operator.xor, data[:-1]), ...
        for item in data[1:-1]:
            checksum ^= item
        if checksum != data[-1]:
            msg = f"the frame checksum {checksum} does not match the expected checksum {data[-1]}"
            raise ValueError(msg)
        data = data[24:-1]

        # extract cumulated current and cumulative efficient powers
        is_cum, p_cum = [], []  # each cumulative square current an efficient power for each channel
        while data:
            is_cum.extend(struct.unpack("<ffffff", data[:24]))
            p_cum.extend(struct.unpack("<ffffff", data[24:48]))
            data = data[48:]

        # final normalization
        tot = float(samplecount)
        return {
            "dt": float(delta)*STEP,
            "u_rms": [math.sqrt(u1s_cum / tot), math.sqrt(u2s_cum / tot), math.sqrt(u3s_cum / tot)],
            "i_rms": [math.sqrt(is_cum_ / tot) for is_cum_ in is_cum],
            "p_eff": [p_cum_ / tot for p_cum_ in p_cum],
        }

    @staticmethod
    def _read_port(port: serial.Serial, nbr: int = 1) -> bytes:
        """Raise an exception if the port is not readable."""
        try:
            if len(data := port.read(nbr)) == nbr:
                return data
        # device reports readiness to read but returned no data...
        except serial.SerialException as err:
            time.sleep(0.1)  # wait for better stabilisation
            msg = f"device {port.port!r} busy"
            raise ValueError(msg) from err
        msg = f"failed to read on device {port.port!r}, data to short {len(data)} vs {nbr}"
        raise TimeoutError(msg)

    def _yield_frames(self, port: serial.Serial) -> dict[str]:
        """Like _read_frame but skip the corrupted one."""
        n_corrupted_max = 5
        errors = [None]
        while True:
            for _ in range(n_corrupted_max):
                try:
                    self._find_header(port)
                    yield self._read_frame(port)
                except ValueError as err:  # reject the first frame
                    errors[0] = err
                else:
                    break
            else:
                msg = f"{n_corrupted_max} corrupted packets recovered subsequently"
                raise RuntimeError(msg) from errors.pop()

    @staticmethod
    def guess_port() -> str:
        """Automaticaly find the port in the list of reachable ports."""
        known_vid_pid = [
            (0x10C4, 0xEA60),  # CP210x
            (0x1A86, 0x7523),  # CH340
            (0x0403, 0x6001),  # FTDI FT232
            (0x0403, 0x6011),  # FTDI FT4232
        ]
        ports = comports()
        if len(  # first selection
            selection := {
                port.device for port in comports()
                if any(port.vid == vid and port.pid == pid for vid, pid in known_vid_pid)
            } or {p.device for p in ports},
        ) == 1:
            return selection.pop()
        # fallback on default values
        if not (selection := {p for p in selection if "USB" in p or "ACM" in p}):
            msg = "no usb port found for the wattmeter, please provide it"
            raise RuntimeError(msg)
        return min(selection)

    def run(self) -> None:
        """Perform the measures."""
        is_warming = True
        if self.res is None:
            self._signal_queue.put(None)
            return
        # reset the measures
        for data in self.res.values():
            data.clear()
        try:
            # open the port
            with serial.Serial(
                self.port,
                baudrate=BAUD,
                timeout=1.0,
                dsrdtr=False,  # already default values, just to be shure
                rtscts=False,  # already default values, just to be shure
            ) as port:
                port.dtr = port.rts = False  # like in adecwatts c code
                port.reset_input_buffer()  # can trigger other daemons doing stuff on this port
                self.res["ts"].append(time.time())
                for frame in self._yield_frames(port):
                    if is_warming:
                        is_warming = False
                        self._signal_queue.put(None)  # send signal catched by .__enter__()
                    self.res["ts"].append(self.res["ts"][-1] + frame["dt"])  # increment timestamp
                    for lbl in ("u_rms", "i_rms", "p_eff"):
                        self.res[lbl].append(frame[lbl])
                    if self._stop_flag:
                        break
        except Exception as err:
            self._signal_queue.put(err)
            raise

    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'ts': The absolute timestamps between 2 measurements (in s), shape (n+1,).
            * 'u_rms': The voltage of the 3 phases (in V), shape (n, 3).
            * 'i_rms': The current of each channal (in A), shape (n, c).
            * 'p_eff': The efficient power of each channal (in W), shape (n, c).

        """
        self.start()
        if (err := self._signal_queue.get()) is not None:  # wait until the first frame is catched
            raise err
        return self.res

    def __exit__(self, *_: object) -> None:
        """Stop the measure and update the dictionary returnd by __enter__."""
        self._stop_flag = True
        self.join()  # wait the last update of self.run
        try:
            err = self._signal_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            raise err
