"""Allow to handle ffmpeg command line."""

import io
import pathlib
import re
import shlex
import subprocess
import typing

import cutcutcodec
import tqdm

from mendevi.measures import Activity


class CmdFFMPEG:
    """Allow easy manipulation of a complete ffmpeg expression.

    ffmpeg -y -hide_banner -loglevel verbose

    Attributes
    ----------
    general : list[str]
        The options immediately after ffmpeg and immediately before the decoder (read and write).
    decode : list[str]
        The options between -c:v and -i (read and write).
    video : pathlib.Path
        The input video path (readonly).
    vid_filter : str
        The filter string after -vf (read and write).
    encode : list[str]
        The encoder name and options after -c:v (read and write).
    output : list[str]
        The final arguments of the ffmpeg cmd (read and write).

    """

    def __init__(
        self,
        video: pathlib.Path | str,
        **kwargs: dict[str],
    ) -> None:
        """Initialise the ffmpeg cmd.

        Parameters
        ----------
        video : pathlike
            The input video path.
        **kwargs: dict
            See above.
        general : list[str], str, optional
            The options immediately after ffmpeg and immediately before the decoder.
        decode : list[str], str, optional
            The options between ``-c:v`` and ``-i``.
        vid_filter : str, optional
            The filter string after ``-vf``.
        encode: list[str], str, optional
            The encoder name and options after ``-c:v``.
        output: list[str], str, default="-f null -"
            The final arguments of the ffmpeg command, after the encoder description.

        """
        # initialisation
        video = pathlib.Path(video).expanduser()
        self._video = video
        self._general = self._decode = self._vid_filter = self._encode = self._output = None

        # parse and check, using setter
        self.general = kwargs.get("general")
        self.decode = kwargs.get("decode")
        self.vid_filter = kwargs.get("vid_filter", "")
        self.encode = kwargs.get("encode")
        self.output = kwargs.get("output")

    def copy(self) -> typing.Self:
        """Return an independant copy of self."""
        return CmdFFMPEG(
            video=self.video,
            general=self.general,
            decode=self.decode,
            vid_filter=self.vid_filter,
            encode=self.encode,
            output=self.output,
        )

    @property
    def decode(self) -> list[str]:
        """Return the options between -c:v and -i."""
        return self._decode.copy()

    @decode.setter
    def decode(self, decode: list[str] | str | None) -> None:
        """Update the options between -c:v and -i."""
        match decode:
            case None:
                self._decode = []
            case str():
                self._decode = shlex.split(decode)
            case list():
                assert all(isinstance(cmd, str) for cmd in decode), decode
                self._decode = decode.copy()
            case _:
                msg = f"'decode' has to be None, str or list, not {decode.__class__.__name__}"
                raise TypeError(msg)

    @property
    def encode(self) -> list[str]:
        """Return the encoder name and options after -c:v."""
        return self._encode.copy()

    @encode.setter
    def encode(self, encode: list[str] | str | None) -> None:
        """Update the encoder name and options after -c:v."""
        match encode:
            case None:
                self._encode = []
            case str():
                self._encode = shlex.split(encode)
            case list():
                assert all(isinstance(cmd, str) for cmd in encode), encode
                self._encode = encode.copy()
            case _:
                msg = f"'encode' has to be None, str or list, not {encode.__class__.__name__}"
                raise TypeError(msg)

    @property
    def general(self) -> list[str]:
        """Return the options immediately after ffmpeg and immediately before the decoder."""
        if self._general is None:
            return ["-hide_banner", "-y", "-loglevel", "verbose"]
        return self._general.copy()

    @general.setter
    def general(self, general: list[str] | str | None) -> None:
        """Update the options immediately after ffmpeg and immediately before the decoder."""
        match general:
            case None:
                self._general = None
            case str():
                self._general = shlex.split(general)
            case list():
                assert all(isinstance(cmd, str) for cmd in general), general
                self._general = general.copy()
            case _:
                msg = f"'general' has to be None, str or list, not {general.__class__.__name__}"
                raise TypeError(msg)

    @property
    def output(self) -> list[str]:
        """Return the final arguments of the ffmpeg command, after the encoder."""
        return self._output.copy()

    @output.setter
    def output(self, output: list[str] | str | None) -> None:
        """Update the final arguments of the ffmpeg command, after the encoder."""
        match output:
            case None:
                self._output = ["-f", "null", "-"]
            case str():
                self._output = shlex.split(output)
            case list():
                assert all(isinstance(cmd, str) for cmd in output), output
                self._output = output.copy()
            case _:
                msg = f"'output' has to be None, str or list, not {output.__class__.__name__}"
                raise TypeError(msg)

    def run(self, cmd: list[str] | str | None = None) -> tuple[str, dict[str]]:
        """Execute the command and return the stderr output.

        If a cmd is provided, it is used instead of self.
        """
        # verification
        if cmd is None:
            cmd = list(self)
        elif isinstance(cmd, str):
            cmd = shlex.split(cmd)
        assert isinstance(cmd, list), cmd.__class__.__name__

        # preparation of progress bar
        try:
            total = round(float(cutcutcodec.get_duration_video(self.video)), 2)
        except cutcutcodec.core.exceptions.MissingStreamError:
            total = None
        load = tqdm.tqdm(
            dynamic_ncols=True,
            leave=False,
            smoothing=1e-6,
            total=total,
            unit="s",
        )

        # utilitaries
        def read_lines(stream: io.BufferedReader) -> bytes:
            r"""Yield each line (separated by \n or \r)."""
            line: bytes = b""
            while buff := stream.read(64):
                *prev, line = re.split(br"\n|\r", line + buff)
                yield from prev
            if line:
                yield line

        # run command
        output: bytes = b""
        with Activity() as activity, subprocess.Popen(cmd, stderr=subprocess.PIPE) as process:
            for line in read_lines(process.stderr):
                if (
                    match := re.search(
                        br"time=(?P<h>\d+):(?P<m>\d{1,2}):(?P<s>\d{1,2}\.\d*)", line,
                    )
                ) is None:
                    output += line + b"\n"
                else:
                    elapsed = round(
                        3600.0*float(match["h"]) + 60.0*float(match["m"]) + float(match["s"]), 2,
                    )
                    load.total = None if load.total is None else max(load.total, elapsed)
                    load.update(elapsed-load.n)
        load.close()
        if process.returncode:
            msg = f"failed to execute {cmd}:\n{output}"
            raise RuntimeError(msg)
        return output.decode("utf-8"), activity

    @property
    def vid_filter(self) -> str:
        """Return the filter string after -vf."""
        return self._vid_filter

    @vid_filter.setter
    def vid_filter(self, vid_filter: str) -> None:
        """Update the filter string after -vf."""
        assert isinstance(vid_filter, str), vid_filter.__class__.__name__
        self._vid_filter = vid_filter

    @property
    def video(self) -> pathlib.Path:
        """Return the input video path."""
        return self._video

    def __iter__(self) -> str:
        """Iterate over each parameter to be compatible with list(self)."""
        yield "ffmpeg"
        yield from self.general
        if self._decode:
            yield "-c:v"
            yield from self._decode
        yield "-i"
        yield str(self._video)
        if self._vid_filter:
            yield "-vf"
            yield self._vid_filter
        if self._encode:
            yield "-c:v"
            yield from self._encode
        yield from self._output

    def __str__(self) -> str:
        """Return the full shell cmd.

        Examples
        --------
        >>> from mendevi.cmd import CmdFFMPEG
        >>> print(CmdFFMPEG(video="src.mp4"))
        ffmpeg -hide_banner -y -loglevel verbose -i src.mp4 -f null -
        >>>

        """
        return " ".join(map(shlex.quote, self))
