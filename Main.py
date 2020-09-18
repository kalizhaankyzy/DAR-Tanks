import pika
import uuid
import json
from threading import Thread
import threading as th
from math import *
import pygame, random, math
import operator
IP = '34.254.177.17'
PORT = '5672'
VHOST = 'dar-tanks'
USER = 'dar-tanks'
PASSWORD = '5orPLExUYnyVYZg48caMpX'
pygame.init()
Width = 1050
Height = 600
screen = pygame.display.set_mode((Width,Height))
clock = pygame.time.Clock()
RAD = pi / 180
pygame.display.set_caption("DAR TANKS")
clock = pygame.time.Clock()
bullets = []
bullet_sound = pygame.mixer.Sound("sounds/bullet.ogg")
bomb_sound = pygame.mixer.Sound("sounds/bomb.ogg")
music = pygame.mixer.Sound("sounds/Offensive-AShamaluevMusic.ogg")
class Client():
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=IP,
                port = PORT,
                virtual_host = VHOST,
                credentials = pika.PlainCredentials(
                    username = USER,
                    password = PASSWORD
                )
            )
        )
        self.channel = self.connection.channel()
        queue = self.channel.queue_declare(queue='',auto_delete = True,exclusive = True)
        self.callback_queue = queue.method.queue
        self.channel.queue_bind(
            exchange='X:routing.topic',
            queue=self.callback_queue
        )

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )
        self.response = None
        self.corr_id = None
        self.token = None
        self.tank_id = None
        self.room_id = None
    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)
            print(self.response)
    def call(self, key, message={}):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='X:routing.topic',
            routing_key=key,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json.dumps(message)
        )
        while self.response is None:
            self.connection.process_data_events()
    def check_server_status(self):
        self.call('tank.request.healthcheck')
    def obtain_token(self, room_id):
        message = {
            'roomId' : room_id
        }
        self.call('tank.request.register', message)
        if 'token' in self.response:
            self.token = self.response['token']
            self.tank_id = self.response['tankId']
            self.room_id = self.response['roomId']
            return True
        return False
    def turn_tank(self, token, direction):
        message = {
            'token' : token,
            'direction': direction
        }
        self.call('tank.request.turn', message)
    def fire_bullet(self,token):
        message = {
            'token' : token
        }
        self.call('tank.request.fire', message)

class TankConsumerClient(Thread):
    def __init__(self,room_id):
        super().__init__()
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=IP,
                port = PORT,
                virtual_host = VHOST,
                credentials = pika.PlainCredentials(
                    username = USER,
                    password = PASSWORD
                )
            )
        )
        self.channel = self.connection.channel()
        queue = self.channel.queue_declare(queue='',auto_delete = True,exclusive = True)
        event_listener = queue.method.queue
        self.channel.queue_bind(
            exchange='X:routing.topic',
            queue=event_listener,
            routing_key='event.state.'+room_id)
        self.channel.basic_consume(
            queue = event_listener,
            on_message_callback=self.on_response,
            auto_ack=True)
        self.response = None
    def on_response(self, ch, method, props, body):
        self.response = json.loads(body)
        print(self.response)
    def run(self):
        self.channel.start_consuming()
class Bullet():
    def __init__(self,x,y,angle):
        self.x = x
        self.y = y
        self.side = 4
        self.angle = angle
        self.color = (255,0,0)
        self.speed = 40
        self.time = 0
    def update(self,seconds):
        self.x +=self.speed*seconds*cos(self.angle*RAD)
        self.y +=self.speed*seconds*sin(self.angle*RAD)
        self.draw()
        self.rules()
    def draw(self):
        pygame.draw.circle(screen,self.color,(round(self.x),round(self.y)),self.side)
    def rules(self):
        if self.y + self.side <= 0:
            self.y = Height
        elif self.y >= Height:
            self.y = 0 - self.side
        elif self.x >= Width:
            self.x = 0 - self.side
        elif self.x + self.side <= 0:
            self.x = Width
class player():
    def __init__(self,x,y,number):
        self.x = x
        self.y = y
        self.number = number
        self.col = (173,6,35)
        self.col_d = (200,0,0)
        self.vel = 20
        self.width = 40
        self.height = 30
        self.angle = 0
        self.stop = False
        self.center = (self.x+self.width/2,self.y+self.height/2)
        self.life = 3
        self.direction = ""
        self.bullet_time = 0
        
    def update(self,seconds):
        pressedkeys = pygame.key.get_pressed()
        if pressedkeys[pygame.K_z]:
            self.stop = 1
        elif pressedkeys[pygame.K_x]:
            self.stop = 0
        if self.number == 1:
            if pressedkeys[pygame.K_UP]:
                if self.stop:
                    self.y -= self.vel*seconds
                self.direction = 'u'
            elif pressedkeys[pygame.K_DOWN]:
                if self.stop:
                    self.y += self.vel*seconds
                self.direction = 'd'
            elif pressedkeys[pygame.K_LEFT]:
                if self.stop:
                    self.x -= self.vel*seconds
                self.direction = 'l'
            elif pressedkeys[pygame.K_RIGHT]:
                if self.stop:
                    self.x += self.vel*seconds
                self.direction = 'r'
            if pressedkeys[pygame.K_SPACE] and (pygame.time.get_ticks() - self.bullet_time)/1000 >=0.2:
                self.bullet_time = pygame.time.get_ticks()
                bullet = Bullet(self.center[0]+0.7*self.width*cos(self.angle*RAD),self.center[1]+self.height*sin(self.angle*RAD),self.angle)
                bullets.append(bullet)
                bullet_sound.play()
        self.center = (self.x+self.width/2,self.y+self.height/2)
        self.draw()
        self.rules(seconds)
        
    def draw(self):
        pygame.draw.rect(screen, self.col, (self.x,self.y,self.width,self.height))
        pygame.draw.line(screen, self.col_d, self.center,(self.center[0]+0.7*self.width*cos(self.angle*RAD),self.center[1]+self.height*sin(self.angle*RAD)),5)
        pygame.draw.circle(screen, self.col_d, (round(self.center[0]),round(self.center[1])), 11)
    def rules(self,seconds):
        if self.y + self.height <= 50:
            self.y = Height
        elif self.y >= Height:
            self.y = 50 - self.height
        elif self.x >= Width:
            self.x = 0 - self.width
        elif self.x + self.width <= 0:
            self.x = Width

        if not self.stop:
            if self.direction == 'u':
                self.y -= self.vel*seconds
            elif self.direction == 'd':
                self.y += self.vel*seconds
            elif self.direction == 'l':
                self.x -= self.vel*seconds
            elif self.direction == 'r':
                self.x += self.vel*seconds
class Walls():
    def __init__(self,x,y,w,los):
        self.x = x
        self.y = y
        self.width = w
        self.height = los
    def draw(self):
        img = pygame.transform.scale(pygame.image.load("img/wall.png"),(self.width,self.height))
        screen.blit(img,(self.x,self.y))
class super_power():
    rainbow = [[255,0,0],[255,165,0],[255,255,0],[0,255,0],[0,191,255],[0,0,255],[128,0,128]]
    def __init__(self):
        self.x = random.randint(0,Width)
        self.y = random.randint(5,Height)
        self.color = random.choice(super_power.rainbow)
        self.side = 10
        self.time = 0
        self.effect = False
    def draw(self):
        pygame.draw.rect(screen, self.color,(self.x,self.y,self.side,self.side))
def draw_lives(surf, x, y, lives, img):
    for i in range(lives):
        img_rect = img.get_rect()
        img_rect.x = x + 30 * i 
        img_rect.y = y
        surf.blit(img, img_rect)

UP = 'UP'
DOWN = 'DOWN'
LEFT = 'LEFT'
RIGHT = 'RIGHT'
MoveKeys = {
    pygame.K_UP : UP,
    pygame.K_DOWN : DOWN,
    pygame.K_LEFT : LEFT,
    pygame.K_RIGHT : RIGHT
}

def button(msg,x,y,w,los,ic,ac,size,action=None):
    mouse = pygame.mouse.get_pos() 
    click = pygame.mouse.get_pressed()
    if x+w > mouse[0] > x and y+los > mouse[1] > y:
        pygame.draw.rect(screen, ac,(x,y,w,los))
        if click[0] == 1 and action != None:
            action()
    else:
        pygame.draw.rect(screen, ic,(x,y,w,los))
    font = pygame.font.SysFont('Pokemon GB.ttf', size) 
    text = font.render(msg,1,(255,255,255))
    screen.blit(text,(x+30,y+15))
def game_intro():
    intro = True
    while intro:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
        screen.fill((0,0,0))
        img = pygame.transform.scale(pygame.image.load("img/tank1.png"),(400,400))
        img_rect = img.get_rect()
        x = Width-img_rect.width
        y = Height - img_rect.height + 20
        screen.blit(img,(x,y))
        font = pygame.font.SysFont('Pokemon GB.ttf', 125) 
        text = font.render("DAR TANKS",1,(255,255,0))
        text_rect = text.get_rect()
        text_x = Width/2 - text_rect.width/2
        screen.blit(text, (text_x,70))
        
        button("Single Player",100,200,400,60,(30,30,30),(0,0,0),50,single_game)
        button("Multiplayer",100,300,400,60,(30,30,30),(0,0,0),50,multiplayer)
        button("Multiplayer AI",100,400,400,60,(30,30,30),(0,0,0),50,multi_ai)
        pygame.mixer.music.stop()
        music.stop()
        pygame.display.update()
        clock.tick(15)
def Text(msg,x,y,color,size):
    font = pygame.font.SysFont('Times New Roman', size)
    text = font.render(msg,True,color) 
    screen.blit(text,(x,y))
def draw_tank(x,y,width,height,direction,**kwargs):
    img = pygame.transform.scale(pygame.image.load("img/player.png"),(width,height))
    if direction == 'UP':
        rot = pygame.transform.rotate(img, 90)
        screen.blit(rot,(x,y))
    if direction == 'DOWN':
        rot = pygame.transform.rotate(img, 270)
        screen.blit(rot,(x,y))
    if direction == 'LEFT':
        rot = pygame.transform.rotate(img, 180)
        screen.blit(rot,(x,y))
    if direction == 'RIGHT':
        rot = pygame.transform.rotate(img, 0)
        screen.blit(rot,(x,y))
    
def drawBullet(x,y,width,height,direction,**kwargs):
    img = pygame.transform.scale(pygame.image.load("img/b.png"),(15,5))
    screen.blit(img,(x,y))
    if direction == 'UP':
        rot = pygame.transform.rotate(img, 90)
        screen.blit(rot,(x,y))
    if direction == 'DOWN':
        rot = pygame.transform.rotate(img, 270)
        screen.blit(rot,(x,y))
    if direction == 'LEFT':
        rot = pygame.transform.rotate(img, 180)
        screen.blit(rot,(x,y))
    if direction == 'RIGHT':
        rot = pygame.transform.rotate(img, 0)
        screen.blit(rot,(x,y))

def single_game():
    gameover = False
    effect = False
    font_win = pygame.font.SysFont('Pokemon GB.ttf', 90) 
    font_score = pygame.font.SysFont('Pokemon GB.ttf', 30) 
    tank = player(10,60,1)
    walls = []  
    for i in range(5):
        wall = Walls(100,20+i*40,40,40)
        wall2 = Walls(700,150+i*40,40,40)
        wall3 = Walls(800+i*40,500,40,40)
        walls.append(wall)
        walls.append(wall2)
        walls.append(wall3)
    for i in range(6):
        wall = Walls(500,300+i*40,40,40)
        walls.append(wall)
    for i in range(7):
        wall = Walls(100+i*40,400,40,40)
        walls.append(wall)
    powers = []
    POWER = pygame.USEREVENT + 1
    pygame.time.set_timer(POWER, random.randint(5000,10000)) #time interval (5000,10000)
    music.play()
    power_time = 0
    effect = False
    next_level=False
    while True:
        ms = clock.tick(15)
        seconds = ms/100.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == POWER:
                new_power = super_power()
                powers.append(new_power) 
        screen.fill((0,0,0))
        img = pygame.image.load("img/heart.png")
        draw_lives(screen, 5, 5, tank.life, img)
        button("Back",Width/2-50,5,100,40,(30,30,30),(0,0,0),30,game_intro)
        tank.update(seconds)

        for bullet in bullets:
            bullet.update(seconds)
        for wall in walls:
            wall.draw()
        for power in powers:
            power.draw()
        #collision
        for bullet in bullets:
            if tank.x <= bullet.x <= tank.x + tank.width and tank.y <= bullet.y <= tank.y + tank.height:
                tank.life -= 1
                bullets.remove(bullet)
            if tank.vel == 40:
                bullet.speed = 80
                bullet.color = (255,255,0)
            for wall in walls:  
                if wall.x <= bullet.x <= wall.x + wall.width and wall.y <= bullet.y <= wall.y + wall.height:
                    walls.remove(wall)
                    bullets.remove(bullet)
        for wall in walls:
            if wall.x <= tank.x <= wall.x+wall.width or tank.x <= wall.x <= tank.x + tank.width :
                if wall.y <= tank.y <= wall.y + wall.height or tank.y <= wall.y <= tank.y + tank.height:
                    if tank.direction == 'r':
                        tank.x = tank.x-tank.width
                    if tank.direction == 'l':
                        tank.x = tank.x+tank.width
                    if tank.direction == 'u':
                        tank.y = tank.y+tank.height
                    if tank.direction == 'd':
                        tank.y = tank.y-tank.height
                    tank.life -= 1
                    walls.remove(wall)
            for power in powers:
                if wall.x <= power.x <= wall.x + wall.width and wall.y <= power.y <= wall.y + wall.height:
                    powers.remove(power)
        for power in powers:
            if tank.x <= power.x <= tank.x + tank.width and tank.y <= power.y <= tank.y + tank.height:
                effect = True
                power_time = pygame.time.get_ticks()
                powers.remove(power)
            elif power.x <= tank.x <= power.x+power.side and power.y <= tank.y <= power.y+power.side:
                effect = True
                power_time = pygame.time.get_ticks()
                powers.remove(power)
        if pygame.time.get_ticks()-power_time >=5000:
            effect = False
        if effect: tank.vel = 40
        elif not effect: tank.vel = 20
        if tank.life == 0:
            # pygame.mixer.music.stop()
            # bomb_sound.play()
            gameover = True
        if len(walls)==0:next_level=True
        if gameover==True:
            screen.fill((0,0,0))
            text2 = font_score.render("Score: "+str(tank.life), 0, (255,255,255))
            text2_rect = text2.get_rect()
            text2_x = Width / 2 - text2_rect.width / 2
            screen.blit(text2,(text2_x,10))
            button("Restart the game",Width/2-100,400,200,50,(30,30,30),(0,0,0),30,single_game)
            button("Menu",Width/2-50,470,100,50,(30,30,30),(0,0,0),30,game_intro)
            text = font_win.render("GAME OVER", 0, (255,255,255))
            text_rect = text.get_rect()
            text_x = Width / 2 - text_rect.width / 2
            text_y = Height / 2 - text_rect.height / 2
            screen.blit(text, (text_x,text_y-100))
            pygame.mixer.music.stop()
        if next_level==True:
            screen.fill((0,0,0))
            text2 = font_score.render("Score: "+str(tank.life), 0, (255,255,255))
            text2_rect = text2.get_rect()
            text2_x = Width / 2 - text2_rect.width / 2
            screen.blit(text2,(text2_x,10))
            text = font_win.render("Level complete!", 0, (255,255,0))
            text_rect = text.get_rect()
            text_x = Width / 2 - text_rect.width / 2
            text_y = Height / 2 - text_rect.height / 2
            screen.blit(text, (text_x,text_y-100))
            button("Menu",Width/2-50,270,100,50,(30,30,30),(0,0,0),30,game_intro)
            pygame.mixer.music.stop()
        clock.tick(60)
        pygame.display.update()

def multiplayer():
    gameover = False
    room = 12
    client = Client()
    client.check_server_status()
    client.obtain_token('room-'+str(room))
    client.turn_tank(client.token,'UP')
    event_client = TankConsumerClient('room-'+str(room))
    event_client.daemon = True
    event_client.start()
    info = {}
    win={}
    los = {}
    k = {}
    music.play()
    while True:
        screen.fill((0,0,0))
        font = pygame.font.SysFont('Pokemon GB.ttf', 40) 
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.connection.close()
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key in MoveKeys:
                    client.turn_tank(client.token, MoveKeys[event.key])
                if event.key == pygame.K_SPACE:
                    client.fire_bullet(client.token)
                    bullet_sound.play()
        try:
            pygame.draw.line(screen, (255,143,60), (830,0), (830,Height), 2) 
            remaining_time = event_client.response['remainingTime']
            text = font.render('Time: {}'.format(remaining_time), True, (255,255,255))
            screen.blit(text,(850,30))
            kicked = event_client.response['kicked']
            winners = event_client.response['winners']
            losers = event_client.response['losers']
            # hits = event_client.response['hits']
            for loser in losers:
                los[loser['tankId']] = loser['score']
            for winner in winners:
                win[winner['tankId']] = winner['score']
            for kick in kicked:
                k[kick['tankId']] = kick['score']
            tanks = event_client.response['gameField']['tanks']
            bullets = event_client.response['gameField']['bullets']
            myTank = client.tank_id
            for tank in tanks:
                tank_x = tank['x']
                tank_y = tank['y']
                tank_id = tank['id']
                tank_h = tank['health']
                tank_s = tank['score']
                info[tank_id] = [tank_h,tank_s]
                draw_tank(**tank)
                Text(tank_id,tank_x,tank_y-20,(255,255,255),15)
            for x in los.items():
                for z,y in info.items():
                    if x[0]==z:
                        y[0] = 0
                if myTank == x[0]:
                    gameover = True
            if myTank in k or myTank in win or remaining_time == 0:
                gameover = True
            for bullet in bullets:
                drawBullet(**bullet)
                Text(bullet['owner'],bullet['x'],bullet['y']-10,(255,255,255),15)
            i=0
            Text('Players -- Health -- Score',840,70,(255,255,0),23)
            sorted_y = sorted(info.items(), key=operator.itemgetter(1),reverse=False)
            for x,y in sorted_y:  
                if myTank != x:
                    color = (255,255,255)
                else: color = (255,0,0)    #myTank red,others white
                Text(str(x)+'         '+str(y[0])+'         '+str(y[1]),845,100+20*i,color,20)
                i+=1
            button("Back",Width-160,Height-50,100,40,(30,30,30),(0,0,0),30,game_intro)
        except:
            pass
        if gameover == True:
            screen.fill((0,0,0))
            button("Restart the game",365,100,300,50,(30,30,30),(0,0,0),40,multiplayer)
            button("Back",865,Height-50,100,40,(30,30,30),(0,0,0),30,game_intro)
            Text('Winners',200,200,(255,255,0),40)
            Text('Losers',450,200,(255,0,0),40)
            Text('Kicked',700,200,(255,0,255),40)
            Text('player'+'            '+'score',190,250,(255,255,255),20)
            Text('player'+'            '+'score',440,250,(255,255,255),20)
            Text('player'+'            '+'score',690,250,(255,255,255),20)
            i=0
            for x,y in los.items():
                Text(str(x)+'         '+str(y),440,270+20*i,(255,0,0),23)
                i+=1
            n=0
            for x,y in win.items():
                Text(str(x)+'         '+str(y),190,270+20*n,(255,255,0),23)
                n+=1
            l=0
            for x,y in k.items():
                Text(str(x)+'         '+str(y),690,270+20*l,(255,0,255),23)
                l+=1                
            pygame.display.update()
        pygame.display.update()
    client.connection.close()

def multi_ai():
    gameover = False
    room = 'room-12'
    client = Client()
    client.check_server_status()
    client.obtain_token(room)
    client.turn_tank(client.token,'DOWN')
    event_client = TankConsumerClient(room)
    event_client.daemon = True
    event_client.start()
    info = {}
    win={}
    los = {}
    k = {}
    myinfo={}
    myTank = client.tank_id
    time_elapsed_since_last_action = 0
    clock = pygame.time.Clock()
    music.play()
    while True:
        screen.fill((0,0,0))
        font = pygame.font.SysFont('Pokemon GB.ttf', 40) 
        dt = clock.tick()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                client.connection.close()
                pygame.quit()
                quit()
        
        try:
            pygame.draw.line(screen, (255,143,60), (830,0), (830,Height), 2) 
            remaining_time = event_client.response['remainingTime']
            text = font.render('Time: {}'.format(remaining_time), True, (255,255,255))
            screen.blit(text,(850,30))
            kicked = event_client.response['kicked']
            winners = event_client.response['winners']
            losers = event_client.response['losers']
            # hits = event_client.response['hits']
            for loser in losers:
                los[loser['tankId']] = loser['score']
            for winner in winners:
                win[winner['tankId']] = winner['score']
            for kick in kicked:
                k[kick['tankId']] = kick['score']
            tanks = event_client.response['gameField']['tanks']
            bullets = event_client.response['gameField']['bullets']
            for tank in tanks:
                tank_x = tank['x']
                tank_y = tank['y']
                tank_id = tank['id']
                tank_h = tank['health']
                tank_s = tank['score']
                tank_direction = tank['direction']
                info[tank_id] = [tank_h,tank_s]
                draw_tank(**tank)
                Text(tank_id,tank_x,tank_y-20,(255,255,255),15)
                if myTank == tank_id:
                    myinfo[tank_id]= [tank_x,tank_y,tank_direction]
                for x,y in myinfo.items():
                    if y[0]<=tank_x<=y[0]+31 or tank_x<=y[0]<=tank_x+31:
                        if tank_direction == 'UP':
                            dir = 'RIGHT'
                        elif tank_direction=='DOWN':
                            dir = 'LEFT'
                    elif y[1]<=tank_y<=y[1]+31 or tank_y<=y[1]<=tank_y+31:
                        if tank_direction == 'RIGHT' or tank_direction=='LEFT':
                            dir = 'DOWN'
                    client.turn_tank(client.token,dir)
            for x in los.items():
                for z,y in info.items():
                    if x[0]==z:
                        y[0] = 0
            time_elapsed_since_last_action += dt
            if time_elapsed_since_last_action > 5000:
                client.fire_bullet(client.token)
                time_elapsed_since_last_action = 0
            for bullet in bullets:
                drawBullet(**bullet)
                Text(bullet['owner'],bullet['x'],bullet['y']-10,(255,255,255),15)
            for x in los.items():
                for z,y in info.items():
                    if x[0]==z:
                        y[0] = 0
                if myTank == x[0]:
                    y[0]=0
                    gameover = True
            if myTank in k or myTank in win or remaining_time == 0:
                gameover = True
            i=0
            Text('Players -- Health -- Score',840,70,(255,255,0),23)
            sorted_y = sorted(info.items(), key=operator.itemgetter(1),reverse=True)
            for x,y in sorted_y:   
                if myTank != x:
                    color = (255,255,255)
                else: color = (255,0,0)
                Text(str(x)+'         '+str(y[0])+'         '+str(y[1]),845,100+20*i,color,20)
                i+=1
            button("Back",Width-160,Height-50,100,40,(30,30,30),(0,0,0),30,game_intro)
        except:
            pass
        if gameover == True:
            screen.fill((0,0,0))
            button("Restart the game",350,100,300,50,(30,30,30),(0,0,0),40,multiplayer)
            button("Back",850,Height-50,100,40,(30,30,30),(0,0,0),30,game_intro)
            Text('Winners',200,200,(255,255,0),40)
            Text('Losers',450,200,(255,0,0),40)
            Text('Kicked',700,200,(255,0,255),40)
            Text('player'+'            '+'score',190,250,(255,255,255),20)
            Text('player'+'            '+'score',440,250,(255,255,255),20)
            Text('player'+'            '+'score',690,250,(255,255,255),20)
            i=0
            for x,y in los.items():
                Text(str(x)+'         '+str(y),440,270+20*i,(255,0,0),23)
                i+=1
            n=0
            for x,y in win.items():
                Text(str(x)+'         '+str(y),190,270+20*n,(255,255,0),23)
                n+=1
            l=0
            for x,y in k.items():
                Text(str(x)+'         '+str(y),690,270+20*l,(255,0,255),23)
                l+=1                
            pygame.display.update()
        pygame.display.update()
    client.connection.close()

game_intro()
