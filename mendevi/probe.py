#!/usr/bin/env python3

"""Perform the metrics and video properties measures."""

import json
import pathlib
import sqlite3

from context_verbose import Printer
import cutcutcodec
import numpy as np

from mendevi.database.serialize import list_to_binary
from mendevi.utils import compute_video_hash


def _fill_vid_table(database: pathlib.Path, vid_id: bytes, video: pathlib.Path, **kwargs):
    """Complete the table t_vid_video."""
    # get actual informations
    with sqlite3.connect(database) as sql_database:
        sql_database.row_factory = sqlite3.Row
        cursor = sql_database.cursor()
        prop = cursor.execute(
            "SELECT * FROM t_vid_video WHERE vid_id=?", (vid_id,)
        ).fetchone()
    prop = dict(prop)

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
        "vid_size",
        "vid_uvq",
        "vid_width",
    }
    fields -= {k for k, v in prop.items() if v is not None}
    if kwargs["uvq"] is False:
        fields -= {"vid_uvq"}
    if not fields:
        return None
    fields = sorted(fields)  # to frozen order in sql request and for printing repetability

    # fill missing fields
    pad = max(map(len, fields)) - 4
    with Printer(f"Get properties of {video.name}...", color="green") as prt:
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
                    frames = [dict(zip(header, l)) for l in info.tolist()]
                    prop["vid_frames"] = json.dumps(frames)
                    prt.print(f"{'frames':<{pad}}: {len(frames)} frames")
                case "vid_height":
                    prop["vid_height"] = cutcutcodec.get_resolution(video)[0]
                    prt.print(f"{'height':<{pad}}: {prop['vid_height']} pixels")
                case "vid_width":
                    prop["vid_width"] = cutcutcodec.get_resolution(video)[0]
                    prt.print(f"{'width':<{pad}}: {prop['vid_width']} pixels")
                case "vid_pix_fmt":
                    prop["vid_pix_fmt"] = cutcutcodec.get_pix_fmt(video)
                    prt.print(f"{'pix fmt':<{pad}}: {prop['vid_pix_fmt']}")
                case "vid_uvq":
                    uvq = cutcutcodec.compare(None, video, uvq=True)["uvq"]
                    prop["vid_uvq"] = list_to_binary(uvq)
                    prt.print(f"{'uvq':<{pad}}: {np.mean(uvq):.1f} +/- {np.std(uvq):.1f}")
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

    # update result
    with sqlite3.connect(database) as sql_database:
        sql_database.execute(
            (
                f"UPDATE t_vid_video SET {', '.join(f'{k}=?' for k in fields)} "
                "WHERE vid_id=?"
            ),
            [prop[k] for k in fields] + [vid_id],
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

