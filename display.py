import pygame
#import random
import point
import numpy as np
from coordinates import Coordinates as coord
import itertools
from PIL import Image
from neural import network, mutation, mutation2
from progress.bar import Bar
import threading
from genetic import Genetic

#https://itch.io/game-assets/free
#http://programarcadegames.com/index.php?chapter=introduction_to_sprites&lang=en


# COLORS
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BG = (254, 254, 254)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)


class Robot(pygame.sprite.Sprite):
    """Robot object based on pygame module

      heading =      0 -> car aligned with  +X
      heading =   pi/2 -> car aligned with  +Y
      heading =     pi -> car aligned with  -X
      heading = 3*pi/2 -> car aligned with  -Y

    sensor IDs example with 8 sensors:
     x x x x|x x x x
     0 1 2 3 4 5 6 7
    """
    HEADING_PLUS_X = 0
    HEADING_PLUS_Y = np.pi/2
    HEADING_MINUS_X = np.pi
    HEADING_MINUS_Y = 3*np.pi/2

    id_iter = itertools.count()

    def __init__(self, color, n_sensors, sensors_pitch=10, sensors_dist=100,
                 init_point=None, pos=None, heading=HEADING_PLUS_X):

        #moving parameters
        self.max_speed = 2
        self.acc = 1
        self.turn_rate = np.deg2rad(5)
        
        #print (init_point)

        #initial conditions
        if init_point is None:
            init_point = point.Point(0,0)

        self.speed = 0
        self.alive = True
        self.heading = heading
        self.pos = init_point.copy()
        self.last_position = self.pos.copy()
        self.distance_to_finish = 0
        self.last_distance_to_finish = 0
        self.last_valid_distance = -1
        self.steps_without_moving = 0
        self.steps_without_improving = 0
        self.steps_off_track = 0
        self.best_distance = None
        self.improved_this_step = False

        #robot config parameters
        self.n_sensors = n_sensors
        self.sensors_dist = sensors_dist
        self.sensors_pitch = sensors_pitch
        
        self.max_off_track = 3
        self.max_without_moving = 20
        self.max_without_improving = 10

        self.calculate_sensor_positions()
        self.control_func = self.debug_control_func
        self.color = color

        self.id = next(self.id_iter)
        self.update_count = 0

        #prepare sprite
        super().__init__()

        self.point_radius = 2
        self.margin = self.point_radius

        height = sensors_pitch * (n_sensors - 1) + self.margin * 2
        width = (sensors_dist + self.margin) * 2

        #set robot senter at surface center
        center = point.Point(width/2, height/2)

        sensors_pos = list()
        for i in range(n_sensors):
            p = point.Point(center.x + sensors_dist,
                            center.y + (i - (n_sensors-1)/2)*sensors_pitch)
            sensors_pos.append(p)
            #print(p)

        if(isinstance(pos, point.Point)):
            self.pos = pos
        else:
            self.pos = point.Point(center.x, center.y)

        self.image = pygame.Surface([width, height])
        self.image.fill(BG)
        self.image.set_colorkey(BG)  # Sets the colorkey for tansparency

        pygame.draw.circle(self.image, GREEN, (center.x, center.y), self.point_radius)
        for s in sensors_pos:
            pygame.draw.circle(self.image, BLUE, (s.x, s.y), self.point_radius)

        self.original_image = self.image.copy()
        self.rect = self.image.get_rect()
        self.rect.centerx, self.rect.centery = self.pos.get_xy()
        self.set_angle_rad(heading)
        #print(self.rect)
    
    def get_inputs_amount (self):
        return len(self.get_inputs())
        
    def set_angle_deg(self, angle_deg):
        self.set_angle_rad(np.deg2rad(np.remainder(angle_deg, 360)))

    def set_angle_rad(self, angle_rad):
        new_angle = np.remainder(angle_rad, 2*np.pi)
        self.heading = new_angle

        angle_deg = np.rad2deg(self.heading)

        self.image = pygame.transform.rotate(self.original_image, angle_deg)
        self.rect = self.image.get_rect()
        self.rect.centerx = self.pos.x
        self.rect.centery = self.pos.y

    def set_pos(self, new_pos):
        self.last_position = self.pos.copy()
        self.pos = point.Point(new_pos.x, new_pos.y)
        self.rect.centerx = self.pos.x
        self.rect.centery = self.pos.y

    def set_path_read_func(self, path_read):
        self.path_read_func = path_read

    def debug_control_func(self, inputs):
        for i in range(len(inputs)):
            print("[{}]: {}".format(i, inputs[i]))
        return [1, 0, 1, 0]

    def set_control_func(self, control_func):
        self.control_func = control_func

    def set_control_unit(self, control_unit):
        self.control_unit = control_unit

    def set_path_distance_func(self, path_distance_read):
        self.path_distance_func = path_distance_read

    def get_distance_to_finish(self):
        return self.distance_to_finish

    def get_last_distance_to_finish(self):
        if self.alive:
            return self.distance_to_finish
        return self.last_distance_to_finish
    
    def get_last_valid_distance(self):
        return self.last_valid_distance

    def get_sensor_position(self, sensor_id):
        # front sensors are numbered from left to right, with `sensors_pitch` distance between them
        # they are positioned in a line perpendicular to track direction and `sensors_dist` apart from robot's position

        #calculate sensor position without considering heading
        sensor_x = self.sensors_dist
        sensor_y = ((self.n_sensors - 1)/2 - sensor_id) * self.sensors_pitch

        #transform into polar coordinates
        z = (sensor_x + sensor_y * 1j)
        r, theta = coord.z2polar(z)

        #sum heading to theta to calculate sensor position in reference to robot position
        new_theta = theta + self.heading
        new_z = coord.polar2z(r, new_theta)
        #calculate final position in reference to track's origin
        final_sensor_x = round(np.real(new_z) + self.pos.x)
        final_sensor_y = round(np.imag(new_z) + self.pos.y)

        return point.Point(int(final_sensor_x), int(final_sensor_y))

    def calculate_sensor_positions(self):
        self.sensor_positions = list()
        for i in range(self.n_sensors):
            self.sensor_positions.append(self.get_sensor_position(i))

        return list(self.sensor_positions)
        
        
    def check_alive(self):
        if self.path_read_func(self.pos) is None:
            #print ("out of bounds at: ", self.position)
            self.alive = False

        if self.path_read_func(self.pos) == -1:
            #print ("died at: ", self.position)
            self.steps_off_track += 1
            if (self.steps_off_track >= self.max_off_track):
                self.alive = False
        else:
            self.steps_off_track = 0
        
        if self.improved_this_step is False:
            self.steps_without_improving += 1
            if self.steps_without_improving > self.max_without_improving:
                #print ("{} is not improving for {} steps".format(self.id, self.steps_without_improving))
                self.alive = False
        else:
            self.steps_without_improving = 0
        
        if self.steps_without_moving >= self.max_without_moving:
            #print ("stalled at: ", self.position)
            self.alive = False
        
        return self.alive

    def check_moved(self):
        if self.alive and self.last_position != self.pos:
            self.moved = True
        else:
            self.moved = False
            self.steps_without_moving += 1
        self.last_position = self.pos.copy()
        return self.moved

    def calc_new_position(self):
        x, y = coord.polar2xy(self.speed, self.heading)
        delta = point.Point(x, -y)
        self.set_pos(self.pos + delta)

    def calc_new_distances(self):
        if(self.alive):
            self.last_distance_to_finish = self.distance_to_finish
            self.distance_to_finish = self.path_distance_func(self.pos)
        if (self.distance_to_finish >= 0):
            self.last_valid_distance = self.distance_to_finish
        #store best distance value achieved so far
        if (self.best_distance is None):
            self.best_distance = self.last_valid_distance
        else:
            if (self.last_valid_distance < self.best_distance):
                self.best_distance = self.last_valid_distance
                self.improved_this_step = True
            else:
                self.improved_this_step = False

    def reset(self, start_point, start_heading_rad):
        self.alive = True
        self.set_pos(start_point)
        self.set_angle_rad(start_heading_rad)
        self.speed = 0
        self.moved = False
        self.steps_without_moving = 0
        self.steps_without_improving = 0
        self.steps_off_track = 0
        self.best_distance = None
        self.improved_this_step = False

    def get_inputs(self):
        inputs = list()
        inputs.append(self.speed)
        # inputs.append(self.heading)
        for s in self.calculate_sensor_positions():
            inputs.append(self.path_read_func(s))
        return inputs

    def update(self):
        if self.alive is False:
            return False
        self.update_count += 1

        acc, brake, left, right = self.control_func(self.get_inputs())
        
#        print ("old pos: {} old heading: {}".format(self.pos, np.rad2deg(self.heading)))
        if acc:
            speed_change = self.acc * (np.arctan(acc) / (np.pi * 2))
            self.speed = min(self.speed + speed_change, self.max_speed)
        if brake:
            speed_change = self.acc * (np.arctan(brake) / (np.pi * 2))
#            self.speed = min(self.speed + speed_change, self.max_speed)
            self.speed = max(self.speed - speed_change, (-1)*self.max_speed)
        if left:
            turn_angle = self.turn_rate * (np.arctan(left) / (np.pi * 2))
            self.set_angle_rad(self.heading + turn_angle)
        if right:
            turn_angle = self.turn_rate * (np.arctan(right) / (np.pi * 2))
            self.set_angle_rad(self.heading - turn_angle)

        #limit heading to pi
        self.calc_new_position()
#        print ("new pos: {} new heading: {}".format(self.pos, np.rad2deg(self.heading)))
        self.check_alive()
        self.check_moved()
        if(self.alive is False):
            #print ("Returning to last alive position:", self.last_position)
            self.set_pos(self.last_position)
        self.calc_new_distances()
#        print("x: {: 3}\ty: {: 3}\tacc: {: 2.2}\tbrake: {: 2.2}\tleft: {: 2.2}\tright: {: 2.2}\tspeed: {: 2.2f}\theading: {:2.2f}"\
#            .format(self.pos.x,self.pos.y,float(acc), float(brake), float(left), float(right), float(self.speed),np.rad2deg(self.heading)))
        return True


class Track (pygame.sprite.Sprite):
    OFF_TRACK = (-1)
    ON_TRACK = (1)

    START_VALUE = (-2)
    EMPTY_DISTANCE = (-10)
    END_VALUE = (0)

    START_COLOR     = (0, 255, 0)
    END_COLOR       = (255, 0, 0)
    OFF_TRACK_COLOR = (0, 0, 0)
    ON_TRACK_COLOR  = (255, 255, 255)


    def __init__(self, image):
        super().__init__()
        self.end_points = list()
        self.shortest_distance = None
        self.distances_plot = None
        self.start_point = None
        self.from_image(image)
        #self.win = pygame.display.set_mode((self.size_x, self.size_y))


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
                        this_p = point.Point(x,y)
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
        if point.x >= self.size_x or point.y >= self.size_y or \
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
                p = point.Point(x,y)
#                pix = self.image.getpixel((x,self.size_y - 1 - y))
                pix = self.image.getpixel((x,y))
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
                
        self.create_track_background()
        self.calc_distances()
        self.create_distances_background()
        
        self.image = self.track_image
        self.rect = self.track_image.get_rect()
        
    def create_track_background(self):
        self.track_image = pygame.Surface((self.size_x, self.size_y))
        for x in range(self.size_x):
            for y in range(self.size_y):
                p = point.Point(x,y)
                val = self.get_path(p)
                if val == self.ON_TRACK:
                    self.track_image.set_at((p.x, p.y), self.ON_TRACK_COLOR)
                elif val == self.END_VALUE:
                    self.track_image.set_at((p.x, p.y), self.END_COLOR)
                else:
                    self.track_image.set_at((p.x, p.y), self.OFF_TRACK_COLOR)            
    
    
    def create_distances_background(self):
        print("\nPreparing to distances backgroud")
        print ("max distance:", self.max_distance)
        print ("min distance:", self.shortest_distance)
        self.distances_image = pygame.Surface((self.size_x, self.size_y))
        color_gain = (255 - 40) / self.max_distance
        self.distances_image.fill((0,0,0))
        for x in range(self.size_x):
            for y in range(self.size_y):
                p = point.Point(x,y)
                dist = self.get_distance(p)
                if (dist > 0):
                    R = (int(dist * color_gain) + 40)
                    G = 40
                    B = 40
                    color = (R,G,B)
                    if (dist % 20 == 0):
                        color = (255,255,255)
                    self.distances_image.set_at((p.x, p.y), color)
        
def update():
#    robots_list.draw(screen)
    pygame.display.flip()

def update_thread (sprite_group, surface):
    sprite_group.update()
    sprite_group.draw(surface)
    
def get_key_movement(inputs):
    got_event = False
    while(got_event is False):
        pygame.time.delay(10)
        for event in pygame.event.get():
            acc = 0
            brake = 0
            left = 0
            right = 0
            if got_event is False and event.type == pygame.KEYUP:
                if event.key == pygame.K_UP:
                    acc = 1
                    got_event = True
                if event.key == pygame.K_DOWN:
                    brake = 1
                    got_event = True
                if event.key == pygame.K_LEFT:
                    left = 1
                    got_event = True
                if event.key == pygame.K_RIGHT:
                    right = 1
                    got_event = True
                if event.key == pygame.K_SPACE:
                    got_event = True      
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
    return [acc, brake, left, right]

pygame.init()


key_control = False


#filename = 'tracks/track_100x100_simple.png'
#filename = 'tracks/track_100x100_white.png'
#filename = 'tracks/track_1000x1000_zig_zag.png'
#filename = 'tracks/track_1000x1000_s_curve2.png'
#filename = 'tracks/track_1000x1000_s_curve.png''
#filename = 'tracks/track_1000x1000_s_curve3.png'
#filename = 'tracks/track_1000x1000_s_curve4.png'
#filename = 'tracks/track_1000x1000_s_curve5.png'
#filename = 'tracks/track_1000x1000_fast_training.png'
#filename = 'tracks/track_1000x1000_u_curve.png'
#filename = 'tracks/track_1000x1000_ss.png'
#filename = 'tracks/track_100x100_simple.png'
#filename = 'tracks/track_100x100_line.png'
#filename = 'tracks/track_100x100_C.png'
#filename = 'tracks/track_10x10.png'
#filename = 'tracks/test2.png'
#filename = 'tracks/test3.png'
#filename = 'tracks/test4.png'
#filename = 'tracks/test5.png'
filename = 'tracks/test6.png'


im = Image.open(filename)
t = Track(im.resize((1000,1000)))
#t = Track(im)
pygame.quit()
exit()

screen_width = t.size_x
screen_height = t.size_y
screen = pygame.display.set_mode([screen_width, screen_height])
pygame.display.set_caption("IA follow")

background_list = pygame.sprite.Group()
background_list.add(t)

robots_list = pygame.sprite.Group()

start_pos = t.start_point
#start_heading = (Robot.HEADING_MINUS_X + Robot.HEADING_MINUS_Y)/2
start_heading = Robot.HEADING_MINUS_X

indiv = 200
max_gen = 20000

threads_count = 8
robot_groups = list()
for i in range(threads_count):
    robot_groups.append(pygame.sprite.Group())


if (key_control):
    indiv = 1

neurals = list()
for n in range(indiv):
#    neurals.append(network (9, (20, 4)))
    neurals.append(network (9, (9,6, 4,)))

for i in range(indiv):
    r = Robot(WHITE, 8, 10, 100, heading=start_heading, pos=start_pos)
    r.set_path_read_func(t.get_path)
    r.set_path_distance_func(t.get_distance)
    r.set_control_func(neurals[i].evaluate)
    
    if (key_control):
        r.set_control_func(get_key_movement)
    
    r.set_control_unit(neurals[i])
    robots_list.add(r)
    
    robot_groups[i%threads_count].add(r)

generation = 0
generation_scores = list()
bar = Bar('Processing', max=t.max_distance)
bar.check_tty = False
for g in range (max_gen):
    bar.goto(0)
    print ("Starting generation {}".format(generation))
    for r in robots_list.sprites():
        r.reset(start_pos, start_heading)
    
    step = 0
    alive = True
    stalled_count = 0
    robots = robots_list.sprites()
    while(alive):
        
#        screen.blit(t.track_image, (0,0))
        screen.blit(t.distances_image, (0,0))
        
        step += 1
        alive = 0
        moved = False
        
        threads = list()
        for i, g in enumerate(robot_groups):
            x = threading.Thread(target=update_thread, args=(g, screen))
            x.start()
            threads.append(x)
        
        for i, x in enumerate(threads):
            x.join()
        
        for event in pygame.event.get():
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_k:
                    print ("Kill everyone")
                    for r in robots:
                        r.alive = False
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
        for r in robots:
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
                print ("Stalled for {} steps. Interrupting generation here".format(stalled_count))
                break
        
        if (generation % 1 == 0):
            update()
        closest_distance = min([r.get_last_valid_distance() for r in robots if r.get_last_valid_distance() >= 0])
        bar.goto(bar.max - closest_distance)
        
    distances = list()
    robots_sorted = sorted(robots, key=lambda r: r.get_last_valid_distance())
    for r in robots_sorted:
        distances.append(r.get_last_valid_distance())

    print("")
    for d in distances[:5]:
        print (d)

    print ("#"*40)
    print ("\nEnded generation {} after {} steps".format(generation, step))
    print ("Best robot got to distance {}".format(closest_distance))
    generation_scores.append(closest_distance)
    print ("#"*40)
    generation += 1
    

    #get robots gains and fitness value to run genetic algorithm
    results = list()
    for r in robots:
        gains = r.control_unit.get_gains()
        fitness = t.max_distance - r.get_last_valid_distance()
        
        robot_result = {"gains":gains, "fitness":fitness, "id":r.id}
        results.append(robot_result)

    g = Genetic(results)
    new_gains = g.evolve(keep_percent=0.60)
    
        
    for i, n in enumerate(neurals):
        n.set_gains(new_gains[i]["gains"])
