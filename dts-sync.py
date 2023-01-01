"""finds places where a DTS stream loses sync"""
import sys
f = open(sys.argv[1], 'rb')

SYNC = b'\x7f\xfe\x80\x01'

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
                pos += i
                print("resync at %#x (+%#x)" % (pos, i))
                f.seek(pos, 0)
                continue
        print("lost sync")
        break

    x = header[7] + (header[6]<<8) + (header[5]<<16)
    fsize = ((x >> 4) & 0x3fff) + 1
    if fsize != 0xe00:
        print("fsize=%#x at %#x" % (fsize, pos))
    f.seek(fsize, 1)
    pos += fsize
    blocks += 1

print(blocks, "blocks")

