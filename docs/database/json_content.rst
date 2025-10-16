.. _json_content:

JSON Database Content
=====================

This is a summarized version of :ref:`sql_content`.

.. code:: yaml

    {
        "00cf989a4313672743967debf8eb561f": {  # the video md5 checksum
            "bitrate": 507741.85814185813,  # video bitrate in bit / seconds
            "decode_cores": {  # average cumulative utilisation rate of logical cores during decoding
                "kattappana": [  # hostname
                    4.409871520996094,  # on point per decoding
                    4.563056945800781,
                    4.21993896484375
                ],
                ...,
            },
            "decode_duration": {  # decoding processing activity duration in seconds
                "kattappana": [
                    1.1390342712402344,
                    1.2235794067382812,
                    1.0313429832458496
                ],
                ...,
            },
            "decode_power": {  # average decoding power consumption in Watts
                "kattappana": [
                    15.987945899198474,
                    13.501128622369583,
                    20.06601347820743
                ]
            },
            "effort": "medium",  # effort provided as a parameter to the encoder
            "encode_cores": {
                "kattappana": [
                    6.648703002929688,
                    7.453453451076996
                ]
            },
            "encode_duration": {  # encoding processing activity duration in seconds
                "kattappana": [
                    10.384547710418701,
                    9.503988913457194
                ]
            },
            "encode_power": {  # average encoding power consumption in Watts
                "kattappana": [
                    12.330227397691576,
                    13.64569849689595
                ]
            },
            "encoder": "libx264",  # name of the encoder
            "height": 1080,  # height of images in pixels
            "name": "netflix_crosswalk",  # input video basename
            "profile": "hd",  # profile of the video
            "psnr": 27.739999771118164,  # average Peak Signal to Noise Ratio (PSNR)
            "quality": 0.919921875,  # quality level passed to the encoder
            "ssim": 0.8184635639190674,  # average Structural Similarity (SSIM)
            "video_duration": 5.005,  # video duration in seconds
            "vmaf": 25.194791793823242,  # average Video Multi-Method Assessment Fusion (VMAF)
            "width": 1080  # width of images in pixels
        },
        "00ef134f208da3309bf81c2b5ae19be1": {
            ...,
        },
        ...,
    }


The JSON database is only an extract from the SQL database, which is much more comprehensive.

When a value is not defined, it is simply omitted from the database, so it is safer to use ``json_database_content.get(field)`` rather than ``json_database_content[field]``.
