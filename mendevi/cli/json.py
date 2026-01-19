"""Extract the main fields from an SQL database into JSON format."""

import pathlib
import sqlite3

import click
import orjson
import tqdm
from context_verbose import Printer
from cutcutcodec.utils import mround

from mendevi.database.meta import merge_extractors

from .parse import parse_videos_database


def _round(value: object) -> object:
    """Alias to cutcutcodec mround for float only."""
    if isinstance(value, float):
        return mround(value)
    return value


def _add_key_key_val(dico: dict, key1: str, key2: str, value: object) -> None:
    """Ensure dico[key1][key2] = [value, ...]."""
    dico[key1] = dico.get(key1, {})
    dico[key1][key2] = dico[key1].get(key2, [])
    dico[key1][key2].append(value)


@click.command()
@click.argument("database", type=click.Path())
@click.option("-o", "--output", type=click.Path(), help="The output json database path.")
def main(database: str, **kwargs: dict) -> None:
    """Extract the main fields from an SQL database into JSON format.

    \b
    Parameters
    ----------
    database : pathlike
        The source SQL database to be converted.
    **kwargs: dict
        Please refer to the detailed arguments below.
    output : pathlike, optional
        The destination json database path.
        By default, the file is created in the same folder than the SQL database.

    """
    # parse args
    with Printer("Parse configuration...") as prt:
        _, database = parse_videos_database(prt, (), database)
        if (output := kwargs.get("output")) is None:
            output = database.with_suffix(".json")
        else:
            output = pathlib.Path(output).expanduser()
            if output.is_dir():
                output = output / f"{database.stem}.json"
        prt.print(f"json file : {output}")

    # read database
    content = {}
    context = [
        "bitrate",
        "effort",
        "encoder",
        "eotf",
        "height",
        "lpips",
        "mode",
        "primaries",
        "profile",
        "psnr",
        "quality",
        "range",
        "ref_stem",
        "ssim",
        "threads",
        "video_duration",
        "vmaf",
        "width",
    ]
    with Printer("Read SQL database...", color="cyan") as prt:
        prt.print("compile the line extractor")
        _atom_names, line_extractor = merge_extractors(
            {
                "video_hash",
                # context
                *context,
                # activity
                "hostname",
                "act_duration",
                "cores",
                "power",
                "temp",
            },
            return_callable=True,
        )
        with sqlite3.connect(database) as conn:
            conn.row_factory = sqlite3.Row
            prt.print("read 'encode' and 'metric' extractor")
            # from mendevi.database.meta import get_extractor
            # from mendevi.database.extract import SqlLinker
            # select = {s for lbl in atom_names for s in get_extractor(lbl).func.select}
            # for query in SqlLinker(*select).sql:
            #     print(query)
            count = conn.execute("SELECT COUNT(*) FROM t_enc_encode").fetchone()["COUNT(*)"]
            for row_ in tqdm.tqdm(
                conn.execute(
                    """
                    SELECT
                        t_act_activity.act_duration,
                        t_act_activity.act_ps_core,
                        t_act_activity.act_ps_dt,
                        t_act_activity.act_ps_temp,
                        t_act_activity.act_rapl_dt,
                        t_act_activity.act_rapl_power,
                        t_act_activity.act_wattmeter_dt,
                        t_act_activity.act_wattmeter_power,
                        t_dst_video.vid_duration,
                        t_dst_video.vid_eotf,
                        t_dst_video.vid_gamut,
                        t_dst_video.vid_height,
                        t_dst_video.vid_id,
                        t_dst_video.vid_range,
                        t_dst_video.vid_size,
                        t_dst_video.vid_width,
                        t_enc_encode.enc_effort,
                        t_enc_encode.enc_encoder,
                        t_enc_encode.enc_mode,
                        t_enc_encode.enc_quality,
                        t_enc_encode.enc_threads,
                        t_env_environment.env_hostname,
                        t_met_metric.met_lpips_alex,
                        t_met_metric.met_lpips_vgg,
                        t_met_metric.met_psnr,
                        t_met_metric.met_ssim,
                        t_met_metric.met_vmaf,
                        t_ref_video.vid_name AS ref_vid_name
                    FROM t_enc_encode
                    JOIN t_vid_video AS t_ref_video
                        ON t_enc_encode.enc_src_vid_id = t_ref_video.vid_id
                    JOIN t_vid_video AS t_dst_video
                        ON t_enc_encode.enc_dst_vid_id = t_dst_video.vid_id
                    LEFT JOIN t_met_metric
                        ON t_enc_encode.enc_dst_vid_id = t_met_metric.met_dis_vid_id
                        AND t_enc_encode.enc_src_vid_id = t_met_metric.met_ref_vid_id
                    JOIN t_act_activity
                        ON t_enc_encode.enc_act_id = t_act_activity.act_id
                    JOIN t_env_environment
                        ON t_enc_encode.enc_env_id = t_env_environment.env_id
                    """,
                ),
                dynamic_ncols=True,
                leave=False,
                smoothing=1e-6,
                total=count,
                unit="vid",
            ):
                row = line_extractor(dict(row_))
                vid_id = row.pop("video_hash")
                content[vid_id] = content.get(vid_id, {"id": vid_id})
                content[vid_id] |= {k: _round(row[k]) for k in context if row[k] is not None}
                _add_key_key_val(
                    content[vid_id],
                    "encode_duration",
                    row["hostname"],
                    _round(row["act_duration"]),
                )
                _add_key_key_val(
                    content[vid_id], "encode_cores", row["hostname"], _round(row["cores"]),
                )
                _add_key_key_val(
                    content[vid_id], "encode_power", row["hostname"], _round(row["power"]),
                )
                _add_key_key_val(
                    content[vid_id], "encode_temp", row["hostname"], _round(row["temp"]),
                )
            prt.print("read 'decode' and 'metric' extractor")
            count = conn.execute("SELECT COUNT(*) FROM t_dec_decode").fetchone()["COUNT(*)"]
            for row_ in tqdm.tqdm(
                conn.execute(
                    """
                    SELECT
                        t_act_activity.act_duration,
                        t_act_activity.act_ps_core,
                        t_act_activity.act_ps_dt,
                        t_act_activity.act_ps_temp,
                        t_act_activity.act_rapl_dt,
                        t_act_activity.act_rapl_power,
                        t_act_activity.act_wattmeter_dt,
                        t_act_activity.act_wattmeter_power,
                        t_dst_video.vid_duration,
                        t_dst_video.vid_eotf,
                        t_dst_video.vid_gamut,
                        t_dst_video.vid_height,
                        t_dst_video.vid_id,
                        NULL AS ref_vid_name,  -- bulshit
                        t_dst_video.vid_range,
                        t_dst_video.vid_size,
                        t_dst_video.vid_width,
                        NULL AS enc_effort,  -- bulshit
                        NULL AS enc_encoder,  -- bulshit
                        NULL AS enc_mode,  -- bulshit
                        NULL AS enc_quality,  -- bulshit
                        NULL AS enc_threads,  -- bulshit
                        t_env_environment.env_hostname,
                        t_met_metric.met_lpips_alex,
                        t_met_metric.met_lpips_vgg,
                        t_met_metric.met_psnr,
                        t_met_metric.met_ssim,
                        t_met_metric.met_vmaf
                    FROM t_dec_decode
                    JOIN t_act_activity
                        ON t_dec_decode.dec_act_id = t_act_activity.act_id
                    LEFT JOIN t_met_metric
                        ON t_dec_decode.dec_vid_id = t_met_metric.met_dis_vid_id
                    JOIN t_vid_video AS t_dst_video
                        ON t_dec_decode.dec_vid_id = t_dst_video.vid_id
                    JOIN t_env_environment
                        ON t_dec_decode.dec_env_id = t_env_environment.env_id
                    """,
                ),
                dynamic_ncols=True,
                leave=False,
                smoothing=1e-6,
                total=count,
                unit="vid",
            ):
                row = line_extractor(dict(row_))
                row["name"] = None
                vid_id = row.pop("video_hash")
                content[vid_id] = content.get(vid_id, {"id": vid_id})
                content[vid_id] |= {k: _round(row[k]) for k in context if row[k] is not None}
                _add_key_key_val(
                    content[vid_id],
                    "decode_duration",
                    row["hostname"],
                    _round(row["act_duration"]),
                )
                _add_key_key_val(
                    content[vid_id], "decode_cores", row["hostname"], _round(row["cores"]),
                )
                _add_key_key_val(
                    content[vid_id], "decode_power", row["hostname"], _round(row["power"]),
                )
                _add_key_key_val(
                    content[vid_id], "decode_temp", row["hostname"], _round(row["temp"]),
                )
            prt.print_time()

    # write json
    content = [content[k] for k in sorted(content)]
    with Printer("Write JSON database...", color="cyan") as prt:
        content = orjson.dumps(content, option=orjson.OPT_INDENT_2|orjson.OPT_SORT_KEYS)
        with output.open("wb") as raw:
            raw.write(content)
        prt.print_time()
