from typing import List

from numpy import typing as npt
from pylsl import (
    StreamInfo,
    StreamOutlet,
    cf_double64,
    cf_float32,
    cf_int8,
    cf_int16,
    cf_int32,
    cf_int64,
    cf_string,
    cf_undefined,
)


class LSLStream:
    def __init__(self):
        self.outlet = None
        self._is_init = False

    @property
    def is_init(self):
        return self._is_init

    def init(
        self,
        name: str,
        content_type: str,
        n_channels: int,
        stream_id: str,
        freq: int,
        channel_format: int,
        metadata: dict | None = None,
    ):
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
        if self._is_init:
            return

        info = StreamInfo(
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

        self._is_init = True
        self.outlet = StreamOutlet(info)

    def push_sample(self, sample: List | npt.NDArray):
        """Push a sample to the LSL stream if it is initialized."""
        if not self._is_init:
            # Don't do anything
            return
        self.outlet.push_sample(sample)  # type: ignore
