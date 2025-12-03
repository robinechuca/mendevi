"""Allow to handle ffmpeg command line."""

import pathlib
import shlex


class CmdFFMPEG:
    """Allow easy manipulation of a complete ffmpeg expression.

    ffmpeg -y -hide_banner -loglevel verbose

    Attributes
    ----------
    decode : list[str]
        The options between -c:v and -i (read and write).
    vid_filter : str
        The filter string after -vf (read and write).
    general : list[str]
        The options immediately after ffmpeg and immediately before the decoder (read and write).
    video : pathlib.Path
        The input video path (readonly).
    encode : list[str]
        The encoder name and options after -c:v (read and write).

    """

    def __init__(
        self,
        video: pathlib.Path | str,
        general: list[str] | str | None = None,
        decode: list[str] | str | None = None,
        vid_filter: str = "",
        encode: list[str] | str | None = None,
    ) -> None:
        """Initialise the ffmpeg cmd.

        Parameters
        ----------
        video : pathlike
            The input video path.
        general : list[str], str, optional
            The options immediately after ffmpeg and immediately before the decoder.
        decode : list[str], str, optional
            The options between -c:v and -i.
        vid_filter : str, optional
            The filter string after -vf.
        encode: list[str], str, optional
            The encoder name and options after -c:v.

        """
        video = pathlib.Path(video).expanduser()
        self._video = video
        self._general = self._decode = self._vid_filter = self._encode = None  # initialisation

        self.general = general  # setter
        self.decode = decode
        self.vid_filter = vid_filter
        self.encode = encode

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
    def vid_filter(self) -> str:
        """Return the filter string after -vf."""
        return self._filter

    @vid_filter.setter
    def vid_filter(self, vid_filter: str) -> None:
        """Update the filter string after -vf."""
        assert isinstance(vid_filter, str), vid_filter.__class__.__name__
        self._vid_filter = vid_filter

    @property
    def general(self) -> list[str]:
        """Return the options immediately after ffmpeg and immediately before the decoder."""
        if self._general is None:
            return ["-y", "-log_verbose"]
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
        yield from ("-f", "null", "-")

    def __str__(self) -> str:
        """Return the full shell cmd.

        Examples
        --------
        >>> from mendevi.cmd import CmdFFMPEG
        >>> print(CmdFFMPEG(video="src.mp4"))
        ffmpeg -y -log_verbose -i src.mp4 -f null -
        >>>

        """
        return " ".join(map(shlex.quote, self))
