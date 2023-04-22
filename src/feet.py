import dataclasses
import os
import shutil
from typing import List, Any

from solid2 import *
from math import sin, pi

unprintable_thickness = 0.01

def half(v):
    return v / 2


def square_with_cut_corners(width, depth, cutoff_length):
    a = sin(pi / 4) / sin(pi / 2) * cutoff_length
    points = [(-depth / 2, -width / 2 + a), (-depth / 2 + a, -width / 2), (width / 2 - a, -width / 2),
              (width / 2, -width / 2 + a), (width / 2, width / 2 - a), (width / 2 - a, width / 2),
              (-depth / 2 + a, width / 2), (-depth / 2, width / 2 - a)]
    return linear_extrude(unprintable_thickness)(polygon(points))


def screw_negative_with_washer():
    h = 3.5
    washer_r = 12.5 / 2
    screw_r = 3 / 2
    washer = cylinder(r2=washer_r, r1=washer_r * 1.25, h=h, center=True)
    screw = cylinder(r=screw_r, h=30, center=True,_fn=20)
    return (washer + screw).up(h / 2)


def screw_negative():
    h = 3.5
    head_r = 7.5 / 2
    screw_r = 3 / 2
    head = cylinder(r2=screw_r, r1=head_r, h=h, center=True)
    screw = cylinder(r=screw_r, h=30, center=True, _fn=20)
    return (head + screw).up(h / 2)


def make_flap(feet_width, edge_depth, inside_depth, flap_width, flap_height, feet_height, clearance, with_slopes=True):
    p = [(feet_width / 2 - edge_depth - clearance, -feet_width / 2 - clearance),
         (feet_width / 2 + clearance, -feet_width / 2 - clearance), ]
    if with_slopes:
        p += [(feet_width / 2 + clearance, -feet_width / 2 + flap_width + 3 + clearance * 2),
              (feet_width / 2 - 3 - clearance, -feet_width / 2 + flap_width + clearance)]
    else:
        p += [(feet_width / 2 + clearance, -feet_width / 2 + flap_width + clearance)]
    p += [(feet_width / 2 - inside_depth - clearance, -feet_width / 2 + flap_width + clearance)]

    s = linear_extrude(flap_height + 0.05 + clearance)(polygon(points=p))
    wing = s.up(feet_height).down(flap_height + clearance).left(clearance).forward(clearance)
    if with_slopes:
        side_slope = s.rotate([20, 0, 0]).up(feet_height + 11).translate([0, -3, 0]).down(flap_height / 2 + 1)
        front_slope = s.rotate([0, 5, 0]).up(feet_height + 0.5).left(-0.1).down(flap_height / 1.5)
        wing = wing + front_slope + side_slope
    return wing


def make_feet(breaking_point=True, with_slopes=True, with_screws=True, shorten=True, with_flaps=True, clearance=0):
    feet_height = 11.5 - clearance
    top_square_width = 84 - clearance
    top_width = top_square_width
    top_depth = top_square_width

    bottom_square_xy = 72 - clearance
    bottom_width = bottom_square_xy
    bottom_depth = bottom_square_xy
    top_corner_cutoff_length = 10
    bottom_corner_cutoff_length = 6
    flap_height = 4.5
    flap_width = 13.75
    flap_edge_depth = 37
    flap_inside_depth = 25
    if shorten:
        depth_reduction = 74
    else:
        depth_reduction = 0

    top_surface = square_with_cut_corners(top_width, top_depth - depth_reduction, top_corner_cutoff_length).up(
        feet_height)

    bottom_surface = square_with_cut_corners(bottom_width, bottom_depth - depth_reduction, bottom_corner_cutoff_length)

    feet_mold = hull()(top_surface, bottom_surface)

    flap = make_flap(top_width, flap_edge_depth, flap_inside_depth, flap_width, flap_height, feet_height, clearance,
                     with_slopes)

    screws = {}
    screws['front'] = screw_negative_with_washer().translate([top_width / 2 - 13, top_width / 2 - 13 - 4, 0])
    screws['middle'] = screw_negative_with_washer().translate([9, top_width / 2 - 13 - 0.5, 0])
    screws['back'] = screw_negative_with_washer().translate([17.5, top_width / 2 - 13 - 10, 0])

    all_screws = screws['front'] + screws['middle'] + screws['back']

    if with_flaps:
        feet = feet_mold - flap - flap.mirrorY()
    else:
        feet = feet_mold

    if with_screws:
        feet = feet - all_screws - all_screws.mirrorY()
    if breaking_point:
        breaking_point_bottom = cube([bottom_depth / 2, 21, 0.1], center=True).right(bottom_width / 4)
        breaking_point_top = cube([top_depth / 2 + 10, 0.1, 0.1], center=True).right(bottom_width / 4).up(
            feet_height - 1)

        breaking_point = hull()(breaking_point_top, breaking_point_bottom)
        feet -= breaking_point
    return feet


def make_shoe(clearance, flipt_to_print=True, shorten=True):
    bottom_layer_height = 0
    rim_with = 25
    left_right_rim_with = 18.5
    feet_height = 11.5 - bottom_layer_height
    top_square_width = 84
    top_width = top_square_width + left_right_rim_with
    top_depth = top_square_width + rim_with

    top_surface = cube([top_depth, top_width, unprintable_thickness], center=True).up(feet_height)
    bottom_surface = cube([top_depth + feet_height, top_width, unprintable_thickness], center=True)

    shoe_mold = hull()(top_surface, bottom_surface)
    feet_negative = make_feet(breaking_point=False, with_screws=False, with_slopes=False, shorten=False,
                              clearance=-0.25)
    feet_negative = feet_negative.up(bottom_layer_height - 0.1)

    shoe = shoe_mold - feet_negative

    if shorten:
        top_surface = square_with_cut_corners(top_width, top_depth, 25).up(feet_height)
        bottom_surface = square_with_cut_corners(top_width, top_depth, 25).down(0.1)

        cutoff = hull()(top_surface, bottom_surface).left(top_depth / 2 - 7)
        cutoff += cube([top_depth, top_width, feet_height + 2], center=True).up(feet_height / 2).left(
            top_depth / 2 + 10)
        shoe -= cutoff

    screws = screw_negative_with_washer().mirrorZ().translate([20, 42, feet_height + 0.5])
    screws += screw_negative_with_washer().mirrorZ().translate([38, 39, feet_height + 0.5])
    screws += screw_negative_with_washer().mirrorZ().translate([49, 15, feet_height + 0.5])
    screws += screw_negative().mirrorZ().translate([0, 47, feet_height + 0.5])
    screws += screw_negative().mirrorZ().translate([-30, 47, feet_height + 0.5])
    screws += screw_negative_with_washer().mirrorZ().translate([-48, 39, feet_height + 0.5])
    screws += screw_negative_with_washer().mirrorZ().translate([-48, 15, feet_height + 0.5])

    shoe = shoe - screws - screws.mirrorY()
    a = feet_height
    b = feet_height / 2
    c = math.sqrt(a ** 2 + b ** 2)
    alpha = math.asin(a / c) / pi * 180 if flipt_to_print else 0
    shoe = shoe.rotate([0, -alpha + 180, 90])

    return shoe, {"width": top_width, "depth": top_depth}


def make_double_shoe(clearance):
    shoe_left = make_shoe(clearance=1, flipt_to_print=True)
    shoe_right = make_shoe(clearance=1, flipt_to_print=True)
    double_shoe = shoe_left[0].left(shoe_left[1]["width"] / 2) + shoe_right[0].right(shoe_right[1]["width"] / 2)
    return double_shoe


def main(output_scad_basename, output_stl_basename):
    to_output = [
        (make_feet(breaking_point=True, with_screws=True, with_slopes=True, shorten=True, clearance=0), "feet")]
    to_output += [(make_shoe(clearance=1)[0], "shoe")]
    to_output += [(make_double_shoe(clearance=1), "shoe_pair")]
    if output_scad_basename is not None:
        for obj, filename_prefix in to_output:
            filename = output_scad_basename + filename_prefix + ".scad"
            obj.save_as_scad(filename)

    if output_stl_basename is not None:
        for obj, filename_prefix in to_output:
            filename = output_scad_basename + filename_prefix + ".stl"
            obj.save_as_stl(filename)


if __name__ == "__main__":
    skip_stl = False  # creating the stl takes more time and prints stuff on stdout, so you may disable it
    build_path = os.path.dirname(os.path.realpath(__file__))
    output_path = os.path.abspath(os.path.join(build_path, '..', 'build')) + os.path.sep
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    stl_output_path = output_path
    if shutil.which("openscad") is None or skip_stl:
        stl_output_path = None
    main(output_scad_basename=output_path, output_stl_basename=stl_output_path)
