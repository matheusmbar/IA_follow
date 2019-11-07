#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 26 18:50:52 2019

@author: matheus
"""

import numpy as np
from point import *

def polar2z(r,theta):
    return r * np.exp( 1j * theta )

def z2polar(z):
    return ( abs(z), np.angle(z) )

def xy2polar(x,y):
    return z2polar(x + y * 1j)

def z2xy(z):
    return (np.real(z), np.imag(z))

def polar2xy(r,theta):
    return z2xy(polar2z(r,theta))


##             ^ +y
##             |
##             |
##      -x ---------> +x
##             |
##             |
##             | -y
class robot:
    # heading =      0 -> car aligned with  +X
    # heading =   pi/2 -> car aligned with  +Y
    # heading =     pi -> car aligned with  -X
    # heading = 3*pi/2 -> car aligned with  -Y
    HEADING_PLUS_X  = 0
    HEADING_PLUS_Y  = np.pi/2
    HEADING_MINUS_X = np.pi
    HEADING_MINUS_Y = 3*np.pi/2

    RED   = (255,0,0)
    GREEN = (0,255,0)
    YELLOW = (255,255,0)
    BLUE  = (0,0,255)
    WHITE = (255,255,255)

    # sensor IDs example with 8 sensors:
    #  x x x x|x x x x
    #  0 1 2 3 4 5 6 7 
    def __init__(self, init_point, init_heading, n_sensors,color=WHITE,sensors_pitch=10,sensors_dist=100):
        self.alive = True
        self.speed = 0
        self.max_speed = 2
        self.heading = init_heading
        self.position = init_point
        self.acc = 1
        self.turn_rate = np.deg2rad(2)
        self.n_sensors = n_sensors
        self.sensors_dist = sensors_dist
        self.sensors_pitch = sensors_pitch

        self.calculate_sensor_positions()
        self.control_func = self.debug_control_func
        self.color = color
        self.last_position = point(self.position.x,self.position.y)
        self.distance_to_finish = 0
        self.last_distance_to_finish = 0
        self.steps_without_moving = 0

    def get_sensor_position (self, sensor_id):
        # front sensors are numbered from left to right, with `sensors_pitch` distance between them
        # they are positioned in a line perpendicular to track direction and `sensors_dist` apart from robot's position

        #calculate sensor position without considering heading
        sensor_x = self.sensors_dist
        sensor_y = ((self.n_sensors - 1)/2 - sensor_id) * self.sensors_pitch

        #transform into polar coordinates
        z = (sensor_x + sensor_y * 1j)
        r,theta = z2polar(z)

        #sum heading to theta to calculate sensor position in reference to robot position
        new_theta = theta + self.heading
        new_z = polar2z(r,new_theta)
        #calculate final position in reference to track's origin
        final_sensor_x = round(np.real(new_z) + self.position.x)
        final_sensor_y = round(np.imag(new_z) + self.position.y)

        return point(int(final_sensor_x), int(final_sensor_y))

    def calculate_sensor_positions (self):
        self.sensor_positions = list()
        for i in range (self.n_sensors):
            self.sensor_positions.append(self.get_sensor_position(i))

        return list(self.sensor_positions)

    def set_path_read_func (self, path_read):
        self.path_read_func = path_read

    def set_path_distance_func (self, path_distance_read):
        self.path_distance_func = path_distance_read

    def debug_control_func (self, inputs):
        for i in range(len(inputs)):
            print ("[{}]: {}".format(i, inputs[i]))
        return [1,0,1,0]

    def set_control_func(self, control_func):
        self.control_func = control_func

    def set_control_unit(self, control_unit):
        self.control_unit = control_unit

    def calc_new_position(self):
        x_delta,y_delta = polar2xy(self.speed,self.heading)
        # new
        # r,theta = xy2polar(self.position.x,self.position.y)
        # new_x,new_y = polar2xy(r+self.speed,theta)
        self.position = point(self.position.x + x_delta,self.position.y + y_delta)

    def get_distance_to_finish (self):
        return self.distance_to_finish

    def get_last_distance_to_finish (self):
        if self.alive:
            return self.distance_to_finish
        return self.last_distance_to_finish

    def check_alive (self):
        if self.path_read_func(self.position) == None:
            #print ("out of bounds at: ", self.position)
            self.alive = False
        elif self.path_read_func(self.position) == -1:
            #print ("died at: ", self.position)
            self.alive = False
        elif self.steps_without_moving >= 20:
            #print ("stalled at: ", self.position)
            self.alive = False
        return self.alive

    def check_moved (self):
        if self.alive and ((self.last_position.x != self.position.x) or \
           (self.last_position.y != self.position.y)):
           self.moved = True
        else:
            self.moved = False
            self.steps_without_moving +=1
        self.last_position = point(self.position.x, self.position.y)
        return self.moved

    def calc_new_distances(self):
        if (self.alive):
            self.last_distance_to_finish = self.distance_to_finish
            self.distance_to_finish = self.path_distance_func(self.position)

    def set_position(self, new_position):
        self.position = point(new_position.x, new_position.y)

    def reset (self, start_point, start_heading):
        self.alive = True
        self.set_position(start_point)
        self.heading = start_heading
        self.speed = 0
        self.moved = False
        self.steps_without_moving = 0
        self.last_position = point(start_point.x, start_point.y)
    
    def update_fitness (self):
        self.fitness = self.get_last_distance_to_finish()
    
    def get_fitness (self):
        return self.fitness

    def run (self):
        if self.alive == False:
            return False

        inputs = list()
        inputs.append(self.speed)
        # inputs.append(self.heading)
        # inputs.append(1)
        for s in self.calculate_sensor_positions():
            inputs.append(self.path_read_func(s))

        acc,brake,left,right = self.control_func(inputs)

        if acc :
            self.speed = min(self.speed + self.acc, self.max_speed) 
        if brake:
            self.speed = max(self.speed - self.acc, (-1)*self.max_speed) 
        if left:
            self.heading += self.turn_rate
        if right:
            self.heading += self.turn_rate
        
        #limit heading to pi
        self.heading = np.remainder(self.heading, 2*np.pi)
        self.calc_new_position()
        self.check_alive()
        self.check_moved()
        if (self.alive == False):
            #print ("Returning to last alive position:", self.last_position)
            self.position = self.last_position
        self.calc_new_distances()
        #print("x: {: 3}\ty: {: 3}\tacc: {: 2.2}\tbrake: {: 2.2}\tleft: {: 2.2}\tright: {: 2.2}\tspeed: {: 2.2f}\theading: {:2.2f}"\
        #    .format(self.position.x,self.position.y,float(acc), float(brake), float(left), float(right), float(self.speed),np.rad2deg(self.heading)))
        return 
