import re, sys, itertools, operator, argparse
parser = argparse.ArgumentParser()
parser.add_argument('-c', '--channels', type=int, default=2)
parser.add_argument('-b', '--bitdepth', type=int, default=24)
parser.add_argument('-r', '--rate', type=int, default=96000)
parser.add_argument('--sox', action='store_true')
args = parser.parse_args()
def parse(s): return round((sum(itertools.starmap(operator.mul, zip(map(int, s[:s.index('.')].split(':')), [60*60, 60, 1]))) + float(s[s.index('.'):])) * args.rate)
if args.sox:
    chaps = []
    for line in sys.stdin:
        if '<ChapterTimeEnd>' in line:
            m = re.search(r'..:..:..\.[0-9]*', line)
            chaps.append(parse(m.group(0)))
    pos = 0
    trims = []
    for i, x in enumerate(chaps):
        len = x - pos
        if i != 0:
            print(" : newfile : ", end="")
        print("trim 0 {}s".format(int(len)), end="")
        pos = x
else:
    for line in sys.stdin:
        if '<ChapterTimeStart>' in line:
            m = re.search(r'..:..:..\.[0-9]*', line)
            print(parse(m.group(0)) * args.channels * (args.bitdepth//8))
