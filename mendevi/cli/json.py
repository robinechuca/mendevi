#!/usr/bin/env python3

"""Extract the main fields from an SQL database into JSON format."""

import json
import pathlib
import sqlite3

from context_verbose import Printer
import click

from mendevi.database.meta import merge_extractors
from .parse import parse_videos_database


@click.command()
@click.argument("database", type=click.Path())
@click.option("-o", "--output", type=click.Path(), help="The output json database path.")
def main(database: str, **kwargs):
    """Extract the main fields from an SQL database into JSON format.

    \b
    Parameters
    ----------
    database : pathlike
        The source SQL database to be converted.
    output : pathlike, optional
        The destination json database path.
        By default, the file is created in the same folder than the SQL database.
    """
    # parse args
    with Printer("Parse configuration...") as prt:
        _, database = parse_videos_database(prt, (), database)
        if (output := kwargs.get("output", None)) is None:
            output = database.with_suffix(".json")
        else:
            output = pathlib.Path(output).expanduser()
            if output.is_dir():
                output = output / f"{database.stem}.json"
        prt.print(f"json file : {output}")

    # read database
    json_content = {}
    context = [
        "bitrate",
        "effort",
        "encoder",
        "height",
        "lpips",
        "name",
        "profile",
        "psnr",
        "quality",
        "ssim",
        "video_duration",
        "vmaf",
        "width",
    ]
    with Printer("Read SQL database...") as prt:
        prt.print("compile the line extractor")
        atom_names, line_extractor = merge_extractors(
            {
                "video_hash",
                # context
                *context,
                # activity
                "act_duration",
                "cores",
                "power",
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
            for raw in conn.execute(
                """
                SELECT
                    t_act_activity.act_duration,
                    t_act_activity.act_ps_core,
                    t_act_activity.act_ps_dt,
                    t_act_activity.act_rapl_dt,
                    t_act_activity.act_rapl_power,
                    t_act_activity.act_wattmeter_dt,
                    t_act_activity.act_wattmeter_power,
                    t_dst_video.vid_duration,
                    t_dst_video.vid_height,
                    t_dst_video.vid_size,
                    t_dst_video.vid_id,
                    t_enc_encode.enc_effort,
                    t_enc_encode.enc_encoder,
                    t_enc_encode.enc_quality,
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
                JOIN t_met_metric
                    ON t_enc_encode.enc_dst_vid_id = t_met_metric.met_dis_vid_id
                    AND t_enc_encode.enc_src_vid_id = t_met_metric.met_ref_vid_id
                JOIN t_act_activity
                    ON t_enc_encode.enc_act_id = t_act_activity.act_id
                """
            ):
                raw = line_extractor(dict(raw))
                video_hash = raw.pop("video_hash")
                json_content[video_hash] = json_content.get(video_hash, {})
                json_content[video_hash] |= {k: raw[k] for k in context if raw[k] is not None}
                json_content[video_hash]["encode_duration"] = (
                    json_content[video_hash].get("encode_duration", [])
                )
                json_content[video_hash]["encode_duration"].append(raw["act_duration"])
                json_content[video_hash]["encode_cores"] = (
                    json_content[video_hash].get("encode_cores", [])
                )
                json_content[video_hash]["encode_cores"].append(raw["cores"])
                json_content[video_hash]["encode_power"] = (
                    json_content[video_hash].get("encode_power", [])
                )
                json_content[video_hash]["encode_power"].append(raw["power"])
            prt.print("read 'decode' extractor")
            for raw in conn.execute(
                """
                SELECT
                    t_act_activity.act_duration,
                    t_act_activity.act_ps_core,
                    t_act_activity.act_ps_dt,
                    t_act_activity.act_rapl_dt,
                    t_act_activity.act_rapl_power,
                    t_act_activity.act_wattmeter_dt,
                    t_act_activity.act_wattmeter_power,
                    t_dst_video.vid_duration,
                    t_dst_video.vid_height,
                    t_dst_video.vid_size,
                    t_dst_video.vid_id,
                    t_dst_video.vid_name AS ref_vid_name,  -- bulshit
                    t_enc_encode.enc_effort,
                    t_enc_encode.enc_encoder,
                    t_enc_encode.enc_quality,
                    t_met_metric.met_lpips_alex,
                    t_met_metric.met_lpips_vgg,
                    t_met_metric.met_psnr,
                    t_met_metric.met_ssim,
                    t_met_metric.met_vmaf
                FROM t_dec_decode
                JOIN t_enc_encode
                    ON t_dec_decode.dec_vid_id = t_enc_encode.enc_dst_vid_id
                JOIN t_act_activity
                    ON t_dec_decode.dec_act_id = t_act_activity.act_id
                JOIN t_met_metric
                    ON t_dec_decode.dec_vid_id = t_met_metric.met_dis_vid_id
                JOIN t_vid_video AS t_dst_video
                    ON t_dec_decode.dec_vid_id = t_dst_video.vid_id
                """
            ):
                raw = line_extractor(dict(raw))
                del raw["name"]
                video_hash = raw.pop("video_hash")
                json_content[video_hash] = json_content.get(video_hash, {})
                json_content[video_hash] |= {k: raw[k] for k in context if raw[k] is not None}
                json_content[video_hash]["decode_duration"] = (
                    json_content[video_hash].get("decode_duration", [])
                )
                json_content[video_hash]["decode_duration"].append(raw["act_duration"])
                json_content[video_hash]["decode_cores"] = (
                    json_content[video_hash].get("decode_cores", [])
                )
                json_content[video_hash]["decode_cores"].append(raw["cores"])
                json_content[video_hash]["decode_power"] = (
                    json_content[video_hash].get("decode_power", [])
                )
                json_content[video_hash]["decode_power"].append(raw["power"])
            prt.print_time()

    # write json
    with Printer("Write JSON database...") as prt:
        with open(output, "w", encoding="utf-8") as raw:
            json.dump(json_content, raw, indent=4, sort_keys=True)
        prt.print_time()
