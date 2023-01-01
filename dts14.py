"""converts a dtswav file (with 14-bit packing) to a normal dts file"""
import sys
import struct

def main():
    f = open(sys.argv[1], "rb")
    f.read(0x2c)
    out = sys.stdout.buffer
    if len(sys.argv) > 2:
        out = open(sys.argv[2], "xb")
    convert(f, out)
    f.close()
    if out != sys.stdout.buffer:
        out.close()

def convert(f, out):
    unpack = struct.Struct("<hhhhhhhh").unpack
    #for i in range(1000):
    while 1:
        data = f.read(16)
        if len(data) < 16:
            break
        bits = 0
        for n in unpack(data):
            assert -0x2000 <= n <= 0x1fff, hex(n)
            bits = (bits<<14) + (n&0x3fff)
            #if i == 0: print(hex(n), hex(bits), file=sys.stderr)
        out.write(bits.to_bytes(14, 'big'))

main()
