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
        if args.tags or args.import_:
            # we're going to add tags later, so just clear the tags dict for now
            # (if there are no tags yet, do nothing)
            if f.tags is not None:
                f.tags.clear()
            # fallthrough...
        else:
            # we're only deleting, so call f.delete() and quit.
            # this will remove the entire APEv2 chunk
            # it does nothing if f.tags is not set
            f.delete()
            return

    if not args.tags and not args.import_:
        return

    if f.tags is None:
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
