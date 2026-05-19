from pylsl import StreamInfo, StreamOutlet


def init(
    name: str,
    n_channels: int,
    stream_id: str,
    freq: int,
    metadata: dict | None = None,
) -> StreamOutlet:
    """
    Initialise a LSL stream

    Args:
        name: name of the stream
        n_channels: number of channels per sample
        channel_format: format/type of each channel (ex: string, int, ...)
                        same format for each channel
        stream_id: unique identifier of the stream
        content_type: content type of stream. By convention LSL uses the content
            types defined in the XDF file format specification where
            applicable
        freq: sampling rate in Hz

    Return:
        outlet: StreamOulet to push samples with LSL
    """
    # LSL
    # StreamInfo takes name t
    info = StreamInfo(name, "force",
                      channel_count=n_channels,
                      nominal_srate=freq,
                      source_id=stream_id)

    # Check if there is metadata to add to the lsl stream
    if metadata:
        # Get xml object of the stream created earlier
        xml_info = info.desc()
        # Add meta data to xml object
        for key, data in metadata.items():
            xml_info.append_child_value(key, str(data))

    return StreamOutlet(info)