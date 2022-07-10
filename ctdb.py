#!/usr/bin/env python3
import sys
import argparse
import subprocess
from collections import namedtuple

import mutagen.flac
import requests
from xml.etree import ElementTree

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    toc = get_toc(args.files)

    print(f"toc={toc}")

    info = lookup_toc(toc)
    if not info:
        print("album not found")
        sys.exit(1)

    os.environ['PATH'] += os.pathsep + os.path.dirname(__file__)
    p1 = subprocess.Popen(["sox", "--no-clobber"] + args.files + ["-t", "s16", "-"], stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    p2 = subprocess.Popen(["ctdb_crc32"] + [entry.crc32 for entry in info], stdin=p1.stdout, stdout=subprocess.PIPE)

    p1.stdout.close()
    out = p2.stdout.read()
    p2.stdout.close()
    p2.wait()
    p1.wait()

    print(out)


def get_toc(tracks):

    toc = []
    t = 0
    for filename in tracks:
        toc.append(t // 588)

        f = mutagen.flac.Open(filename)
        if f.info.sample_rate != 44100 or f.info.channels != 2:
            raise Exception("%s: not a 44100 Hz stereo track" % filename)

        length = f.info.total_samples * 44100 // f.info.sample_rate
        t += length
    toc.append((t + 588 - 1) // 588)

    return toc


CTDBEntry = namedtuple("CTDBEntry", "confidence, crc32, stride, trackcrcs")

def lookup_toc(toc):
    url = 'http://db.cuetools.net/lookup2.php'
    params = {
        'version': '3',
        'ctdb': '1',
        'metadata': 'fast', # fast, default, or extensive
        'fuzzy': '1',
        'toc': ':'.join(map(str, toc)),
    }

    resp = requests.get(url, params)
    resp.raise_for_status()

    ns = {'Z': 'http://db.cuetools.net/ns/mmd-1.0#'}

    root = ElementTree.fromstring(resp.content)
    assert root.tag == '{http://db.cuetools.net/ns/mmd-1.0#}ctdb', root.tag

    crcinfo = []
    for entry in root.iterfind('Z:entry', ns):
        crcinfo.append(CTDBEntry(entry.get('confidence'), entry.get('crc32'), entry.get('stride'), entry.get('trackcrcs', '').split()))

    return crcinfo


if __name__ == '__main__':
    main()
