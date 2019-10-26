import pygame
import random

#https://itch.io/game-assets/free
#http://programarcadegames.com/index.php?chapter=introduction_to_sprites&lang=en


# COLORS
BLACK = (0,0,0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

#class Treasure(pygame.sprite.Sprite):
#    def __init__ (self):
#        super().__init__()
#        self.image = pygame.image.load("sprites/chest_empty_open_anim_f0.png").convert()
#        self.rect = self.image.get_rect()
        
    
class Robot(pygame.sprite.Sprite):
    def __init__ (self, color, width, height):
        super().__init__()
        
        self.image = pygame.Surface([width, height])
        self.image.fill(color)
        self.rect = self.image.get_rect()


pygame.init()
screen_width = 500
screen_height = 500
screen = pygame.display.set_mode([screen_width, screen_height])
pygame.display.set_caption("IA follow")

treasure_list = pygame.sprite.Group()
all_sprites_list = pygame.sprite.Group()

#t = Treasure()
r = Robot(BLUE, 10, 10)

#t.rect.x = random.randrange(screen_width)
#t.rect.y = random.randrange(screen_height)

r.rect.x = random.randrange(screen_width)
r.rect.y = random.randrange(screen_height)

#treasure_list.add(t)
#all_sprites_list.add(t)
all_sprites_list.add(r)

all_sprites_list.draw(screen)



def old_code ():
    x = 50
    y = 50
    width = 40
    height = 60
    vel = 5
    
    run = True
    while run:
        pygame.time.delay(100)
        for event in pygame.event.get():
            if event.type ==pygame.QUIT:
                run = False
        keys = pygame.key.get_pressed()
    
        if keys[pygame.K_UP]:
            y -= vel
            print("up")
        if keys[pygame.K_DOWN]:
            y += vel
            print("DOWN")
        if keys[pygame.K_LEFT]:
            x -= vel
            print("LEFT")
        if keys[pygame.K_RIGHT]:
            x += vel
            print("RIGHT")
    
        win.fill((0,0,0))
        pygame.draw.rect(win,(255,0,0),(x,y,width,height))
        pygame.display.update()
    
    pygame.quit()