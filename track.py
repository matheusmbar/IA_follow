

import numpy as np
from PIL import Image
import time
import psutil
import pygame
from neural import *
from robot import *

def show_image_and_close(image, seconds):
    image.show()
    # display image for 2 seconds
    time.sleep(seconds)

    # hide image
    for proc in psutil.process_iter():
        if proc.name() == "display":
            proc.kill()

def put_circle_over_image (x, y, radius, color,win):
    pygame.draw.circle(win, color, (x,y), int(radius))
    pygame.display.update()

def put_square_over_image (x, y, size, color,win):
    pygame.draw.rect(win, color, (x,y, size, size))
    pygame.display.update()

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



class track:
    OFF_TRACK = (-1)
    ON_TRACK = (1)

    START_VALUE = (-2)
    EMPTY_DISTANCE = (-10)
    END_VALUE = (0)


    START_COLOR     = (0,255,0)
    END_COLOR       = (255,0,0)
    OFF_TRACK_COLOR = (0,0,0)
    ON_TRACK_COLOR  = (255,255,255)

    

    def __init__(self, image):
        self.end_points = list()
        self.shortest_distance = None
        self.distances_plot = None
        self.start_point = None
        self.from_image(image)
        self.win = pygame.display.set_mode((self.size_x, self.size_y))


    def calc_distances (self, print_steps=False):
        print("\nStarting to calculate distances")
        finished = False
        self.distances = np.array(self.path)
        for cell in np.nditer(self.distances, op_flags=['readwrite']):
            if cell == self.ON_TRACK:
                cell[...] = self.EMPTY_DISTANCE
            elif cell == self.START_VALUE:
                cell[...] = self.START_VALUE
            else:
                cell[...] = self.OFF_TRACK

        for end in self.end_points:
            self.set_distance(end, self.END_VALUE)

        max_x = self.size_x - 1
        max_y = self.size_y - 1

        next_points = list(self.end_points)

        while (finished == False):
            if (print_steps):
                self.print_distances()
        
            now_points = list(next_points)
            next_points = list()

            for p in now_points:

                p_dist = self.get_distance(p)
                neighbors = ((-1,0), (1,0), (0,-1), (0,1))

                for dx,dy in neighbors:
                    x = p.x + dx
                    y = p.y + dy
                    if x < 0 or x >= self.size_x or y < 0 or y >= self.size_y:
                        continue
                    else:
                        this_p = point (x,y)
                        this_distance = self.get_distance(this_p) 
                        if this_distance == self.OFF_TRACK:
                            continue
                        if this_distance > 0:    #calculated
                            continue
                        if this_distance == self.END_VALUE:
                            continue
                        if this_distance == self.START_VALUE:
                            if (self.shortest_distance == None):
                                self.shortest_distance = p_dist
                            continue

                        self.set_distance(this_p, p_dist + 1)
                        next_points.append(this_p)
            
            self.max_distance = self.distances.max()

            if (len(next_points) == 0):
                finished = True
        print (self.distances)

    def set_start_point (self, start_point):
        self.start_point = start_point

    def set_end (self,end_points):
        for p in end_points:
            self.end_points.append(p)
        print (end_points)

    def get_distance (self, point):
        if point.x > self.size_x or point.y > self.size_y or \
            point.x < 0 or point.y < 0:
            return None
        return self.distances[int(point.y)][int(point.x)]

    def set_distance (self, point, value):
        self.distances[point.y][point.x] = value

    def get_path (self, point):
        if point.x >= self.size_x or point.y >= self.size_y or \
            point.x < 0 or point.y < 0:
            return self.OFF_TRACK
        return self.path[int(point.y)][int(point.x)]

    def set_path (self, point, value):
        self.path[point.y][point.x] = value

    def from_image (self, track_image):
        self.size_x = track_image.size[0]
        self.size_y = track_image.size[1]
        self.image = track_image.copy()
        self.path = np.ones((self.size_y, self.size_x)) * self.OFF_TRACK

        for x in range(self.size_x):
            for y in range(self.size_y):
                p = point (x,y)
                pix = self.image.getpixel((x,self.size_y - 1 - y))
                if pix == self.START_COLOR:
                    if self.start_point == None:
                        self.start_point = p
                    self.set_path(p, self.ON_TRACK)
                    continue
                if pix == self.END_COLOR:
                    self.set_path(p, self.END_VALUE)
                    self.end_points.append(p)
                    continue
                if pix == self.ON_TRACK_COLOR:
                    self.set_path(p, self.ON_TRACK)
                    continue
                if pix == self.OFF_TRACK_COLOR:
                    self.set_path(p, self.OFF_TRACK)
                    continue

        #print (self.path)
        self.calc_distances()

    def print_distances(self):
        if self.distances_plot == None:
            print("\nPreparing to print distances")
            print ("max distance:", self.max_distance)
            print ("min distance:", self.shortest_distance)
            color_gain = (255 - 40) / self.max_distance
            self.win.fill((0,0,0))
            for x in range(self.size_x):
                for y in range(self.size_y):
                    p = point(x,y)
                    dist = self.get_distance(p)
                    if (dist > 0):
                        R = (int(dist * color_gain) + 40)
                        color = (R,40,40)
                        pygame.draw.rect(self.win,color,(x,self.size_y - 1 - y,1,1))
            self.distances_plot = pygame.Surface.copy(self.win)
        else:
            self.win.blit(self.distances_plot,(0,0))
        pygame.display.update()


    def print_robots_over_distances (self, robots, print_sensors=False):
        self.print_distances()
        for r in robots:
            if (print_sensors):
                for s in r.calculate_sensor_positions():
                    if (self.get_path(s)) == self.ON_TRACK:
                        color = (0,0,255)
                    else:
                        color = (0,255,255)
                    put_circle_over_image(s.x, self.size_y - 1 - s.y, 5, color,self.win)
                    
            if (r.alive):
                center_color = r.color
            else:
                center_color = [c * 0.5 for c in r.color]
            put_circle_over_image(r.position.x, self.size_y -1 - r.position.y, 5, center_color,self.win)



def main():

    # filename = 'tracks/track_10x10.png'
    # filename = 'tracks/track_10x10b.png'
    # filename = 'tracks/track_100x100.png'
    #filename = 'tracks/track_100x100_simple.png'
    #filename = 'tracks/track_100x100_B.png'
    filename = 'tracks/track_100x100_C.png'
#    filename = 'tracks/track_100x100_line.png'
    #filename = 'tracks/track_100x100_s_curve.png'
    #filename = 'tracks/track_1000x1000_u_curve.png'
    #filename = 'tracks/track_1000x1000_s_curve.png'
#    filename = 'tracks/track_1000x1000_s_curve2.png'
    # filename = 'tracks/track_100x100_white.png'
    # filename = 'tracks/track_100x100_crazy.png'

    pygame.init()

    im = Image.open(filename)
    #show_image_and_close(im.resize((1000,1000)),2)


    t = track(im.resize((1000,1000)))

    start_pos = t.start_point
    start_heading = robot.HEADING_MINUS_X

    t.print_distances()

    indiv = 1000
    max_gen = 50

    neurals = list()
    for n in range(indiv):
        #neurals.append(network (11,(4,4)))
        neurals.append(network (11,(4,4)))

    robots = list()
    for i in range (indiv):
        r = robot (start_pos, start_heading, 8,color=robot.GREEN,sensors_pitch=20,sensors_dist=100)
        r.set_path_read_func(t.get_path)
        r.set_path_distance_func(t.get_distance)
        r.set_control_func(neurals[i].evaluate)
        r.set_control_unit(neurals[i])
        robots.append(r)

    generation = 0
    for g in range (max_gen):
        print ("Starting generation {}".format(generation))
        for r in robots:
            r.reset(start_pos, start_heading)

        step = 0
        alive = True
        stalled_count = 0
        while(alive):
            #t.print_robots_over_distances(robots,print_sensors=False)
            #if (step%20 == 0):
            #    t.print_robots_over_distances(robots,print_sensors=False)
            step += 1
            #print ("step:",step)
            alive = 0
            moved = False
            for r in robots:
                r.run()
                if (r.alive):
                    alive += 1
                moved |= r.moved 
                # print("x: {: 3}\ty: {: 3}\tdist: {: 4}".format(r.position.x,r.position.y,r.get_distance_to_finish()))
            #print ("Alive:",alive)

            if moved:
                stalled_count = 0
            else:
                stalled_count += 1
                if (stalled_count > 10):
                    print ("Stalled for {} steps. Interrupting generation here")
                    break



        distances = list()
        all_distances = list()

        best_robot = None
        for r in robots:
            dist = r.get_last_distance_to_finish()
            all_distances.append(dist)
            if (dist > 0):
                distances.append(dist)

                if best_robot == None:
                    best_robot = r 
                elif dist < best_robot.get_last_distance_to_finish():
                    best_robot = r

        if (len(distances) == 0):
            print("Best distances list is empty. This is the list of all distances:")
            for d in all_distances:
                print (d)
            exit()
        
        if (best_robot == None):
            best_robot = robots[0]
            best_robot.control_unit.set_gains(None)

        distances.sort()
        distances.reverse()
        for d in distances[-5:]:
            print (d)

        print ("#"*40)
        print ("\nEnded generation {}".format(generation))
        print ("Best robot got to distance {}".format(best_robot.get_last_distance_to_finish()))
        #time.sleep(0.2)
        print ("#"*40)
        t.print_robots_over_distances(robots,print_sensors=False)
        generation += 1

        best_robot_gains = list(best_robot.control_unit.get_gains())
        robots[0].control_unit.set_gains(best_robot_gains) 
        for r in robots[1:]:
            r.control_unit.set_gains(mutation(best_robot_gains))

        #zz = input("press enter")

    t.print_robots_over_distances(robots,print_sensors=True)

    # print (p.get_last_distance_to_finish())
    # print (q.get_last_distance_to_finish())
    zz = input("press enter")
    t.print_robots_over_distances(robots,print_sensors=True)
    zz = input("press enter")
    
    
    pygame.quit()
    exit()


if __name__ == "__main__":
   try:
      main()
   except KeyboardInterrupt:
      # do nothing here
      pygame.quit()
      exit()