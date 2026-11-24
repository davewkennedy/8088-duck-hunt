"""Regenerate every figure and the custom symbol library.
    python build_all.py      (then: bash ../tools/render.sh)"""
import glob
import importlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from kgen import IC, write_lib  # noqa: E402

syms = {}
for path in sorted(glob.glob(os.path.join(HERE, 'fig*_*.py'))):
    mod = importlib.import_module(os.path.basename(path)[:-3])
    print(mod.build())
    for v in vars(mod).values():
        if isinstance(v, IC):
            syms[v.name] = v
import common  # noqa: E402
syms[common.LS138.name] = common.LS138
lib = os.path.join(common.OUT, 'skeet8088.kicad_sym')
write_lib(lib, syms.values())
print(lib, '-', ', '.join(sorted(syms)))
