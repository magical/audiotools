import sys

"""this script splits a dts file into separate tracks based on
blu-ray chapter markings.

to get the chapter markings, run mpls_dump from bdtools 1.5

    mpls_dump -c PLAYLIST/00001.mpls | grep ticks | cut -d: -f2 > chaps

to extract a dts core stream from a m2ts stream

    ffmpeg -i http://172.17.0.2:51000/stream/title1.m2ts -bsf:a dca_core -acodec copy -map 0:2 audio.dts
"""

DTS_FRAME_SAMPLES = 512 # samples / frame
DTS_FRAME_BYTES = 0x7DC # bytes / frame
DTS_HZ = 48000.0 # samples / second
TICK_HZ = 45000.0 # samples / second
TICK_START = 27000000 # ticks

def main():
    ticklist = []

    chapfile = sys.argv[1]
    dtsfile = sys.argv[2]

    with open(chapfile) as f:
        for line in f:
            tick = int(line.strip())
            ticklist.append(tick)

    assert ticklist[0] == TICK_START
    del ticklist[0]

    sizelist = []

    prev = 0
    for tick in ticklist:
        tick = tick - TICK_START
        frame = int(round(tick * (DTS_HZ / TICK_HZ) / DTS_FRAME_SAMPLES))
        bytes = (frame - prev) * DTS_FRAME_BYTES
        prev = frame
        sizelist.append(bytes)

    with open(dtsfile, 'rb') as f:
        for i, bytes in enumerate(sizelist):
            track = i + 1
            outfile = "track%02d.dts" % track
            copy(f, outfile, bytes)

        copyall(f, "track%02d.dts" % (len(sizelist) + 1))

def copy(f, outfile, bytes):
    print(outfile)
    with open(outfile, "xb") as out:
        while bytes > 0:
            buf = f.read(min(bytes, 4096))
            if not buf:
                break
            out.write(buf)
            bytes -= len(buf)
    if bytes:
        print("unexpected eof, expected %d more bytes" % bytes)

def copyall(f, outfile):
    print(outfile)
    with open(outfile, "xb") as out:
        while True:
            buf = f.read(4096)
            if not buf:
                break
            out.write(buf)

main()
