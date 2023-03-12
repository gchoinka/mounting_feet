import os
import shutil

from solid2 import *
from math import sin


def square_with_cut_corners(width, depth, cutoff_length):
    a = sin(math.pi / 4) / sin(math.pi / 2) * cutoff_length
    points = [[-depth / 2, -width / 2 + a], [-depth / 2 + a, -width / 2], [width / 2 - a, -width / 2],
              [width / 2, -width / 2 + a], [width / 2, width / 2 - a], [width / 2 - a, width / 2],
              [-depth / 2 + a, width / 2], [-depth / 2, width / 2 - a]]
    return linear_extrude(0.01)(polygon(points))


def screw_place():
    h = 2.5
    r = 12.5 / 2
    return (cylinder(r2=12.5 / 2, r1=r * 1.25, h=h, center=True) + cylinder(r=4 / 2, h=30, center=True, _fn=20)).up(
        h / 2 - 0.1)


def flap_raw(feet_width, edge_depth, inside_depth, flap_width, flap_height, feet_height):
    p = [(feet_width / 2 - edge_depth, -feet_width / 2),
         (feet_width / 2, -feet_width / 2),
         (feet_width / 2, -feet_width / 2 + flap_width + 3),
         (feet_width / 2 - 3, -feet_width / 2 + flap_width),
         (feet_width / 2 - inside_depth, -feet_width / 2 + flap_width)]
    s = linear_extrude(flap_height + 0.05)(polygon(points=p))
    base = s.up(feet_height).down(flap_height)
    front_slope = s.rotate([20, 0, 0]).up(feet_height + 11).translate([0, -3, 0]).down(flap_height / 2 + 0.25)
    side_slope = s.rotate([0, 5, 0]).up(feet_height + 0.5).left(-0.1).down(flap_height / 2)
    return base + front_slope + side_slope


# TODO: remove feet_height, add front_slope and side_slope and replace flap_raw
def flap_raw_wip(edge_depth, inside_depth, flap_width, flap_height, feet_height):
    p = [(- edge_depth, 0),
         (0, 0),
         (0, flap_width + 3),
         (- 3, flap_width),
         (- inside_depth, flap_width)]
    s = linear_extrude(flap_height + 0.05)(polygon(points=p))
    base = s.up(feet_height).down(flap_height)
    return base


def feet():
    feet_height = 11.5
    top_square_width = 84
    top_width = top_square_width
    top_depth = top_square_width

    bottom_square_xy = 72
    bottom_width = bottom_square_xy
    bottom_depth = bottom_square_xy
    top_corner_cutoff_length = 10
    bottom_corner_cutoff_length = 6
    flap_height = 4
    flap_width = 13
    flap_edge_depth = 37
    flap_inside_depth = 25
    depth_reduction = 74

    top_surface = square_with_cut_corners(top_width, top_depth - depth_reduction, top_corner_cutoff_length).up(
        feet_height)

    bottom_surface = square_with_cut_corners(bottom_width, bottom_depth - depth_reduction, bottom_corner_cutoff_length)

    feet_mold = hull()(top_surface, bottom_surface)

    flap = flap_raw(top_width, flap_edge_depth, flap_inside_depth, flap_width, flap_height, feet_height)

    screws = {}
    screws['front'] = screw_place().translate([top_width / 2 - 13, top_width / 2 - 13 - 4, 0])
    screws['middle'] = screw_place().translate([9, top_width / 2 - 13 - 0.5, 0])
    screws['back'] = screw_place().translate([17.5, top_width / 2 - 13 - 10, 0])

    all_screws = screws['front'] + screws['middle'] + screws['back']

    feet_wide = feet_mold - flap - flap.mirrorY() - all_screws - all_screws.mirrorY()

    feet_slim = feet_wide.translate([0, top_width / 2 - 13 - 10, 0]) - cube([top_width, top_width, feet_height + 0.1]).down(
        0.05).left(5)

    feet_slim = feet_slim + feet_slim.mirrorY()

    return [(feet_wide, "feet"), (feet_slim, "feet_slim")]


def main(output_scad_basename, output_stl_basename):
    to_output = feet()
    if output_scad_basename is not None:
        for obj, filename_prefix in to_output:
            filename = output_scad_basename + filename_prefix + ".scad"
            obj.save_as_scad(filename)

    if output_stl_basename is not None:
        for obj, filename_prefix in to_output:
            filename = output_scad_basename + filename_prefix + ".stl"
            obj.save_as_stl(filename)


if __name__ == "__main__":
    skip_stl = False  # creating the stl takes more time and prints stuf on stdout, so you may disable it
    build_path = os.path.dirname(os.path.realpath(__file__))
    output_path = os.path.abspath(os.path.join(build_path, '..', 'build')) + os.path.sep
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    stl_output_path = output_path
    if shutil.which("openscad") is None or skip_stl:
        stl_output_path = None
    main(output_scad_basename=output_path, output_stl_basename=stl_output_path)
