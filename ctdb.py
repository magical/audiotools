#!/usr/bin/env python3
import sys
import os
import argparse
import subprocess
import sqlite3
import zlib
from collections import namedtuple

import wave
import mutagen.flac
import requests
from xml.etree import ElementTree

CTDBEntry = namedtuple("CTDBEntry", "confidence, crc32, stride, trackcrcs")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--pregap", type=int, help="pregap frames")
    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    toc = get_toc(args.files)

    if args.pregap:
        toc[0] = args.pregap

    info = lookup_toc(toc)
    if not info:
        print("album not in database")
        sys.exit(1)

    os.environ['PATH'] += os.pathsep + os.path.dirname(__file__)
    effects = []
    if args.pregap:
        effects += ["trim", str(args.pregap*588)+"s"]
    p1 = subprocess.Popen(["sox", "--no-clobber"] + args.files + ["-t", "s16", "-"] + effects, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
    p2 = subprocess.Popen(["ctdb_crc32"] + [entry.crc32 for entry in info], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    p1.stdout.close()
    out = p2.stdout.read()
    p2.stdout.close()
    p2.wait()
    p1.wait()

    # TODO: note highest confidence entry

    matches = 0
    for line in out.decode().splitlines():
        offset, c = line.split()
        for entry in info:
            if entry.crc32 == c or int(entry.crc32, 16) == int(c, 16):
                print(f"Found match at offset {offset} with confidence {entry.confidence} and CRC {entry.crc32}")
                matches += 1

    if not matches:
        print(f"No matches found")
        sys.exit(1)

def get_toc(tracks):

    toc = []
    t = 0
    for filename in tracks:
        toc.append(t // 588)

        if filename.endswith(".wav"):
            f = wave.open(filename, 'rb')
            if f.getframerate() != 44100 or f.getnchannels() != 2:
                raise Exception("%s: not a 44100 Hz stereo track" % filename)
            length = f.getnframes()
            f.close()
        else:
            f = mutagen.flac.Open(filename)
            if f.info.sample_rate != 44100 or f.info.channels != 2:
                raise Exception("%s: not a 44100 Hz stereo track" % filename)

            length = f.info.total_samples * 44100 // f.info.sample_rate
        t += length
    toc.append((t + 588 - 1) // 588)

    return toc

def lookup_toc(toc):
    tocstr = ':'.join(str(x) for x in toc)

    print(f"info: toc={tocstr}", file=sys.stderr)

    add_to_cache = False
    content = lookup_from_cache(tocstr)
    if content == None:
        add_to_cache = True
        content = lookup_from_web(tocstr)
        if not content:
            return None

    info = parse_ctdb_xml(content)

    if info and add_to_cache:
        save_to_cache(tocstr, content)

    return info

db = None
def open_db():
    global db
    if db != None:
        return db

    cachedir = os.environ.get("XDG_CACHE_HOME")
    if not cachedir:
        cachedir = os.path.expanduser("~/.cache")
    cachedir  = os.path.join(cachedir, "ctdb")
    try:
        os.mkdir(cachedir)
    except FileExistsError:
        pass

    dbfile = os.path.join(cachedir, "ctdb.sqlite")
    db = sqlite3.connect(dbfile)
    ver, = db.execute("PRAGMA user_version;").fetchone()

    if ver < 1:
        db.executescript("""
            BEGIN;
            CREATE TABLE IF NOT EXISTS ctdb (
                toc TEXT,
                content BLOB,
                mtime TIMESTAMP DEFAULT current_timestamp
            );
            CREATE UNIQUE INDEX IF NOT EXISTS ctdb_index ON ctdb (toc);
            PRAGMA user_version = 1;
            COMMIT;
        """).close()

    return db

def lookup_from_cache(tocstr):
    db = open_db()
    cur = db.execute("SELECT content FROM ctdb WHERE toc = ?", (tocstr,))
    row = cur.fetchone()
    cur.close()
    if row == None:
        return None
    print("info: found in cache", file=sys.stderr)
    return zlib.decompress(row[0])

def save_to_cache(tocstr, content):
    db = open_db()
    with db:
        db.execute(
            "INSERT INTO ctdb(toc, content) VALUES (:1, :2)" +
            "ON CONFLICT(toc) DO UPDATE SET content = :2, mtime = current_timestamp",
            (tocstr, zlib.compress(content))).close()

def lookup_from_web(tocstr):
    print("info: fetching from web", file=sys.stderr)
    url = 'http://db.cuetools.net/lookup2.php'
    params = {
        'version': '3',
        'ctdb': '1',
        'metadata': 'fast', # fast, default, or extensive
        'fuzzy': '1',
        'toc': tocstr,
    }

    resp = requests.get(url, params)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()

    return resp.content

def parse_ctdb_xml(content):
    ns = {'Z': 'http://db.cuetools.net/ns/mmd-1.0#'}

    root = ElementTree.fromstring(content)
    assert root.tag == '{'+ns['Z']+'}ctdb', root.tag

    crcinfo = []
    for entry in root.iterfind('Z:entry', ns):
        crcinfo.append(CTDBEntry(entry.get('confidence'), entry.get('crc32'), entry.get('stride'), entry.get('trackcrcs', '').split()))

    return crcinfo


if __name__ == '__main__':
    main()
