#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct 31 11:05:02 2019

@author: matheus
"""

import numpy as np


class Coordinates:
    @staticmethod
    def polar2z(r, theta):
        return r * np.exp(1j * theta)

    @staticmethod
    def z2polar(z):
        return (abs(z), np.angle(z))

    @staticmethod
    def xy2polar(x, y):
        return Coordinates.z2polar(x + y * 1j)

    @staticmethod
    def z2xy(z):
        return (np.real(z), np.imag(z))

    @staticmethod
    def polar2xy(r, theta):
        return Coordinates.z2xy(Coordinates.polar2z(r, theta))
