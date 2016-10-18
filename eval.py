
from astar import AStarParser
import sys
import re
import multiprocessing
import os
import argparse
from pathlib import Path
from time import time
from ccgbank import AutoReader, get_leaves

modelpath = "model"
astarp = AStarParser(modelpath)

re_subset = {"train": re.compile(r"wsj_(0[2-9]|1[0-9]|20|21)..\.auto"),
            "test": re.compile(r"wsj_23..\.auto"),
            "val": re.compile(r"wsj_00..\.auto"),
            "all": re.compile(r"wsj_....\.auto") }

def ccgbank2raw_text(args):
    matcher = re_subset[args.subset]
    autos = []
    for root, dirs, files in os.walk(args.path):
        for autofile in files:
            if matcher.match(autofile):
                autos.append(os.path.join(root, autofile))
    n_process = multiprocessing.cpu_count()
    p = multiprocessing.Pool(n_process)
    with open(args.out, "w") as out:
        for lines in p.map(_worker, autos):
            for line in lines:
                out.write(line + "\n")


def _worker(autofile):
    res = []
    for tree in AutoReader(autofile).readall(suppress_error=True):
        sent = " ".join(map(lambda x: x.word, get_leaves(tree)))
        res.append(sent)
    return res


def predict_auto(args):
    outdir = Path(args.outdir)
    candc = Path(args.candcdir)
    scripts = (candc / "src" / "scripts" / "ccg")
    catsdir = (candc / "src" / "data" / "ccg" / "cats")
    markedup = (candc / "markedup")
    pred = (outdir / "auto_predicts.txt")
    pred_processed = (outdir / "auto_predicts_processed.txt")

    astarp = AStarParser(args.model)
    with pred.open("w") as f:
        for inp in open(args.valfile):
            res = astarp.parse(inp.strip())
            f.write(str(res) + "\n")
    cmd1 = "cat {0} | {1}/convert_auto | sed -f {1}/convert_brackets > {2}". \
        format(pred, scripts, pred_processed)

    cmd2 = "{0}/generate -j {1} {2} {3}". \
            format((candc / "bin"), catsdir, markedup, pred_processed)



parser = argparse.ArgumentParser(
            "CCG parser's evaulator")
subparsers = parser.add_subparsers()

# Creating training data from CCGBank AUTO files
parser_c = subparsers.add_parser(
        "create", help="create test data")
parser_c.add_argument("path",
        help="path to AUTO directory")
parser_c.add_argument("out",
        help="output file path")
parser_c.add_argument("--subset",
        choices=["train", "val", "test", "all"],
        default="train",
        help="train: 02-21, val: 00, test: 23, (default: train)")
parser_c.set_defaults(func=ccgbank2raw_text)

args = parser.parse_args()
args.func(args)

