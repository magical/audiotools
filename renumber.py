#!/usr/bin/python

import sys
import subprocess

def save_tracknumber(filename, n, total):
    subprocess.call([
        "metaflac",
        "--remove-tag=TRACKNUMBER",
        "--remove-tag=TRACKTOTAL",
        "--set-tag=TRACKNUMBER="+str(n),
        "--set-tag=TRACKTOTAL="+str(total),
        filename,
    ])

def main():
    filenames = sys.argv[1:]

    if not filenames:
        print("Usage: retitle.py files...")
        sys.exit(1)

    for n, filename in enumerate(filenames):
        save_tracknumber(filename, n+1, len(filenames))

if __name__ == '__main__':
    main()
