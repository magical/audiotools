import sys

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
    ticklist = []

    chapfile = "-"
    if len(sys.argv) > 2:
        chapfile = sys.argv[1]

    if chapfile and chapfile != '-':
        with open(chapfile) as f:
            for line in f:
                tick = int(line.strip())
                ticklist.append(tick)
    else:
        for line in sys.stdin:
            tick = int(line.strip())
            ticklist.append(tick)

    assert ticklist[0] == TICK_START
    del ticklist[0]

    sizelist = []

    prev = 0
    for tick in ticklist:
        tick = tick - TICK_START
        current = int(round(tick * (FLAC_HZ / TICK_HZ)))
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
