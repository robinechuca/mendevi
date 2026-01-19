"""Perform the metrics and video properties measures."""

import datetime
import logging
import pathlib
import sqlite3

import cutcutcodec
import numpy as np
import orjson
from context_verbose import Printer
from flufl.lock import Lock

from mendevi.database.serialize import list_to_binary
from mendevi.utils import compute_video_hash


def open_ro(database: pathlib.Path, conn: sqlite3.Connection | None) -> sqlite3.Connection:
    """Open a new conn if the previous one is not already opened."""
    if conn is None:
        conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=30)
        conn.row_factory = sqlite3.Row
    return conn


def _fill_vid_table(
    database: pathlib.Path,
    vid_id: bytes,
    video: pathlib.Path,
    conn: sqlite3.Connection | None = None,
    **kwargs: dict,
) -> sqlite3.Connection | None:
    """Complete the table t_vid_video."""
    # get actual informations
    conn = open_ro(database, conn)
    prop = conn.execute(
        "SELECT * FROM t_vid_video WHERE vid_id=?", (vid_id,),
    ).fetchone()
    prop = {} if prop is None else dict(prop)

    # missing fields
    fields = {
        "vid_codec",
        "vid_duration",
        "vid_eotf",
        "vid_fps",
        "vid_frames",
        "vid_gamut",
        "vid_height",
        "vid_name",
        "vid_pix_fmt",
        "vid_range",
        "vid_size",
        "vid_width",
        *(("vid_rms_sobel",) if kwargs["rms_sobel"] else ()),
        *(("vid_rms_time_diff",) if kwargs["rms_time_diff"] else ()),
        *(("vid_uvq",) if kwargs["uvq"] else ()),
    }
    fields -= {k for k, v in prop.items() if v is not None}
    if not fields:
        return conn
    conn.close()

    # fill missing fields
    pad = max(map(len, fields)) - 4
    with Printer(f"Get properties of {video.name}...", color="green") as prt:
        # basic fields
        for field in fields - {"vid_rms_sobel", "vid_rms_time_diff", "vid_uvq"}:
            prop[field] = _fill_vid_table_prop(field, prt, pad, video)

        # metric fields
        new_metrics = cutcutcodec.video_metrics(
            video,
            rms_sobel="vid_rms_sobel" in fields,
            rms_time_diff="vid_rms_time_diff" in fields,
            uvq="vid_uvq" in fields,
        )
        for metric in sorted(new_metrics):
            values = new_metrics[metric]
            prt.print(f"{metric:<{pad}}: {np.nanmean(values):.2f} +/- {np.nanstd(values):.2f}")
        prop |= {f"vid_{m}": list_to_binary(v) for m, v in new_metrics.items()}

    # update result
    fields = list(fields)  # to frozen order for sql request
    with (
        Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=600)),
        sqlite3.connect(database) as conn,
    ):
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO t_vid_video (vid_id) VALUES (?)", (vid_id,),
        )
        cursor.execute(
            (
                f"UPDATE t_vid_video SET {', '.join(f'{k}=?' for k in fields)} "
                "WHERE vid_id=?"
            ),
            [prop[k] for k in fields] + [vid_id],
        )
    return None


def _fill_vid_table_prop(field: str, prt: Printer, pad: int, video: pathlib.Path) -> object:
    """Help _fill_vid_table."""
    prop = None
    match field:
        case "vid_duration":
            prop = float(cutcutcodec.get_duration_video(video))
            prt.print(f"{'duration':<{pad}}: ", end="")
            prt.print_time(prop, print_headers=False)
        case "vid_fps":
            prop = float(cutcutcodec.get_rate_video(video))
            prt.print(f"{'fps':<{pad}}: {prop:.2f} Hz")
        case "vid_frames":
            header, info = cutcutcodec.core.analysis.ffprobe.get_slices_metadata(video)
            header, info = header[0], info[0]
            frames = [dict(zip(header, line, strict=False)) for line in info.tolist()]
            prop = orjson.dumps(
                frames, option=orjson.OPT_INDENT_2|orjson.OPT_SORT_KEYS,
            ).decode()
            prt.print(f"{'frames':<{pad}}: {len(frames)} frames")
        case "vid_height":
            prop = cutcutcodec.get_resolution(video)[0]
            prt.print(f"{'height':<{pad}}: {prop} pixels")
        case "vid_width":
            prop = cutcutcodec.get_resolution(video)[1]
            prt.print(f"{'width':<{pad}}: {prop} pixels")
        case "vid_size":
            prop = video.stat().st_size
            prt.print(f"{'size':<{pad}}: {prop*1e-6:.2f} MB")
        case "vid_pix_fmt" | "vid_range" | "vid_name" | "vid_eotf" | "vid_gamut" | "vid_codec":
            prop = {
                "vid_pix_fmt": cutcutcodec.get_pix_fmt,
                "vid_range": cutcutcodec.get_range,
                "vid_name": lambda p: p.name,
                "vid_eotf": lambda p: cutcutcodec.get_colorspace(p).transfer,
                "vid_gamut": lambda p: cutcutcodec.get_colorspace(p).primaries,
                "vid_codec": cutcutcodec.get_codec_video,
            }[field](video)
            prt.print(f"{' '.join(field.split('_')[1:]):<{pad}}: {prop}")
        case _:
            logging.getLogger(__name__).warning("field %s not recognised, skipped", field)
    return prop


def _fill_met_table(
    database: pathlib.Path,
    ref_id: bytes,
    ref_path: pathlib.Path,
    dis_id: bytes,
    dis_path: pathlib.Path,
    **kwargs: dict,
) -> sqlite3.Connection | None:
    """Complete the table t_met_metric."""
    # get actual informations
    conn = open_ro(database, kwargs.pop("conn"))
    metrics = conn.execute(
        "SELECT * FROM t_met_metric WHERE met_ref_vid_id=? AND met_dis_vid_id=?",
        (ref_id, dis_id),
    ).fetchone()
    metrics = {} if metrics is None else dict(metrics)

    # missing fields
    fields = {
        *(("met_lpips_alex",) if kwargs["lpips_alex"] else ()),
        *(("met_lpips_vgg",) if kwargs["lpips_vgg"] else ()),
        *(("met_psnr",) if kwargs["psnr"] else ()),
        *(("met_ssim",) if kwargs["ssim"] else ()),
        *(("met_vif",) if kwargs["vif"] else ()),
        *(("met_vmaf",) if kwargs["vmaf"] else ()),
    }
    fields -= {k for k, v in metrics.items() if v is not None}
    if not fields:
        return conn
    conn.close()
    fields = sorted(fields)  # to frozen order in sql request and for printing repetability

    # fill missing fields
    pad = max(map(len, fields)) - 4
    with Printer(
        f"Compute metrics between {ref_path.name} and {dis_path.name}...", color="green",
    ) as prt:
        new_metrics = cutcutcodec.video_metrics(
            dis_path, ref_path,
            lpips_alex=kwargs["lpips_alex"],
            lpips_vgg=kwargs["lpips_vgg"],
            psnr=kwargs["psnr"],
            ssim=kwargs["ssim"],
            vif=kwargs["vif"],
            vmaf=kwargs["vmaf"],
        )
        for metric in sorted(new_metrics):
            values = new_metrics[metric]
            prt.print(f"{metric:<{pad}}: {np.nanmean(values):.2f} +/- {np.nanstd(values):.2f}")
    metrics = {f"met_{m}": list_to_binary(v) for m, v in new_metrics.items()}

    # update result
    with (
        Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=600)),
        sqlite3.connect(database) as conn,
    ):
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO t_met_metric (met_ref_vid_id, met_dis_vid_id) VALUES (?, ?)",
            (ref_id, dis_id),
        )
        cursor.execute(
            (
                f"UPDATE t_met_metric SET {', '.join(f'{k}=?' for k in fields)} "
                "WHERE met_ref_vid_id=? AND met_dis_vid_id=?"
            ),
            [metrics[k] for k in fields] + [ref_id, dis_id],
        )

    return None


def probe_and_store(
    database: pathlib.Path,
    video: pathlib.Path,
    conn: sqlite3.Connection | None = None,
    **kwargs: dict,
) -> sqlite3.Connection | None:
    """Measure the properties of the video.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.
    video : pathlib.Path
        The source video file to be annalysed.
    conn: sqlite3.Connection, optional
        A read only database connection.
    **kwargs : dict
        All the metrics

    """
    assert isinstance(video, pathlib.Path), video.__class__.__name__
    assert video.is_file(), video

    vid_id: bytes = compute_video_hash(video)

    conn = _fill_vid_table(database, vid_id, video, conn=conn, **kwargs)
    conn = open_ro(database, conn)

    # get the references videos for comparative comparisons
    references: dict[pathlib.Path, bytes] = kwargs["ref"].copy()
    for res in conn.execute(
        """
        SELECT vid_name, enc_src_vid_id FROM t_enc_encode
        JOIN t_vid_video ON enc_src_vid_id=vid_id
        WHERE enc_dst_vid_id=?
        """,
        (vid_id,),
    ):
        ref_stem, ref_id = res["vid_name"], res["enc_src_vid_id"]
        # try to find video full path
        if (
            ref := database.with_name(ref_stem)).is_file() or (ref := video.with_name(ref_stem)
        ).is_file():
            references[ref] = ref_id
        else:
            logging.getLogger(__name__).info("failed to find the reference video %s", ref)
    references = {ref: ref_id for ref, ref_id in references.items() if ref_id != vid_id}

    # perform the comparative metrics
    for ref, ref_id in references.items():
        conn = _fill_met_table(database, ref_id, ref, vid_id, video, conn=conn, **kwargs)
    return conn
