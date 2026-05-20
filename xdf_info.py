from icecream import ic
from pyxdf import pyxdf


def xdf_info(filepath: str, info_dict:bool = False) -> tuple:
    """
    Extract metadata from an xdf file

    Args:
        filepath: path to the xdf file
        info_dict: if True, return a dictionary containing the metadata extracted from the xdf file
    Return:
        metadata: dict containing the metadata extracted from the xdf file
    """
    data, header = pyxdf.load_xdf(filepath)
    for stream in data:
        n = len(stream['time_series'])
        stream_time = stream['time_stamps'][-1] - stream['time_stamps'][0]
        print(f"{stream['info']['name'][0]}: {n} samples, duration {stream_time:.2f} seconds")

        if info_dict:
           ic(stream['info'])
    return data, header

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract metadata from an xdf file")
    parser.add_argument("filepath", type=str, help="path to the xdf file")
    parser.add_argument("--info-dict", action="store_true", help="show info dictionary")
    args = parser.parse_args()

    xdf_info(args.filepath, info_dict=args.info_dict)
