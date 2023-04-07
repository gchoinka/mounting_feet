import os
import shutil

from solid2 import *
from math import sin, pi


def drill_patter():
    pattern0 = cylinder(r=6/2, h=1)

    return [(pattern0, "pattern0"), ]

def main(output_scad_basename, output_stl_basename):
    to_output = drill_patter()
    if output_scad_basename is not None:
        for obj, filename_prefix in to_output:
            filename = output_scad_basename + filename_prefix + ".scad"
            obj.save_as_scad(filename)

    if output_stl_basename is not None:
        for obj, filename_prefix in to_output:
            filename = output_scad_basename + filename_prefix + ".stl"
            obj.save_as_stl(filename)


if __name__ == "__main__":
    skip_stl = True  # creating the stl takes more time and prints stuf on stdout, so you may disable it
    build_path = os.path.dirname(os.path.realpath(__file__))
    output_path = os.path.abspath(os.path.join(build_path, '..', 'build')) + os.path.sep
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    stl_output_path = output_path
    if shutil.which("openscad") is None or skip_stl:
        stl_output_path = None
    main(output_scad_basename=output_path, output_stl_basename=stl_output_path)