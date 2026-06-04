"""Get the power consumption of as usb plugded ADEC WATTS wattmeters."""

import math
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
    >>> import time
    >>> from mendevi.measures.adec import ADECWattmeter
    >>> with ADECWattmeter() as usage:
    ...     time.sleep(1)
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
        no_fail : bool, default=True
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
            assert isinstance(port, "/dev/ttyUSB0"), port.__class__.__name__

        self._stop_flag = False
        self.port = port
        self.res: dict | None = {"dt": [], "u_rms": [], "i_rms": [], "p_eff": []} if port else None

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
            msg = f"the frame checksum {checksum} doese not match the excpected checksum {data[-1]}"
            raise ValueError(msg)
        data = data[24:-1]

        # extract cumulated current and cummulated efficient powers
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
        if len(data := port.read(nbr)) == nbr:
            return data
        msg = f"failed to read on device {port.port!r}"
        raise TimeoutError(msg)

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
        if self.res is None:
            return
        # open the port
        with serial.Serial(
            self.port,
            baudrate=BAUD,
            timeout=1.0,
            dsrdtr=False,  # already default values, juste to be shure
            rtscts=False,  # already default values, juste to be shure
        ) as port:
            port.dtr = port.rts = False  # like in adecwatts c code
            port.reset_input_buffer()
            self._find_header(port)  # reject the first frame
            self._find_header(port)  # and the second one as well
            while not self._stop_flag:
                self._find_header(port)
                for lbl, value in self._read_frame(port).items():
                    self.res[lbl].append(value)

    def __enter__(self) -> dict:
        """Start to measure.

        Returns
        -------
        Consumption: dict[str]
            * 'dt': The duration of the sample measure (in s).
            * 'u_rms': The voltage of the 3 phases (in V).
            * 'i_rms': The current of each channal (in A).
            * 'p_eff': The efficient power of each channal (in W).

        """
        self.start()
        return self.res

    def __exit__(self, *_: object) -> None:
        """Stop the measure and update the dictionary returnd by __enter__."""
        self._stop_flag = True
        self.join()  # wait the last update of self.run


if __name__ == "__main__":
    with ADECWattmeter() as usage:
        time.sleep(10)
    import pprint
    pprint.pprint(usage)
