#!/usr/bin/env python3

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


def _fill_vid_table(database: pathlib.Path, vid_id: bytes, video: pathlib.Path, **kwargs):
    """Complete the table t_vid_video."""
    # get actual informations
    with sqlite3.connect(database) as sql_database:
        sql_database.row_factory = sqlite3.Row
        cursor = sql_database.cursor()
        prop = cursor.execute(
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
        return
    fields = sorted(fields)  # to frozen order in sql request and for printing repetability

    # fill missing fields
    pad = max(map(len, fields)) - 4
    with Printer(f"Get properties of {video.name}...", color="green") as prt:
        # basic fields
        for field in fields:
            match field:
                case "vid_duration":
                    prop["vid_duration"] = float(cutcutcodec.get_duration_video(video))
                    prt.print(f"{'duration':<{pad}}: ", end="")
                    prt.print_time(prop["vid_duration"], print_headers=False)
                case "vid_fps":
                    prop["vid_fps"] = float(cutcutcodec.get_rate_video(video))
                    prt.print(f"{'fps':<{pad}}: {prop['vid_fps']:.2f} Hz")
                case "vid_frames":
                    header, info = cutcutcodec.core.analysis.ffprobe.get_slices_metadata(video)
                    header, info = header[0], info[0]
                    frames = [dict(zip(header, line)) for line in info.tolist()]
                    prop["vid_frames"] = orjson.dumps(
                        frames, option=orjson.OPT_INDENT_2|orjson.OPT_SORT_KEYS,
                    ).decode()
                    prt.print(f"{'frames':<{pad}}: {len(frames)} frames")
                case "vid_height":
                    prop["vid_height"] = cutcutcodec.get_resolution(video)[0]
                    prt.print(f"{'height':<{pad}}: {prop['vid_height']} pixels")
                case "vid_width":
                    prop["vid_width"] = cutcutcodec.get_resolution(video)[1]
                    prt.print(f"{'width':<{pad}}: {prop['vid_width']} pixels")
                case "vid_pix_fmt":
                    prop["vid_pix_fmt"] = cutcutcodec.get_pix_fmt(video)
                    prt.print(f"{'pix fmt':<{pad}}: {prop['vid_pix_fmt']}")
                case "vid_range":
                    prop["vid_range"] = cutcutcodec.get_range(video)
                    prt.print(f"{'range':<{pad}}: {prop['vid_range']}")
                case "vid_size":
                    prop["vid_size"] = video.stat().st_size
                    prt.print(f"{'size':<{pad}}: {prop['vid_size']*1e-6:.2f} MB")
                case "vid_name":
                    prop["vid_name"] = video.name
                    prt.print(f"{'name':<{pad}}: {prop['vid_name']}")
                case "vid_eotf":
                    prop["vid_eotf"] = cutcutcodec.get_colorspace(video).transfer
                    prt.print(f"{'eotf':<{pad}}: {prop['vid_eotf']}")
                case "vid_gamut":
                    prop["vid_gamut"] = cutcutcodec.get_colorspace(video).primaries
                    prt.print(f"{'gamut':<{pad}}: {prop['vid_gamut']}")
                case "vid_codec":
                    prop["vid_codec"] = cutcutcodec.get_codec_video(video)
                    prt.print(f"{'codec':<{pad}}: {prop['vid_codec']}")

        # metric fields
        fields = set(fields)
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
    with (
        Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=600)),
        sqlite3.connect(database) as sql_database,
    ):
        cursor = sql_database.cursor()
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


def _fill_met_table(
    database: pathlib.Path,
    ref_id: bytes,
    ref_path: pathlib.Path,
    dis_id: bytes,
    dis_path: pathlib.Path,
    **kwargs,
):
    """Complete the table t_met_metric."""
    # get actual informations
    with sqlite3.connect(database) as sql_database:
        sql_database.row_factory = sqlite3.Row
        cursor = sql_database.cursor()
        metrics = cursor.execute(
            "SELECT * FROM t_met_metric WHERE met_ref_vid_id=? AND met_dis_vid_id=?",
            (ref_id, dis_id),
        ).fetchone()
    metrics = {} if metrics is None else dict(metrics)

    # missing fields
    fields = set([
        *(("met_lpips_alex",) if kwargs["lpips_alex"] else ()),
        *(("met_lpips_vgg",) if kwargs["lpips_vgg"] else ()),
        *(("met_psnr",) if kwargs["psnr"] else ()),
        *(("met_ssim",) if kwargs["ssim"] else ()),
        *(("met_vmaf",) if kwargs["vmaf"] else ()),
    ])
    fields -= {k for k, v in metrics.items() if v is not None}
    if not fields:
        return
    fields = sorted(fields)  # to frozen order in sql request and for printing repetability

    # fill missing fields
    pad = max(map(len, fields)) - 4
    with Printer(
        f"Compute metrics between {ref_path.name} and {dis_path.name}...", color="green",
    ) as prt:
        new_metrics = cutcutcodec.video_metrics(
            ref_path, dis_path,
            lpips_alex=kwargs["lpips_alex"],
            lpips_vgg=kwargs["lpips_vgg"],
            psnr=kwargs["psnr"],
            ssim=kwargs["ssim"],
            vmaf=kwargs["vmaf"],
        )
        for metric in sorted(new_metrics):
            values = new_metrics[metric]
            prt.print(f"{metric:<{pad}}: {np.nanmean(values):.2f} +/- {np.nanstd(values):.2f}")
    metrics = {f"met_{m}": list_to_binary(v) for m, v in new_metrics.items()}

    # update result
    with (
        Lock(str(database.with_name(".dblock")), lifetime=datetime.timedelta(seconds=600)),
        sqlite3.connect(database) as sql_database,
    ):
        cursor = sql_database.cursor()
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


def probe_and_store(database: pathlib.Path, video: pathlib.Path, **kwargs):
    """Measure the properties of the video.

    Parameters
    ----------
    database : pathlike
        The path of the existing database to be updated.
    video : pathlib.Path
        The source video file to be annalysed.
    **kwargs : dict
        All the metrics

    """
    assert isinstance(video, pathlib.Path), video.__class__.__name__
    assert video.is_file(), video

    vid_id: bytes = compute_video_hash(video)

    _fill_vid_table(database, vid_id, video, **kwargs)

    # get the references videos for comparative comparisons
    references: dict[pathlib.Path, bytes] = kwargs["ref"].copy()
    with sqlite3.connect(database) as sql_database:
        cursor = sql_database.cursor()
        for ref_name, ref_id in cursor.execute(
            """
            SELECT vid_name, enc_src_vid_id FROM t_enc_encode
            JOIN t_vid_video ON enc_src_vid_id=vid_id
            WHERE enc_dst_vid_id=?
            """,
            (vid_id,),
        ):
            # try to find video full path
            if (ref := database.with_name(ref_name)).is_file() or (ref := video.with_name(ref_name)).is_file():
                references[ref] = ref_id
            else:
                logging.info("failed to find the reference video %s", ref)
    references = {ref: ref_id for ref, ref_id in references.items() if ref_id != vid_id}

    # perform the comparative metrics
    for ref, ref_id in references.items():
        _fill_met_table(database, ref_id, ref, vid_id, video, **kwargs)
