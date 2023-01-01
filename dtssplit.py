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

    info(dtsfile)

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

def info(dtsfile):
    global DTS_FRAME_BYTES
    global DTS_FRAME_SAMPLES
    global DTS_HZ
    with open(dtsfile, 'rb') as f:
        header = f.read(10)
        if header[0:4] != b'\x7f\xfe\x80\x01':
            sys.exit("error: %s is not a DTS file (header does not match)" % f.name)
        x = int.from_bytes(header[4:10], byteorder='big')
        fsize = (x>>20) & 0x3fff
        nblks = (x>>34) & 0x7f
        sfreq = (x>>10) & 0xf
        bitrate = (x>>5) & 0x1f

        if sfreq == 1: DTS_HZ = 8000.0
        elif sfreq == 2: DTS_HZ = 16000.0
        elif sfreq == 3: DTS_HZ = 32000.0
        elif sfreq == 6: DTS_HZ = 11025.0
        elif sfreq == 7: DTS_HZ = 22050.0
        elif sfreq == 8: DTS_HZ = 44100.0
        elif sfreq == 11: DTS_HZ = 12000.0
        elif sfreq == 12: DTS_HZ = 24000.0
        elif sfreq == 13: DTS_HZ = 48000.0
        else:
            sys.exit("error: invalid sfreq: %#x" % sfreq)

        DTS_FRAME_BYTES = fsize + 1
        DTS_FRAME_SAMPLES = 32 * (nblks + 1)

    bitrates = [
          32000,   56000,   64000,   96000,  112000,
         128000,  192000,  224000,  256000,  320000,
         384000,  448000,  512000,  576000,  640000,
         768000,  896000, 1024000, 1152000, 1280000,
        1344000, 1408000, 1411200, 1472000, 1536000,
        1920000, 2048000, 3072000, 3840000,
        "open", "variable", "lossless",
    ]
    print("bitrate = %s" % bitrates[bitrate])
    print("sample rate = %d" % DTS_HZ)
    print("frame size = %#x" % DTS_FRAME_BYTES)
    print("frame samples = %#x" % DTS_FRAME_SAMPLES)
    #sys.exit(0)

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
