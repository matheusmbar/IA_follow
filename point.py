#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 26 18:52:08 2019

@author: matheus
"""

#  The first dimension value in a numpy array is in Y direction
#  when array is printed
#
#  array position [0][0] is top left member


class Point:
    """The first dimension value in a numpy array is in Y direction
    when array is printed
    \narray position [0][0] is top left member"""
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return str(self)

    def __str__(self):
        return "X:{: 3}    Y:{: 3}".format(self.x, self.y)

    def __eq__(self, other):
        if not isinstance(other, Point):
            return False
        return (self.x == other.x) and (self.y == other.y)

    def __ne__(self, other):
        if not isinstance(other, Point):
            return False
        return not (self == other)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __radd__(self, other):
        if (not isinstance(other, Point)):
            return self
        return self + other

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def get_xy(self):
        return (self.x, self.y)

    def get_int_xy(self):
        return (self.int_x(), self.int_y())

    def int_x(self):
        return int(round(self.x))

    def int_y(self):
        return int(round(self.y))

    def copy(self):
        return Point(self.x, self.y)

    def copy_int(self):
        return Point(self.int_x(), self.int_y())


class point(Point):
    pass
