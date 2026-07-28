"""Convenience functions for working with LSL streams.

v0.1.0
"""

import pylsl
from pylsl import (  # useful constants and functions from pylsl
        cf_double64,
        cf_float32,
        cf_int8,
        cf_int16,
        cf_int32,
        cf_int64,
        cf_string,
        cf_undefined,
        local_clock,
        resolve_streams,
)


def init_stream(
        name: str,
        content_type: str,
        n_channels: int,
        stream_id: str,
        freq: int,
        channel_format: int,
        metadata: dict | None = None,
    ) -> pylsl.StreamOutlet:
        """
        Initialise a LSL stream

        Args:
            name: name of the stream
            content_type: content type of stream. By convention LSL uses the content
                types defined in the XDF file format specification where
            n_channels: number of channels per sample
            channel_format: format/type of each channel (ex: string, int, ...)
                            same format for each channel
            stream_id: unique identifier of the stream

                applicable
            freq: sampling rate in Hz

        Return:
            outlet: StreamOulet to push samples with LSL
        """

        info = pylsl.StreamInfo(
            name, content_type,
            channel_count=n_channels,
            nominal_srate=freq,
            channel_format=channel_format,
            source_id=stream_id,
        )

        # Check if there is metadata to add to the lsl stream
        if metadata:
            # Get xml object of the stream created earlier
            xml_info = info.desc()
            # Add meta data to xml object
            for key, data in metadata.items():
                xml_info.append_child_value(key, str(data))

        return pylsl.StreamOutlet(info)


def open_stream(prop:str, value:str, timeout:float = pylsl.FOREVER) -> pylsl.StreamInlet:
    """Open a LSL stream with a specific value for a given property.

    Keyword arguments:
    prop -- The StreamInfo property that should have a specific value (e.g.,
            "name", "type", "source_id", or "desc/manufacturer").
    value -- The string value that the property should have (e.g., "EEG" as
             the type property).
    timeout -- Optionally a timeout of the operation, in seconds. If the
               timeout expires, less than the desired number of streams
               (possibly none) will be returned. (default FOREVER)

    Returns a StreamInlet object to read from the stream.
    """

    streams = pylsl.resolve_byprop(prop, value, minimum=1, timeout=timeout)
    if not streams:
        raise RuntimeError(f"No stream found with {prop}={value}")
    return pylsl.StreamInlet(streams[0])
