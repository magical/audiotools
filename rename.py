#!/usr/bin/python3
import argparse
import os
import re
import subprocess
import sys

this_dir = os.path.dirname(__file__)

def deprefix(s, prefix):
    if s.lower().startswith(prefix.lower()):
        s = s[len(prefix):]
    return s

def read_flac_tag(filename, tag):
    try:
        title = subprocess.check_output([
            "metaflac",
            "--show-tag="+tag,
            filename,
        ],
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return ""

    title = title.decode("utf-8")
    title = deprefix(title, tag+"=")
    title = title.strip("\n\t ")
    return title

def read_ape_tag(filename, tag):
    try:
        title = subprocess.check_output([
            "python3",
            os.path.join(this_dir, "ape.py"),
            "--get="+tag,
            filename,
        ])
    except subprocess.CalledProcessError:
        return ""

    title = title.decode("utf-8")
    title = title.strip("\n\t ")
    return title

_opus_cache = {}
def read_opus_tag(filename, tag):
    if filename in _opus_cache:
        return _opus_cache[filename].get(tag, "")

    try:
        output = subprocess.check_output([ "opustags", filename ])
        output = output.decode('utf-8')
    except subprocess.CalledProcessError as e:
        _opus_cache[filename] = {}
        return ""
    tags = {}
    last_key = ""
    for line in output.splitlines():
        if last_key and line.startswith("\t"):
            tags[last_key] += "\n" + line[1:]
        else:
            k, _, v = line.partition('=')
            tags[k] = v
            last_key = k
    #print(tags)
    _opus_cache[filename] = tags
    return tags.get(tag, "")

def read_tag(filename, tag):
    if filename.endswith(".dts") or filename.endswith(".ac3"):
        return read_ape_tag(filename, tag)
    if filename.endswith(".opus"):
        return read_opus_tag(filename, tag)
    return read_flac_tag(filename, tag)

def read_title(filename):
    return read_tag(filename, 'TITLE')

def read_number(filename, tag):
    n = read_tag(filename, tag)
    try:
        return int(n, 10)
    except ValueError:
        return None

def clean(s, noparens=True):
    s = s.replace(": ", " - ") # A: B => A - B
    s = s.replace(":", ".") # 6:00 => 6.00
    s = s.replace("/", "-")
    s = s.replace("?", "")
    s = s.replace("*", "")
    s = s.replace("‘", "'").replace("’", "'") # Curly quotes are evil
    s = s.replace("“", "").replace("”", "").replace('"', "")
    s = s.replace("\u2014", " - ")
    s = s.replace("\u2010", "-")
    s = s.replace("…", "...")
    s = re.sub(r"[\x00-\x1F\x7F]", '', s) # Remove control chars
    if noparens:
        s = re.sub(r'\(.*\)', '', s) # Remove parentheticals
        s = re.sub(r'\[.*\]', '', s)
    s = s.rstrip('. ') # Strip trailing periods
    s = s.strip() # Strip whitespace
    return s

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--disc', action='store_true', help="prepend disc number")
    parser.add_argument('-p', '--keep-parens', dest='parens', action='store_true', help="don't strip parentheticals")
    parser.add_argument('-a', '--artists', action='store_true', help="include artist names")
    parser.add_argument('filenames', nargs='+')
    args = parser.parse_args()

    if not args.filenames:
        print("Usage: rename.py files...")
        sys.exit(1)

    renames = []
    for row, filename in enumerate(args.filenames):
        title = read_title(filename)
        if not title:
            print("No title, skipping: {!r}".format(filename))
            continue

        number = read_number(filename, 'TRACKNUMBER')
        discnumber = None
        disctotal = None
        artist = None
        if args.disc:
            discnumber = read_number(filename, 'DISCNUMBER')
            disctotal = read_number(filename, 'DISCTOTOL')
        if args.artists:
            artist = read_tag(filename, "ARTIST")

        dirname, basename = os.path.split(filename)
        _, ext = os.path.splitext(basename)

        newname = clean(title, noparens=not args.parens) + ext
        if args.artists and artist:
            newname = "{} - {}".format(artist, newname)
        if number is not None:
            newname = "{:02d} {}".format(number, newname)
            if args.disc and discnumber and disctotal != 1:
                newname = "{:d}-{}".format(discnumber, newname)

        if basename == newname:
            continue

        newpath = os.path.join(dirname, newname)

        renames.append((filename, newpath))
        print("{} => {}".format(filename, newpath))

    if not renames:
        return

    response = input("Rename these files? ")
    if response.strip().lower() not in ('y', 'yes'):
        print("OK, nevermind")
        return

    for filename, newname in renames:
        if os.path.exists(newname):
            print("Path already exists: {!r}".format(newname))
            continue
        os.rename(filename, newname)

if __name__ == '__main__':
    main()
