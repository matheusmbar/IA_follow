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

class point:
    INIT = (-5)
    def __init__ (self, x,y):
        self.x = int(round(x,0))
        self.y = int(round(y,0))
        self.value = self.INIT
    def __repr__(self):
        return "X:{}, Y={}".format(self.x, self.y)
    def __str__(self):
        return "X:{}, Y={}".format(self.x, self.y)
    
    