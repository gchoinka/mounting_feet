import math  # noqa
import multiprocessing
from enum import Enum, auto
import os
import shutil
import sys
from dataclasses import dataclass
from typing import Iterable, Tuple, Dict, List

from solid2 import cube, linear_extrude, polygon, cylinder, union, hull, scale, intersection, square, P2, P3
from solid2.core.object_base import OpenSCADObject
from pathlib import Path

SizeMM = float

unprintable_thickness: SizeMM = 0.01  #
preview_fix: SizeMM = 0.05  # add/subtract this to avoids openscad preview artefacts

y_reduction = 0

g_top_feet: P2 = (84.0, 84.0-y_reduction)
g_bottom_feet: P2 = (72.0, 72.0-y_reduction)
g_feet_height: SizeMM = 11.5

washer_r: SizeMM = 10.5 / 2
washer_r1 = washer_r
washer_r2 = washer_r * 1.25
screw_r: SizeMM = 3.5 / 2


def square_with_cut_corners(dim: P2, cutoff_length: SizeMM) -> OpenSCADObject:
    a = math.sin(math.pi / 4) / math.sin(math.pi / 2) * cutoff_length
    x, y = dim
    points = [(x / -2 + 0, y / +2 - a), (x / -2 + a, y / +2 + 0), (x / +2 - a, y / +2 + 0), (x / +2 + 0, y / +2 - a),
        (x / +2 + 0, y / -2 + a), (x / +2 - a, y / -2 + 0), (x / -2 + a, y / -2 + 0), (x / -2 + 0, y / -2 + a), ]
    return linear_extrude(unprintable_thickness)(polygon(points))


def screw_negative_with_washer() -> OpenSCADObject:
    h: SizeMM = 3.5
    washer = cylinder(r2=washer_r, r1=washer_r * 1.25, h=h, center=True)
    screw = cylinder(r=screw_r, h=30, center=True, _fn=20)
    return (washer + screw).up(h / 2)


def screw_negative() -> OpenSCADObject:
    h: SizeMM = 5
    head_r: SizeMM = 9 / 2
    head = cylinder(r2=screw_r, r1=head_r, h=h, center=True)
    screw = cylinder(r=screw_r, h=30, center=True, _fn=20)
    return (head + screw).up(h / 2)


def make_wing(feet_dim: Tuple[float, float, float], edge_depth: float, inside_depth: float,
              wing_dim: Tuple[float, float, float], clearance: float, flap_type: str = 'sloped') -> OpenSCADObject:
    p = [(feet_dim[0] / 2 - edge_depth - clearance, -feet_dim[1] / 2 - clearance),
         (feet_dim[0] / 2 + clearance, -feet_dim[1] / 2 - clearance),
         (feet_dim[0] / 2 + clearance, -feet_dim[1] / 2 + wing_dim[0] + clearance)]
    if flap_type == 'sloped':
        p += [(feet_dim[0] / 2 + clearance, -feet_dim[1] / 2 + wing_dim[0] + clearance + 3)]
        p += [(feet_dim[0] / 2 + clearance - 7.5, -feet_dim[1] / 2 + wing_dim[0] + clearance)]
        p += [(feet_dim[0] / 2 - inside_depth - clearance, -feet_dim[1] / 2 + wing_dim[0] + clearance)]

        z_slop = 4
        wing = linear_extrude(wing_dim[2] + 0.05 + clearance + z_slop)(polygon(points=p)).up(feet_dim[2]).down(
            wing_dim[2] + clearance + z_slop).left(clearance).forward(clearance)

        bottom_flap = linear_extrude(unprintable_thickness)(polygon(points=p)).up(feet_dim[2]).down(
            wing_dim[2] + clearance + z_slop).left(clearance).forward(clearance)

        p = [(feet_dim[0] / 2 - edge_depth - clearance + 1, -feet_dim[1] / 2 - clearance + 5),  # left top corner
             (feet_dim[0] / 2 + clearance - 17, -feet_dim[1] / 2 - clearance + 5), ]

        p += [(feet_dim[0] / 2 + clearance - 17, -feet_dim[1] / 2 + wing_dim[0] + clearance + 10)]
        p += [(feet_dim[0] / 2 + clearance - 17, -feet_dim[1] / 2 + wing_dim[0] + clearance + 3)]
        p += [(feet_dim[0] / 2 + clearance - 7.5 - 9, -feet_dim[1] / 2 + wing_dim[0] + clearance)]
        p += [(feet_dim[0] / 2 - inside_depth - clearance,
               -feet_dim[1] / 2 + wing_dim[0] + clearance)]  # right top corner

        bottom_flap_2 = linear_extrude(unprintable_thickness)(polygon(points=p)).up(feet_dim[2]).down(
            wing_dim[2] + clearance).left(clearance).forward(clearance)

        slope = hull()(bottom_flap, bottom_flap_2)

        return wing - slope

    elif flap_type == 'back_sloped':
        p += [(feet_dim[0] / 2 - inside_depth - clearance, -feet_dim[1] / 2 + wing_dim[0] + clearance)]

        poly = linear_extrude(unprintable_thickness)(polygon(points=p))
        top_flap = poly.translate([-clearance, clearance, feet_dim[2]])
        bottom_flap = poly.translate([-(clearance - 2), clearance, feet_dim[2] - wing_dim[2] + clearance])
        wing = hull()(top_flap, bottom_flap)
        return wing
    else:
        raise ValueError()


class SlopesMode(Enum):
    sloped = auto()
    back_sloped = auto()


@dataclass
class FeetOptions:
    breaking_point: bool = True
    slope_mode: SlopesMode = SlopesMode.sloped
    screws: bool = True
    short: bool = False # TODO rename


def make_feet(opt: FeetOptions, clearance: SizeMM = 0.0) -> OpenSCADObject:
    depth_reduction: SizeMM = 74 / 2 if opt.short else 0
    top_feet_dim: P2 = (g_top_feet[0] - clearance - depth_reduction, g_top_feet[1] - clearance )
    feet_dim = (top_feet_dim[0], top_feet_dim[1], g_feet_height - clearance)

    bottom_feet_dim: P2 = (g_bottom_feet[0] - clearance - depth_reduction, g_bottom_feet[1] - clearance )
    top_corner_cutoff_length: SizeMM = 10
    bottom_corner_cutoff_length: SizeMM = 6
    flap_edge_depth: SizeMM = 37
    flap_inside_depth: SizeMM = 25
    flap_dim: P3 = (13.75, 0, 4.5)

    top_surface = square_with_cut_corners(top_feet_dim, top_corner_cutoff_length).up(feet_dim[2])
    bottom_surface = square_with_cut_corners(bottom_feet_dim, bottom_corner_cutoff_length)

    feet_mold = hull()(top_surface, bottom_surface)

    flap_sloped = make_wing(feet_dim, flap_edge_depth, flap_inside_depth, flap_dim, clearance, 'sloped')
    flap_back_sloped = make_wing(feet_dim, flap_edge_depth, flap_inside_depth, flap_dim, clearance, 'back_sloped')

    feet = cube(0)
    if opt.slope_mode == SlopesMode.sloped:
        feet = feet_mold - flap_sloped - flap_sloped.mirrorY()
    elif opt.slope_mode == SlopesMode.back_sloped:
        feet = feet_mold - flap_back_sloped - flap_back_sloped.mirrorY()
    else:
        raise ValueError()

    if opt.screws:
        screw_pos = [[top_feet_dim[0] / 2 - 13, top_feet_dim[1] / 2 - 17, -preview_fix],
                     [top_feet_dim[0] / 2 - 32, top_feet_dim[1] / 2 - 13, -preview_fix],
                     [-bottom_feet_dim[0] / 2 + washer_r2, 0, -preview_fix],
                     [bottom_feet_dim[0] / 2 - washer_r2*2, 0, -preview_fix]]
        screws = union()(*(screw_negative_with_washer().translate(p) for p in screw_pos))
        feet = feet - screws - screws.mirrorY()
    if opt.breaking_point:
        breaking_point_bottom = cube([bottom_feet_dim[1] / 2, 21, 0.1], center=True).right(bottom_feet_dim[0] / 4)
        breaking_point_top = cube([top_feet_dim[1] / 2 + 10, 0.1, 0.1], center=True).right(bottom_feet_dim[0] / 4).up(
            feet_dim[2] - 1)

        breaking_point = hull()(breaking_point_top, breaking_point_bottom)
        feet -= breaking_point
    return feet


@dataclass
class ShoeOptions:
    shoe_top: bool = False
    flipt_to_print: bool = False
    short: bool = False


def make_shoe(opt: ShoeOptions) -> Tuple[OpenSCADObject, P2]:
    rim_with: SizeMM = 25
    left_right_rim_with: SizeMM = 18.5
    shoe_feet_height: SizeMM = g_feet_height

    shoe_top: P2 = (g_top_feet[0] + left_right_rim_with, g_top_feet[1] + rim_with)

    top_surface = cube([shoe_top[0], shoe_top[1], unprintable_thickness], center=True).up(shoe_feet_height)
    bottom_surface = cube([shoe_top[0] + shoe_feet_height, shoe_top[1], unprintable_thickness], center=True)

    shoe_mold = hull()(top_surface, bottom_surface)
    feet_negative = make_feet(
        FeetOptions(breaking_point=False, slope_mode=SlopesMode.back_sloped, screws=False, short=False, ),
        clearance=-0.35)
    feet_negative = feet_negative.up(-preview_fix)

    shoe = shoe_mold - feet_negative

    if opt.short or opt.shoe_top:
        cutoff_top_surface = square_with_cut_corners((shoe_top[0], shoe_top[1]), 29).up(shoe_feet_height)
        cutoff_bottom_surface = square_with_cut_corners((shoe_top[0], shoe_top[1]), 29).down(preview_fix)

        cutoff = hull()(cutoff_top_surface, cutoff_bottom_surface).left(shoe_top[0] / 2 - 7)
        cutoff += cube([shoe_top[0], shoe_top[1], shoe_feet_height + 2], center=True).up(shoe_feet_height / 2).left(
            shoe_top[0] / 2 + 10)
        if opt.short:
            shoe -= scale(1.001)(cutoff)
        if opt.shoe_top:
            shoe = intersection()(shoe, cutoff)

    screw_sink: SizeMM = 0.7
    washer_screw_pos = [[20, 42, shoe_feet_height + screw_sink], [38, 39, shoe_feet_height + screw_sink],
                        [49, 15, shoe_feet_height + screw_sink], [-48, 39, shoe_feet_height + screw_sink],
                        [-48, 15, shoe_feet_height + screw_sink]]
    screw_pos = [[0, 47, shoe_feet_height + screw_sink], [-30, 47, shoe_feet_height + screw_sink]]

    screws = union()(*(screw_negative_with_washer().mirrorZ().translate(p) for p in washer_screw_pos))
    screws += union()(*(screw_negative().mirrorZ().translate(p) for p in screw_pos))

    shoe = shoe - screws - screws.mirrorY()
    if opt.flipt_to_print:
        a = shoe_feet_height
        b = shoe_feet_height / 2
        c = math.sqrt(a ** 2 + b ** 2)
        alpha = math.asin(a / c) / math.pi * 180
        shoe = shoe.rotate([0, -alpha + 180, 90])

    return shoe, shoe_top


# def make_double_shoe(opt: ShoeOptions) -> OpenSCADObject:
#     shoe_left = make_shoe(opt)
#     shoe_right = make_shoe(opt)
#     double_shoe = shoe_left[0].left(shoe_left[1]["width"] / 2) + shoe_right[0].right(shoe_right[1]["width"] / 2)
#     return double_shoe


def stl_task_function(stl_task: Tuple[OpenSCADObject, str]) -> None:
    obj, filename = stl_task
    obj.save_as_stl(filename)


def main(output_scad_basename: str, output_stl_basename: str | None) -> None:
    output = [(
    make_feet(FeetOptions(breaking_point=False, slope_mode=SlopesMode.sloped, screws=True, short=True), clearance=0.0),
    "feet"), (make_shoe(ShoeOptions(short=True))[0], "shoe_short"),
        (make_shoe(ShoeOptions(short=False, shoe_top=True))[0], "shoe_top"),
        (make_shoe(ShoeOptions(short=False ))[0], "shoe_full"),  # (make_double_shoe(), "shoe_pair"),
        # (make_double_shoe(shorten=False), "shoe_pair_full"),
    ]

    stl_task: List[Tuple[OpenSCADObject, str]] = []
    all_obj: OpenSCADObject = cube(0)
    obj_distance = 55
    next_pos = [0, 0]

    for obj, filename_prefix in output:
        filename = output_scad_basename + filename_prefix + ".scad"
        stl_task.append((obj, output_scad_basename + filename_prefix + ".stl"))
        obj.save_as_scad(filename)
        all_obj += obj.left(next_pos[0]).fwd(next_pos[1])
        next_pos[0] += obj_distance
        next_pos[1] += obj_distance

    filename = output_scad_basename + f"{Path(__file__).stem}_all.scad"
    all_obj.save_as_scad(filename)
    stl_task.append((all_obj, output_scad_basename + f"{Path(__file__).stem}_all.stl"))
    if output_stl_basename is not None:
        with multiprocessing.Pool() as pool:
            pool.map(stl_task_function, stl_task)


if __name__ == "__main__":
    skip_stl: bool = True if len(sys.argv) > 1 and sys.argv[1] == "--fast" else False
    build_path: str = os.path.dirname(os.path.realpath(__file__))
    output_path: str = os.path.abspath(os.path.join(build_path, '..', 'build')) + os.path.sep
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    stl_output_path: str | None = output_path
    if shutil.which("openscad") is None or skip_stl:
        stl_output_path = None
    main(output_scad_basename=output_path, output_stl_basename=stl_output_path)
