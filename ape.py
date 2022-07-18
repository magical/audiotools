#!/usr/bin/env python3
import mutagen.apev2 as ape
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--tag', action='append', dest='tags', metavar="name=value", help="set tag")
    parser.add_argument('-g', '--get', action='append', dest='get', metavar="tag", help="print tag")
    # XXX these are basically different modes
    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('--delete-all', action='store_true')
    parser.add_argument('--import', dest='import_', type=argparse.FileType('r'), metavar="file")
    parser.add_argument('filename')
    args = parser.parse_args()

    f = ape.APEv2File(args.filename)

    if args.list:
        if f.tags:
            print(f.tags.pprint())
        return

    if args.get and f.tags:
        for tag in args.get:
            print(f.tags.get(tag, ''))

    if args.delete_all:
        if f.tags:
            f.tags.delete()
        # don't return; let delete_all be combined with import

    if not args.tags and not args.import_:
        return
        
    if not f.tags:
        f.add_tags()

    if args.import_:
        for line in args.import_:
            t = line.strip()
            if not t:
                continue
            if '=' not in t:
                print("invalid tag:", t)
                continue
            name, _, value = t.partition('=')
            f.tags[name] = value

    if args.tags:
        for t in args.tags:
            if '=' not in t:
                print("invalid tag:", t)
                continue
            name, _, value = t.partition('=')
            f.tags[name] = value

    f.save()

main()
