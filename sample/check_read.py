#!/usr/bin/env python3

from ase.io import read
from pprint import pprint

file = "espresso_scf.pwo"
x = read(file)
x.get_dipole_moment()
pprint(x.get_dipole_moment())
