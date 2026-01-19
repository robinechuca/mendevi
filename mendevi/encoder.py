"""The encoding and decoding ffmpeg cmd."""

import functools
import math
import re
import subprocess
import typing

from mendevi.utils import best_profile


def decorator_pix_fmt(func: typing.Callable) -> typing.Callable:
    """Add a 8 bit pixel format conversion if required.

    Return general: None, vid_filter: str, cmd: list[str]
    """
    @functools.wraps(func)
    def decorated_func(**kwargs: dict) -> tuple[list[str], str, list[str]]:
        cmd = func(**kwargs)
        if (
            kwargs["pix_fmt"] != "yuv420p"
            and not support_pix_fmt(kwargs["encoder"], kwargs["pix_fmt"])
        ):
            return [], "format=yuv420p", cmd
        return [], "", cmd
    return decorated_func


def quality_to_rate(kwargs: dict[str]) -> int:
    """Return the absolute target bitrate in kbit/s.

    Based on https://twitch-overlay.fr/quelle-connexion-internet-choisir-pour-streamer-sur-twitch/
    and https://bitmovin.com/blog/video-bitrate-streaming-hls-dash/

    You can plot the bitrate with: mendevi plot mendevi.db -x bitrate -y psnr -f 'mode = "vbr"'

    The flow margin is taken to be twice as small and twice as large as the recommendations.
    """
    quality = kwargs["quality"]
    assert isinstance(quality, float), quality.__class__.__name__
    assert 0.0 <= quality <= 1.0, quality
    match (profile := best_profile(*kwargs["resolution"])):
        case "sd":
            mini, maxi = 400, 2100
        case "hd":
            mini, maxi = 1500, 6000
        case "fhd":
            mini, maxi = 3000, 9000
        case "uhd4k":
            mini, maxi = 10000, 51000
        case _:
            msg = f"please define a bitrate rule for the profile {profile}"
            raise NotImplementedError(msg)
    mini, maxi = mini // 2, maxi * 2  # apply margin
    mini, maxi = math.log10(float(mini)), math.log10(float(maxi))
    return round(10.0**(maxi-quality*(maxi-mini)))


@functools.cache
def support_pix_fmt(encoder: str, pix_fmt: str) -> bool:
    """Return True if the encoder supports the given pixel format."""
    cmd = ["ffmpeg", "-hide_banner", "-h", f"encoder={encoder}"]
    res: str = subprocess.run(cmd, check=True, capture_output=True).stdout.decode()
    return re.search(fr"\s{pix_fmt}\s", res) is not None


@decorator_pix_fmt
def _encode_av1_nvenc(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    general = [
        "av1_nvenc",
        "-gpu", "any",
        "-tune", "hq",
        "-preset", {"fast": "p2", "medium": "p4", "slow": "p6"}[kwargs["effort"]],
    ]
    if kwargs["mode"] == "vbr":
        return [
            *general,
            "-rc", "vbr",
            "-cq", str(round(1.0 + kwargs["quality"]*60.0)),  # [1, 63]
        ]
    rate = f"{quality_to_rate(kwargs)}k"
    return [
        *general,
        "-b:v", rate,
        "-minrate", rate,
        "-maxrate", rate,
        "-bufsize", rate,
        "-rc", "cbr",
    ]


def _encode_av1_vaapi(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    return _encode_vaapi("av1", **kwargs)


@decorator_pix_fmt
def _encode_h264_nvenc(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    general = [
        "h264_nvenc",
        "-gpu", "any",
        "-tune", "hq",
        "-preset", {"fast": "p2", "medium": "p4", "slow": "p6"}[kwargs["effort"]],
    ]
    if kwargs["mode"] == "vbr":
        return [
            *general,
            "-rc", "vbr",
            "-cq", str(round(1.0 + kwargs["quality"]*50.0)),  # [1, 51]
        ]
    rate = f"{quality_to_rate(kwargs)}k"
    return [
        *general,
        "-b:v", rate,
        "-minrate", rate,
        "-maxrate", rate,
        "-bufsize", rate,
        "-rc", "cbr",
    ]


def _encode_vaapi(codec: str, **kwargs: dict) -> tuple[list[str], str, list[str]]:
    """Return the ffmpeg arguments for the xxx_vaapi encoders."""
    # https://trac.ffmpeg.org/wiki/Hardware/VAAPI
    # https://www.ffmpeg.org/ffmpeg-codecs.html#VAAPI-encoders
    # see compatibility with "vainfo --all"
    pix_fmt = {
        "yuv420p": "nv12",
        "yuv420p10le": "p010",
    }[kwargs["pix_fmt"]]
    compression = {
        "slow": "1",
        "medium": "3",
        "fast": "6",
    }[kwargs["effort"]]
    device = ["-vaapi_device", "/dev/dri/renderD128"]
    vid_filter = f"format={pix_fmt},hwupload"
    general = [
        f"{codec}_vaapi",
        "-async_depth", str(kwargs["threads"]),
        "-compression_level", compression,
    ]
    if kwargs["mode"] == "vbr":
        return device, vid_filter, [
            *general,
            # "rc_mode", "CQP",  # very rare VBR support
            "-qp", str(round(1.0 + kwargs["quality"]*51.0)),  # [1, 52]
        ]
    rate = f"{quality_to_rate(kwargs)}k"
    return device, vid_filter, [
        *general,
        "-b:v", rate,
        "-minrate", rate,
        "-maxrate", rate,
        "-bufsize", rate,
        # "rc_mode", "CBR",
    ]


def _encode_h264_vaapi(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    return _encode_vaapi("h264", **kwargs)


@decorator_pix_fmt
def _encode_hevc_nvenc(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    general = [
        "hevc_nvenc",
        "-gpu", "any",
        "-tune", "hq",
        "-preset", {"fast": "p2", "medium": "p4", "slow": "p6"}[kwargs["effort"]],
    ]
    if kwargs["mode"] == "vbr":
        return [
            *general,
            "-rc", "vbr",
            "-cq", str(round(1.0 + kwargs["quality"]*50.0)),  # [1, 51]
        ]
    rate = f"{quality_to_rate(kwargs)}k"
    return [
        *general,
        "-b:v", rate,
        "-minrate", rate,
        "-maxrate", rate,
        "-bufsize", rate,
        "-rc", "cbr",
    ]


def _encode_hevc_vaapi(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    return _encode_vaapi("hevc", **kwargs)


@decorator_pix_fmt
def _encode_libaomav1(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    # find smart tiles blocs
    columns = math.ceil(math.sqrt(kwargs["threads"]))
    rows = math.ceil(kwargs["threads"]/columns)
    tiles = f"{columns}x{rows}"
    general = [
        "libaom-av1",
        "-cpu-used", {"fast": "7", "medium": "4", "slow": "1"}[kwargs["effort"]],
        "-tune", "ssim",
        "-threads", str(kwargs["threads"]), "-row-mt", "1", "-tiles", tiles,
        "-denoise-noise-level", "0",
    ]
    if kwargs["mode"] == "vbr":
        return [
            *general,
            "-crf", str(round(kwargs["quality"]*63.0)),  # in [0, 63]
        ]
    rate = f"{quality_to_rate(kwargs)}k"
    return [
        *general,
        "-b:v", rate,
        "-minrate", rate,
        "-maxrate", rate,
        "-bufsize", rate,
    ]


@decorator_pix_fmt
def _encode_libopenh264(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    general = [
        "libopenh264",
        "-profile", {
            "fast": "constrained_baseline", "medium": "main", "slow": "high",
        }[kwargs["effort"]],
        "-threads", str(kwargs["threads"]), "-slices", str(kwargs["threads"]),
        # "-slice_mode", "dyn",
    ]
    if kwargs["effort"] != "medium":
        general = [
            *general,
            "-loopfilter", {"slow": "1", "fast": "0"}[kwargs["effort"]],
        ]
    if kwargs["mode"] == "vbr":
        # https://patchwork.ffmpeg.org/project/ffmpeg/patch/
        # 1585926759-22569-1-git-send-email-linjie.fu@intel.com/
        quantization = str(round(1.0 + kwargs["quality"]*50.0))  # [1, 51]
        return [
            *general,
            "-qmin", quantization,
            "-qmax", quantization,
            "-rc_mode", "quality",
        ]
    rate = f"{quality_to_rate(kwargs)}k"
    return [
        *general,
        "-b:v", rate,
        "-minrate", rate,
        "-maxrate", rate,
        "-bufsize", rate,
        "-rc_mode", "bitrate",
    ]


@decorator_pix_fmt
def _encode_librav1e(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    # https://docs.rs/rav1e/latest/rav1e/config/struct.EncoderConfig.html
    if kwargs["mode"] == "vbr":
        quality = ["-qp", str(round(kwargs["quality"]*255))]  # not realy constant quality
    else:
        rate = f"{quality_to_rate(kwargs)}k"
        quality = ["-b:v", rate, "-minrate", rate, "-maxrate", rate]
    return [
        "librav1e",
        *quality,
        # speed in 0, 10, default 6
        "-speed", {"slow": "2", "medium": "6", "fast": "9"}[kwargs["effort"]],
        "-rav1e-params", (
            f"threads={kwargs['threads']}:tiles={kwargs['threads']}:photon-noise=0"
        ),
    ]


@decorator_pix_fmt
def _encode_libsvtav1(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    def libsvtav1_lp(threads: int) -> int:
        """Convert threads in parralel level."""
        # https://gitlab.com/AOMediaCodec/SVT-AV1/-/blob/master/Source/Lib/Globals/enc_handle.c#L613
        # lp=1 -> threads=1
        # lp=2 -> threads=2
        # lp=3 -> threads=8
        # lp=4 -> threads=12
        # lp=5 -> threads=16
        # lp=6 -> threads=20
        return {  # threads to lp
            1: 1,
            2: 2, 3: 2, 4: 2, 5: 2,
            6: 3, 7: 3, 8: 3, 9: 3, 10: 3,
            11: 4, 12: 4, 13: 4, 14: 4,
            15: 5, 16: 5, 17: 5,
        }.get(threads, 6)

    if kwargs["mode"] == "vbr":
        return [
            "libsvtav1",
            "-crf", str(round(kwargs["quality"]*63.0)),
            "-preset", {"slow": "4", "medium": "6", "fast": "8"}[kwargs["effort"]],
            # "-tune", "ssim",  # not same result as -svtav1-params tune=2
            "-svtav1-params", f"film-grain=0:lp={libsvtav1_lp(kwargs['threads'])}:tune=2",
        ]
    rate = f"{min(100_000, quality_to_rate(kwargs))}k"
    return [
        "libsvtav1",
        "-b:v", rate, "-minrate", rate, "-bufsize", rate,
        "-preset", {"slow": "4", "medium": "6", "fast": "8"}[kwargs["effort"]],
        "-tune", "ssim",  # -svtav1-params tune=2 not supported in cbr
        "-svtav1-params", f"rc=1:film-grain=0:lp={libsvtav1_lp(kwargs['threads'])}",
    ]


@decorator_pix_fmt
def _encode_libvpx_vp9(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    # https://trac.ffmpeg.org/wiki/Encode/VP9
    # https://wiki.webmproject.org/ffmpeg/vp9-encoding-guide
    # https://developers.google.com/media/vp9/settings
    if kwargs["mode"] == "vbr":
        quality = ["-crf", str(round(kwargs["quality"]*63.0)), "-b:v", "0"]
    else:
        rate = f"{quality_to_rate(kwargs)}k"
        quality = ["-b:v", rate, "-minrate", rate, "-maxrate", rate, "-lag-in-frames", "0"]
    return [
        "libvpx-vp9",
        *quality,
        # in [-16, 16]
        "-speed", {"slow": "-2", "medium": "1", "fast": "8"}[kwargs["effort"]],
        "-tune", "ssim",
        "-row-mt", "1", "-threads", str(kwargs["threads"]),
    ]


@decorator_pix_fmt
def _encode_libx264(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    if kwargs["mode"] == "vbr":
        quality = ["-crf", str(round(kwargs["quality"]*51.0, 1))]
    else:
        rate = f"{quality_to_rate(kwargs)}k"
        quality = [  # https://trac.ffmpeg.org/wiki/Encode/H.264#CBRConstantBitRate
            "-b:v", rate,
            "-minrate", rate,
            "-maxrate", rate,
            "-bufsize", rate,
            "-x264-params", "nal-hrd=cbr",
        ]
    return [  # https://ffmpeg.party/x264/
        "libx264",
        *quality,
        "-preset", {"fast": "veryfast", "medium": "medium", "slow": "veryslow"}[kwargs["effort"]],
        "-tune", "ssim",
        "-threads", str(kwargs["threads"]), "-thread_type", "frame",
    ]


@decorator_pix_fmt
def _encode_libx265(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    if kwargs["mode"] == "vbr":
        return [  # https://x265.readthedocs.io/en/master/cli.html
            "libx265",
            "-crf", str(round(kwargs["quality"]*51.0, 1)),
            "-preset", kwargs["effort"],
            "-tune", "ssim",
            "-x265-params",
            (
                f"frame-threads={kwargs['threads']}:"
                f"pools={kwargs['threads']}:"
                f"wpp={1 if kwargs['threads'] != 1 else 0}"
            ),
        ]
    rate = quality_to_rate(kwargs)
    return [  # https://x265.readthedocs.io/en/master/cli.html
        "libx265",
        "-b:v", f"{rate}k",
        "-preset", {"fast": "veryfast", "medium": "medium", "slow": "veryslow"}[kwargs["effort"]],
        "-tune", "ssim",
        "-x265-params",
        (
            f"vbv-maxrate={rate}:vbv-bufsize={rate}:"
            f"frame-threads={kwargs['threads']}:"
            f"pools={kwargs['threads']}:"
            f"wpp={1 if kwargs['threads'] != 1 else 0}"
        ),
    ]


def _encode_vp9_vaapi(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    return _encode_vaapi("vp9", **kwargs)


@decorator_pix_fmt
def _encode_vvc(**kwargs: dict) -> list[str]:
    """Return the ffmpeg arguments."""
    # https://github.com/fraunhoferhhi/vvenc/wiki/FFmpeg-Integration
    if kwargs["mode"] == "vbr":
        quality = ["-qp", str(round(kwargs["quality"]*63.0))]
    else:
        rate = quality_to_rate(kwargs)
        quality = ["-b:v", f"{rate}k", "-maxrate", f"{round(1.5*rate)+1}k"]
    bit = int(re.search(r"(?P<bit>\d+)le", kwargs["pix_fmt"] + "8le")["bit"])
    return [
        "vvc",
        *quality,
        "-preset", kwargs["effort"],
        "-qpa", "1",
        "-vvenc-params", f"internalbitdepth={bit}",
        "-threads", str(kwargs["threads"]),
    ]
