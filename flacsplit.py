import sys
import argparse

"""this script splits a dts file into separate tracks based on
blu-ray chapter markings.

to get the chapter markings, run mpls_dump from bdtools 1.5

    mpls_dump -c PLAYLIST/00001.mpls | grep ticks | cut -d: -f2 > chaps

to extract a dts core stream from a m2ts stream

    ffmpeg -i http://172.17.0.2:51000/stream/title1.m2ts -bsf:a dca_core -acodec copy -map 0:2 audio.dts
"""

FLAC_HZ = 96000.0 # samples / second
TICK_HZ = 45000.0 # samples / second
TICK_START = 27000000 # ticks

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--rate", default=FLAC_HZ, type=int, help="flac sample rate")
    parser.add_argument("-s", "--start", default=TICK_START, type=int, help="start ticks")
    parser.add_argument("chapfile", nargs="?", default="-")
    args = parser.parse_args()

    ticklist = []
    if args.chapfile and args.chapfile != '-':
        with open(args.chapfile) as f:
            for line in f:
                tick = int(line.strip())
                ticklist.append(tick)
    else:
        for line in sys.stdin:
            tick = int(line.strip())
            ticklist.append(tick)

    tick_start = args.start
    flac_hz = args.rate

    assert ticklist[0] == tick_start
    del ticklist[0]

    sizelist = []

    prev = 0
    for tick in ticklist:
        tick = tick - tick_start
        current = int(round(tick * (flac_hz / TICK_HZ)))
        samples = (current - prev)
        prev = current
        sizelist.append(samples)

    pipeline = []
    for i, samples in enumerate(sizelist):
            track = i + 1
            pipeline.append("trim 0 {}s".format(samples))
            pipeline.append("newfile")
    print(" : ".join(pipeline))


main()
