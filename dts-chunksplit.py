"""splits a dts file at the places where it loses sync.
this can be useful for splitting a dts stream extracted from a dtswav,
which has 00 padding at the track boundaries in order to align the
start of a dts frame to the start of the track."""

import sys
f = open(sys.argv[1], 'rb')

SYNC = b'\x7f\xfe\x80\x01'

track = 1
out = open("track%02d.dts" % track, 'xb')

blocks = 0
pos = 0
while 1:
    header = f.peek(10)
    if len(header) == 0:
        print("done")
        break
    if header[0:4] != SYNC:
        print("desync at %#x" % pos)
        if header[0:4] == b'\x00\x00\x00\x00':
            haystack = f.read(4096)
            i = haystack.find(SYNC)
            if i >= 0:
                out.write(haystack[:i])
                out.close()
                pos += i
                print("resync at %#x (+%#x)" % (pos, i))
                f.seek(pos, 0)
                track += 1
                out = open("track%02d.dts" % track, 'xb')
                print("starting track", track)
                continue
        print("lost sync")
        out.write(haystack)
        break

    x = header[7] + (header[6]<<8) + (header[5]<<16)
    fsize = ((x >> 4) & 0x3fff) + 1
    if fsize != 0xe00:
        print("fsize=%#x at %#x" % (fsize, pos))
    data = f.read(fsize)
    out.write(data)
    pos += fsize
    blocks += 1

out.close()

print(blocks, "blocks")

