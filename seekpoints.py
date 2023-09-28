#!/usr/bin/env python3
# Finds flac files that lack a SEEKTABLE chunk
# OR that have a SEEKTABLE chunk with frame_samples=0 or PLACEHOLDER entries

import sys
import os
import struct

SEEK_SET = 0
SEEK_CUR = 1

def main():
    args = sys.argv[1:]
    verbose = False
    if '-v' in args:
        args.remove('-v')
        verbose = True
    if '-r' in args:
        # recursive
        dirs = [x for x in args if not x.startswith('-')]
        if not dirs:
            dirs = ['.']
        for topdir in dirs:
            for path, dirnames, filenames in os.walk(topdir):
                dirnames.sort()
                filenames = [x for x in filenames if x.endswith('.flac')]
                filenames.sort()
                scan_filenames([os.path.join(path, x) for x in filenames], verbose=verbose)
    else:
        scan_filenames(args, verbose=verbose)

def scan_filenames(filename_list, verbose=True):
    def report(filename, reason):
        if verbose:
            print("%s: %s" % (filename, reason))
        else:
            print(filename)

    for filename in filename_list:
        try:
            with open(filename, "rb") as f:
                pos, blocksize, found = find_seektable_block(f)
                if found:
                    f.seek(pos, SEEK_SET)
                    num_placeholders, num_empty = get_seekpoint_stats(f, blocksize)
                    if num_placeholders > 0:
                        report(filename, "placeholders")
                    if num_empty > 0 and (verbose or num_placeholders == 0):
                        report(filename, "frame_samples=0")
                else:
                    report(filename, "missing")
                #if not does_it_have_a_seektable_chunk(f):
                #    print(filename, )
        except Exception as e:
            print("Error checking %s: %s" % (filename, e))

def does_it_have_a_seektable_chunk(f):
    magic = f.read(4)
    if magic != b'fLaC':
        raise Exception("not a flac file")

    lastpos = 4
    lastblock = False
    while not lastblock:
        chunk_header = f.read(4)
        if not chunk_header:
            break # eof
        if len(chunk_header) < 4:
            raise Exception("truncated metadata block header")
        lastblock = chunk_header[0]&0x80 != 0
        blocktype = chunk_header[0] & 0x7f
        if blocktype == 0x7f:
            raise Exception("invalid metadata block type")
        blocklength = int.from_bytes(chunk_header[1:4], byteorder='big', signed=False)
        pos = f.seek(blocklength, SEEK_CUR)
        if pos != lastpos + 4 + blocklength:
            raise Exception("truncated metadata block")

        if blocktype == 3:
            # Found a SEEKTABLE chunk
            return True

        lastpos = pos

    return False

def find_seektable_block(f):
    magic = f.read(4)
    if magic != b'fLaC':
        raise Exception("not a flac file")

    lastpos = 4
    lastblock = False
    while not lastblock:
        chunk_header = f.read(4)
        if not chunk_header:
            break # eof
        if len(chunk_header) < 4:
            raise Exception("truncated metadata block header")
        lastblock = chunk_header[0]&0x80 != 0
        blocktype = chunk_header[0] & 0x7f
        if blocktype == 0x7f:
            raise Exception("invalid metadata block type")
        blocklength = int.from_bytes(chunk_header[1:4], byteorder='big', signed=False)
        pos = f.seek(blocklength, SEEK_CUR)
        if pos != lastpos + 4 + blocklength:
            raise Exception("truncated metadata block")

        if blocktype == 3:
            # Found a SEEKTABLE chunk
            return lastpos, blocklength, True

        lastpos = pos

    return 0, 0, False

PLACEHOLDER = 0xFFFF_FFFF_FFFF_FFFF

def get_seekpoint_stats(f, blocklength):
    unpack = struct.Struct('>QQH').unpack
    size = struct.calcsize('>QQH')
    num_placeholders = 0
    num_empty = 0
    f.read(4)
    for _ in range(blocklength//size):
        seekpoint = f.read(size)
        #print(seekpoint)
        if len(seekpoint) < size:
            raise Exception("premature end of seekpoint block")
        sample, offset, frame_samples = unpack(seekpoint)
        if sample == PLACEHOLDER:
            num_placeholders += 1
        elif frame_samples == 0:
            num_empty += 1
    return num_placeholders, num_empty



if __name__ == '__main__':
    main()
