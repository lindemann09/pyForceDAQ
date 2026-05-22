import select
import sys
from time import sleep

from pyforcedaq._lib import lsl

stream = lsl.init(name="test_stream",
                  n_channels=2,
                  stream_id="s1",
                  channel_format=lsl.cf_float32,
                  freq=1)

for x in range(1000):
    print(f"pushing sample {x}")
    stream.push_sample([x, x * 2])
    if select.select([sys.stdin], [], [], 0)[0]:
        sys.stdin.readline()
        break
    sleep(1)
