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
        self.max_speed = 4
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
        self.steps_sensors_off_track = 0
        self.best_distance = None
        self.improved_this_step = False
        self.last_sensor_reads = list()
        self.steps_run = 0

        #robot config parameters
        self.n_sensors = n_sensors
        self.sensors_dist = sensors_dist
        self.sensors_pitch = sensors_pitch
        
        self.max_off_track = 6
        self.max_without_moving = 80
        self.max_without_improving = 80
        self.max_sensors_off_track = 10

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
        center = center.copy_int()

        sensors_pos = list()
        for i in range(n_sensors):
            p = point.Point(center.x + sensors_dist,
                            center.y + (i - (n_sensors-1)/2)*sensors_pitch)
            sensors_pos.append(p)

        if(isinstance(pos, point.Point)):
            self.pos = pos
        else:
            self.pos = point.Point(center.x, center.y)

        self.image = pygame.Surface([width, height])
        self.image.fill(BG)
        self.image.set_colorkey(BG)  # Sets the colorkey for tansparency

        pygame.draw.circle(self.image, GREEN, (center.x, center.y), self.point_radius)
        for s in sensors_pos:
            pygame.draw.circle(self.image, BLUE, (s.int_x(), s.int_y()), self.point_radius)

        self.original_image = self.image.copy()
        self.rect = self.image.get_rect()
        self.rect.centerx, self.rect.centery = self.pos.get_int_xy()
        self.set_angle_rad(heading)
    
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
        self.rect.centerx = self.pos.int_x()
        self.rect.centery = self.pos.int_y()

    def set_pos(self, new_pos):
        self.last_position = self.pos.copy()
        self.pos = point.Point(new_pos.x, new_pos.y)
        self.rect.centerx = self.pos.int_x()
        self.rect.centery = self.pos.int_y()

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
    
    def set_max_distance(self, max_distance):
        self.max_distance = max_distance

    def get_fitness_distances(self):
        last__valid_dist = self.get_last_valid_distance()
        max_dist = self.max_distance
        val = (max_dist - last__valid_dist)/max_dist
        
        return val
    
    def get_fitness_sensors(self):
        val = (self.steps_run - self.steps_sensors_off_track) / self.steps_run
        return val
    
    def get_fitness(self):
        w_dist = 0.9
        w_sensors = 0.1
        w_sum = w_dist + w_sensors
        return (w_dist * self.get_fitness_distances() + w_sensors*self.get_fitness_sensors())/w_sum
        

    def get_sensor_position(self, sensor_id):
        # front sensors are numbered from left to right, with `sensors_pitch` distance between them
        # they are positioned in a line perpendicular to track direction and `sensors_dist` apart from robot's position

        #calculate sensor position without considering heading
        sensor_x = self.sensors_dist
        sensor_y = ((self.n_sensors - 1)/2 - sensor_id) * self.sensors_pitch

        #transform into polar coordinates 
        r, theta = coord.xy2polar(sensor_x, sensor_y)

        #sum heading to theta to calculate sensor position in reference to robot position
        new_theta = theta + self.heading
        new_x, new_y = coord.polar2xy(r, new_theta)
        #calculate final position in reference to track's origin
        final_sensor_x = self.pos.x + new_x
        final_sensor_y = self.pos.y - new_y #inverted sign due to inverted Y axis direction

        return point.Point(final_sensor_x, final_sensor_y)

    def calculate_sensor_positions(self):
        self.sensor_positions = list()
        for i in range(self.n_sensors):
            self.sensor_positions.append(self.get_sensor_position(i))

        return list(self.sensor_positions)
        
        
    def check_alive(self):
        if self.path_read_func(self.pos) is None:
            self.alive = False

        if self.path_read_func(self.pos) == -1:
            self.steps_off_track += 1
            if (self.steps_off_track >= self.max_off_track):
                self.alive = False
        else:
            self.steps_off_track = 0
        
        if self.improved_this_step is False:
            self.steps_without_improving += 1
            if self.steps_without_improving > self.max_without_improving:
                self.alive = False
        else:
            self.steps_without_improving = 0
        
        if self.steps_without_moving >= self.max_without_moving:
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
    
    def check_sensors_off_track(self):
        if len(self.last_sensor_reads) > 0:
            if len([i for i in self.last_sensor_reads if i >= 0]) == 0:
                self.steps_sensors_off_track += 1

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
        self.last_sensor_reads = list()
        self.steps_sensors_off_track = 0
        self.steps_run = 0

    def get_inputs(self):
        inputs = list()
        inputs.append(self.speed)
        self.last_sensor_reads = list()
        for s in self.calculate_sensor_positions():
            read = self.path_read_func(s)
            inputs.append(read)
            self.last_sensor_reads.append(read)
        return inputs

    def update(self):
        if self.alive is False:
            return False
        self.update_count += 1
        self.steps_run += 1

        acc, brake, left, right = self.control_func(self.get_inputs())
        self.check_sensors_off_track()
        
        if acc:
#            speed_acc = self.acc * (np.arctan(acc) / (np.pi * 2))
            speed_change = self.acc * (np.arctan(acc) / (np.pi * 2))
            self.speed = min(self.speed + speed_change, self.max_speed)
        if brake:
#            speed_brake = self.acc * (np.arctan(brake) / (np.pi * 2))
            speed_change = self.acc * (np.arctan(brake) / (np.pi * 2))
            self.speed = max(self.speed - speed_change, (-1)*self.max_speed)
        if left:
#            angle_left = self.turn_rate * (np.arctan(left) / (np.pi * 2))
            turn_angle = self.turn_rate * (np.arctan(left) / (np.pi * 2))
            self.set_angle_rad(self.heading + turn_angle)
        if right:
#            angle_right = self.turn_rate * (np.arctan(right) / (np.pi * 2))
            turn_angle = self.turn_rate * (np.arctan(right) / (np.pi * 2))
            self.set_angle_rad(self.heading - turn_angle)

        #limit heading to pi
        self.calc_new_position()
        self.check_alive()
        self.check_moved()
        if(self.alive is False):
            self.set_pos(self.last_position)
        self.calc_new_distances()
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
        return self.distances[point.int_y()][point.int_x()]

    def set_distance (self, point, value):
        self.distances[point.int_y()][point.int_x()] = value

    def get_path (self, point):
        if point.x >= self.size_x or point.y >= self.size_y or \
            point.x < 0 or point.y < 0:
            return self.OFF_TRACK
        return self.path[point.int_y()][point.int_x()]

    def set_path (self, point, value):
        self.path[point.int_y()][point.int_x()] = value

    def from_image (self, track_image):
        self.size_x = track_image.size[0]
        self.size_y = track_image.size[1]
        self.image = track_image.copy()
        self.path = np.ones((self.size_y, self.size_x)) * self.OFF_TRACK

        for x in range(self.size_x):
            for y in range(self.size_y):
                p = point.Point(x,y)
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
        self.distances_image.set_at((10, 50), (0, 255, 0))
        self.distances_image.set_at((11, 50), (0, 255, 0))
        self.distances_image.set_at((10, 51), (0, 255, 0))
        self.distances_image.set_at((11, 51), (0, 255, 0))
        
def update():
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

def simple_control(inputs):
    speed = inputs[0]
    print (inputs)
    brake = 0
    acc = 0
    left = 0
    right = 0
    
    if speed < 0.2:
        acc = 0.5
    if inputs[1] < 0:
        right = 1
    if inputs[4] < 0:
        left = 1
    print ([acc, brake, left, right])
    return acc, brake, left, right


if __name__ == "__main__":
    pygame.init()


    key_control = False


    # filename = 'tracks/track_100x100_simple.png'
    #filename = 'tracks/track_100x100_white.png'
    #filename = 'tracks/track_1000x1000_zig_zag.png'
    #filename = 'tracks/track_1000x1000_s_curve2.png'
    #filename = 'tracks/track_1000x1000_s_curve.png''
    #filename = 'tracks/track_1000x1000_s_curve3.png'
    #filename = 'tracks/track_1000x1000_s_curve4.png'
    # filename = 'tracks/track_1000x1000_s_curve5.png'
    filename = 'tracks/track_1000x1000_fast_training.png'
    #filename = 'tracks/track_1000x1000_u_curve.png'
    # filename = 'tracks/track_1000x1000_ss.png'
    # filename = 'tracks/track_100x100_simple.png'
    #filename = 'tracks/track_100x100_line.png'
    #filename = 'tracks/track_100x100_C.png'
    # filename = 'tracks/track_10x10.png'
    #filename = 'tracks/test2.png'
    #filename = 'tracks/test3.png'
    #filename = 'tracks/test4.png'
    #filename = 'tracks/test5.png'
    #filename = 'tracks/test6.png'


    im = Image.open(filename)
    t = Track(im.resize((1000,1000)))


    screen_width = t.size_x
    screen_height = t.size_y
    screen = pygame.display.set_mode([screen_width, screen_height])
    pygame.display.set_caption("IA follow")

    background_list = pygame.sprite.Group()
    background_list.add(t)

    robots_list = pygame.sprite.Group()

    start_pos = t.start_point
    start_heading = Robot.HEADING_MINUS_X

    indiv = 100
    max_gen = 20000

    threads_count = 8
    robot_groups = list()
    for i in range(threads_count):
        robot_groups.append(pygame.sprite.Group())


    if (key_control):
        indiv = 1

    neurals = list()

    for i in range(indiv):
        r = Robot(WHITE, 4, 10, 50, heading=start_heading, pos=start_pos)
        r.set_path_read_func(t.get_path)
        r.set_path_distance_func(t.get_distance)
        
        req_inputs = len(r.get_inputs())
        n = network (req_inputs, (4, 4, 4))
        neurals.append(n)
        r.set_control_func(n.evaluate)
        r.set_control_unit(neurals[i])
        
        # r.set_control_func(simple_control)
        r.set_max_distance(t.max_distance)
        
        if (key_control):
            r.set_control_func(get_key_movement)
        
        robots_list.add(r)
        
        robot_groups[i%threads_count].add(r)

    graphics_enabled = True
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
                    if event.key == pygame.K_v:
                        graphics_enabled = not graphics_enabled
                        if graphics_enabled:
                            print("\nEnabled graphics")
                        else:
                            print("\nDisabled graphics")
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
            robots_alive = list()
            for r in robots:
                if (r.alive):
                    alive += 1
                    robots_alive.append(r)
                moved |= r.moved 

            if moved:
                stalled_count = 0
            else:
                stalled_count += 1
                if (stalled_count > 10):
                    print ("Stalled for {} steps. Interrupting generation here".format(stalled_count))
                    break
            
            if (generation % 1 == 0):
                if (graphics_enabled):
                    update()
            closest_distance = min([r.get_last_valid_distance() for r in robots if r.get_last_valid_distance()])
            best_fitness = max([r.get_fitness() for r in robots])
            #bar.goto(bar.max - closest_distance)

        robots_sorted = sorted(robots, key=lambda r: r.get_fitness(), reverse=True)
        
        print("")
        for r in robots_sorted[:5]:
            print ("{:.2f}%\t{:.2f}%\t{:.2f}%\t{}".format(100*r.get_fitness(), 100*r.get_fitness_distances(), 100*r.get_fitness_sensors(), r.id))


        print ("#"*40)
        print ("\nEnded generation {} after {} steps".format(generation, step))
        print ("Best robot got to distance {} and fitness {:.2f}%".format(closest_distance, 100*best_fitness))
        generation_scores.append([closest_distance, best_fitness])
        print ("#"*40)
        generation += 1
        
        # input("press enter to continue")
        

        #get robots gains and fitness value to run genetic algorithm
        results = list()
        for r in robots:
            gains = r.control_unit.get_gains()
            fitness = r.get_fitness()
            
            robot_result = {"gains":gains, "fitness":fitness, "id":r.id}
            results.append(robot_result)

        g = Genetic(results)
        new_gains = g.evolve(keep_percent=0.20)
        
            
        for i, n in enumerate(neurals):
            n.set_gains(new_gains[i]["gains"])
