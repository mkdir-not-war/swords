import pygame
from pygame.locals import *
from math import sqrt
from enum import IntEnum
import json

# constants
# 20 feels good while being ~70 average fps for now (7/24/20)
TILE_WIDTH = 20

# time
PHYSICS_TIME_STEP = 1.0/100

# camera
ASPECT_RATIO_YX = 1.78
SCREENPERCENTABOVEPLAYER = 0.60
SCREENPERCENTFACINGDIR = 0.54

# physics @ PHYSICS_TIME_STEP = 1/100
GRAVITY_ACCEL = 64
HORZ_FRIC_FORCE = 0.156
VERT_FRIC_FORCE = 0.0089

HORZ_FRIC = HORZ_FRIC_FORCE/TILE_WIDTH
VERT_FRIC = VERT_FRIC_FORCE/TILE_WIDTH

# movement @ PHYSICS_TIME_STEP = 1/100
SIDEWAYS_ACCEL_FORCE = 18.0
JUMP_ACCEL_FORCE = 313.0

SIDEWAYS_ACCEL = SIDEWAYS_ACCEL_FORCE * TILE_WIDTH
JUMP_ACCEL = JUMP_ACCEL_FORCE * TILE_WIDTH

# input constants
MAXINPUTQUEUELEN = 10
HOLDBUTTONTIMESHORT = 10 * 1/60.0
JUMP_COOLDOWN_SEC = 0.2

# fudge factors
VEL_CLAMTOZERO_RANGE = 5.0
RECT_FAT_MOD = 1.05

COYOTE_FRAMES = 5
EARLYJUMP_FRAMES = 8

# magic
E_WATER = 0
E_FIRE = 1
E_WIND = 2
E_ETHER = 3
E_ICE = 4
E_SUN = 5
E_LIFE = 6
E_BLOOD = 7

# debug tiles
highlight = []

def sign(n):
	if (n < 0):
		return -1
	elif (n > 0):
		return 1
	else:
		return 0

def v2_int(v):
	result = (int(v[0]), int(v[1]))
	return result

def v2_dot(v1, v2):
	result = v1[0]*v2[0] + v1[1]*v2[1]
	return result

def v2_add(v1, v2):
	result = (v1[0]+v2[0], v1[1]+v2[1])
	return result

def v2_scale2clamp(v, clamp):
	cw, ch = clamp
	vw, vh = v

	diffx = cw - vw
	diffy = ch - vh

	rw = rh = 0

	if (diffx > diffy):
		rw = cw
		rh = cw * vh / vw
	else:
		rw = ch * vw / vh
		rh = ch	

	return (rw, rh)

def length(v):
	result = sqrt(v[0]**2 + v[1]**2)
	return result

def normalize(v):
	vlen = length(v)
	result = (v[0]/vlen, v[1]/vlen)
	return result

def sum_tuples(tuples):
	resultx = 0
	resulty = 0
	for x, y in tuples:
		resultx += x
		resulty += y
	return (resultx, resulty)

def tuple_mult(tup, scalar):
	resultx = tup[0] * scalar
	resulty = tup[1] * scalar
	return (resultx, resulty)

class Rect:
	def __init__(self, pos, dim):
		self.x = pos[0]
		self.y = pos[1]
		self.width = dim[0]
		self.height = dim[1]

	def copy(self):
		result = Rect((self.x, self.y), (self.width, self.height))
		return result

	def print(self):
		print((self.x, self.y), (self.width, self.height))

	def get_dim(self):
		result = (self.width, self.height)
		return result

	def move(self, dp):
		self.x += dp[0]
		self.y += dp[1]
		return self

	def get_center(self):
		result = (self.x + self.width/2.0, self.y + self.height/2.0)
		return result

	def get_fat(self):
		result = Rect(
			(self.x - (self.width*RECT_FAT_MOD - self.width)/2, self.y), 
			(self.width*RECT_FAT_MOD, self.height)
		)
		return result

	def get_verts(self):
		topleft = (self.x, self.y)
		topright = (self.x+self.width, self.y)
		botleft = (self.x, self.y+self.height)
		botright = (self.x+self.width, self.y+self.height)

		return (topleft, topright, botleft, botright)

	def get_pyrect(self):
		result = pygame.Rect((int(self.x), int(self.y)), (int(self.width), int(self.height)))
		return result

	def contains_point(self, point):
		'''
		using strictly gt/lt on the left and top edges so that
		collision detection doesn't think it's colliding down
		when rubbing a wall on the left. 
		Easy fix and no discernable difference right now.
		'''
		result = (
			point[0] > self.x and
			point[0] < self.x+self.width and
			point[1] > self.y and
			point[1] < self.y+self.height
		)
		return result

	def collides_rect(self, rect):
		sum_rect = Rect(
			(self.x-rect.width/2.0, self.y-rect.height/2.0), 
			(self.width+rect.width, self.height+rect.height)
		)
		point = rect.get_center()
		result = sum_rect.contains_point(point)
		return result

	def contains_rect(self, rect):
		result = True
		for point in rect.get_verts():
			if (not self.contains_point(point)):
				result = False
				break
		return result

grey = pygame.Color(200, 200, 200)
lightgrey = pygame.Color(125, 125, 125)
darkred = pygame.Color(80, 0, 0)
lightred = pygame.Color(250, 100, 100)
lightgreen = pygame.Color(100, 250, 100)
lightblue = pygame.Color(100, 100, 250)
red = pygame.Color('red')
black = pygame.Color('black')

spell_elements = [E_WATER, E_FIRE, E_WIND]

class Camera:
	def __init__(self, pos, screendim):

		width = 0
		height = 0
		x_off = 0
		y_off = 0

		ywidth = screendim[1]*ASPECT_RATIO_YX

		if (ywidth > screendim[0]):
			width = screendim[0]
			height = width//ASPECT_RATIO_YX
			y_off = (screendim[1] - height)//2
		else:
			height = screendim[1]
			width = height*ASPECT_RATIO_YX
			x_off = (screendim[0] - width)//2

		# screen pixels, not game units (must divide out zoom)
		self.width = int(width)
		self.height = int(height)

		# only used to draw camera screen onto parent screen
		self.screenoffset = (int(x_off), int(y_off))

		# gamepixels * zoom = screenpixels
		self.zoom = self.width / screendim[0]

		# game dim
		self.game_width = width / self.zoom
		self.game_height = height / self.zoom

		# game pos
		self.pos = (
			pos[0] - int(self.game_width*SCREENPERCENTFACINGDIR), 
			pos[1] - int(self.game_height*SCREENPERCENTABOVEPLAYER))

	def update_pos(self, playerphysics):
		prevpos = self.pos
		playerpos = playerphysics.get_pos()
		pwidth, pheight = playerphysics.get_dim()
		newposx, newposy = prevpos
		facingdir = playerphysics.entity.facing_direction

		camplayeroffy = int(self.game_height*SCREENPERCENTABOVEPLAYER)
		camplayerxoff_facing = int(self.game_width*(1.0-SCREENPERCENTFACINGDIR))
		if (facingdir < 0):
			camplayerxoff_facing = int(self.game_width*SCREENPERCENTFACINGDIR)

		mincammove = TILE_WIDTH*0.06
		cammoveyboundspercenttop = 0.2
		cammoveyboundspercentbot = 0.22
		camerasmoothmovespeedy = 0.05 # percent of delta-y
		camerasmoothmovespeedx = 0.10 # percent of delta-x

		# only retarget y-position when player out of map range, or grounded
		if (prevpos[1] != (playerpos[1] + pheight//2 - camplayeroffy)):
			ydiff = (playerpos[1] + pheight//2 - camplayeroffy) - prevpos[1]

			yboundsmin = prevpos[1] + self.game_height*cammoveyboundspercenttop
			yboundsmax = prevpos[1] + self.game_height*(1.0-cammoveyboundspercentbot)

			if (playerpos[1]+pheight > yboundsmax or
				playerpos[1] < yboundsmin or
				playerphysics.get_collidedown()):

				if (abs(ydiff) < mincammove):
					# case 1: super close, just move diff
					newposy += ydiff
				else:
					# case 2: far enough, lerp one step
					ydeltamove = ydiff * camerasmoothmovespeedy
					if (abs(ydeltamove) < mincammove):
						# case 3: lerped step is too small, move min step
						ydeltamove = mincammove * sign(ydeltamove)

					newposy += ydeltamove

		# target x-pos to bias facing direction
		if (prevpos[0] != (playerpos[0] + pwidth//2 - camplayerxoff_facing)):

			xdiff = (playerpos[0] + pwidth//2 - camplayerxoff_facing) - prevpos[0]

			if (abs(xdiff) < mincammove):
				newposx += xdiff
			else:
				xdeltamove = xdiff * camerasmoothmovespeedx
				if (abs(xdeltamove) < mincammove):
					xdeltamove = mincammove * sign(xdeltamove)

				newposx += xdeltamove


		self.pos = (newposx, newposy)

	def game2screen(self, x, y):
		xpos = x - self.pos[0]
		ypos = y - self.pos[1]

		result = (
			int(xpos * self.zoom + 0.5),
			int(ypos * self.zoom + 0.5)
		)

		return result

	def get_screenrect(self, rect):
		result = Rect(
			self.game2screen(rect.x, rect.y),
			(
				int(rect.width * self.zoom),
				int(rect.height * self.zoom)
			)
		)
		return result

	def get_camerascreen(self, window):
		result = window.subsurface(
			pygame.Rect(
				self.screenoffset,
				(self.width, self.height)
			)
		)
		return result

	def get_maptilebounds(self, geometry):
		mtx, mty = geometry.get_pos2tile(*self.pos)

		width = self.game_width / TILE_WIDTH + 2
		height = self.game_height / TILE_WIDTH + 2

		result = Rect((int(mtx), int(mty)), (int(width), int(height)))

		return result

	def update_window(self):
		surface = pygame.display.get_surface()
		x, y = size = surface.get_width(), surface.get_height()
		if (x < y):
			width = x
			height = width*ASPECT_RATIO_XY
		else:
			height = y
			width = height//ASPECT_RATIO_XY
		self.width = width
		self.height = height

class MapData:
	def __init__(self):
		self.width = 0
		self.height = 0
		self.geo = [False] * (self.width * self.height)
		self.spawn = (0, 0) # bottom left!! of spawn loc

		# Since tile = 2x2, these will both be at least 3/4th empty. 
		# May need to optimize somehow
		self.spriteindexset = [] # use for saving, [(name, index), ...]
		self.spriteindex_geo = [-1] * (self.width * self.height)
		self.spriteindex_mg = [-1] * (self.width * self.height)

	def get_geospriteindex(self, x, y):
		result = self.spriteindex_geo[x + self.width * y]
		return result

	def get_mgspriteindex(self, x, y):
		result = self.spriteindex_mg[x + self.width * y]
		return result

	def get_geo(self, x, y):
		result = self.geo[x + self.width * y]
		return result

	def get_pos2tile(self, x, y):
		result = (int(x//TILE_WIDTH), int(y//TILE_WIDTH))
		return result

	def get_tile2pos(self, x, y, offset=(0.5, 0.5)):
		if (offset == False):
			offset = (0, 0)
		result = ((x+offset[0])*TILE_WIDTH, (y+offset[1])*TILE_WIDTH)
		return result

	def get_nearesttile(self, x, y):
		result = self.get_pos2tile(x+TILE_WIDTH/2, y+TILE_WIDTH/2)
		return result

	def get_nearesttilepos(self, x, y):
		result = (
			(x+TILE_WIDTH/2)//TILE_WIDTH*TILE_WIDTH, 
			(y+TILE_WIDTH/2)//TILE_WIDTH*TILE_WIDTH)
		return result

	# only returns geometry (in world coord's) that is solid (i.e. True in MapData.geo)
	def get_tilesfromrect(self, rect):
		minx, miny = self.get_pos2tile(rect.x, rect.y)
		maxx, maxy = self.get_pos2tile(rect.x+rect.width, rect.y+rect.height)

		result = []
		for i in range(minx, maxx+1):
			for j in range(miny, maxy+1):
				if self.get_geo(i, j):
					newtile = Rect((i*TILE_WIDTH, j*TILE_WIDTH), (TILE_WIDTH, TILE_WIDTH))
					result.append(newtile)
		return result

	def get_spawn(self):
		location = (self.spawn[0], self.spawn[1])
		result = self.get_tile2pos(*location, offset=False)
		return result

	def load(self, filename, spritebatch):
		self.filename = filename
		fin = open('./data/maps/%s.txt' % filename)

		loadphase = 0
		spriteindextranslator = [None]

		linenum = 0
		for line in fin:
			if (line == '~\n'):
				linenum = 0
				loadphase += 1
				continue

			if (loadphase == 0):
				# map size
				width, height = line.strip('\n').split(',')
				width = int(width) * 2
				height = int(height) * 2

				self.width = width
				self.height = height

				self.geo = [False] * (width * height)
				self.spriteindex_geo = [-1] * (width * height)
				self.spriteindex_mg = [-1] * (width * height)
			elif (loadphase == 1):
				# load spawn position
				spline = line.strip('\n').split(',')
				# +1 on y pos to push the pos to bottom left of tile
				self.spawn = (int(spline[0])*2, int(spline[1])*2 + 1)
			elif (loadphase == 2):
				# load sprites
				name = line.strip('\n').split(',')[1]
				index = spritebatch.add(name, 'scene')
				spriteindextranslator.append(index)
				self.spriteindexset.append((name, index))

			elif (loadphase == 3):
				# load geometry, each char is 2x2 tiles
				sline = line.strip('\n').split(',')
				colnum = 0
				botline = [] # assumes all geometry sprites are exactly 2x2 -- one map tile

				for char in sline:
					if (char != '0'):
						# set sprite index
						spriteindex = spriteindextranslator[int(char)]
						self.spriteindex_geo[linenum*2 * self.width + colnum] = spriteindex
						# set geometry
						self.geo[linenum * 2 * self.width + colnum] = True
						self.geo[linenum * 2 * self.width + colnum + 1] = True
						self.geo[(linenum * 2 + 1) * self.width + colnum] = True
						self.geo[(linenum * 2 + 1) * self.width + colnum + 1] = True
					else:
						self.geo[linenum * 2 * self.width + colnum] = False
						self.geo[linenum * 2 * self.width + colnum + 1] = False
						self.geo[(linenum * 2 + 1) * self.width + colnum] = False
						self.geo[(linenum * 2 + 1) * self.width + colnum + 1] = False

					colnum += 2

			elif (loadphase == 4):
				# load middleground, each char is 2x2 tiles
				sline = line.strip('\n').split(',')
				colnum = 0

				for char in sline:
					if (char != '0'):
						# set sprite index
						spriteindex = spriteindextranslator[int(char)]
						gridindex = linenum*2 * self.width + colnum
						# don't draw midground behind geometry (can't see it anyway)
						if (not self.geo[gridindex]):
							self.spriteindex_mg[gridindex] = spriteindex
					colnum += 2
			
			linenum += 1
				
		fin.close()
		return spritebatch

def update_physicsbodies(entities, numentities, geometry):
	# get all new rects by moving them and reconciling with collisions

	# first, try assuming zero collisions and just move in direction of velocity
	new_rects = []
	for e in entities:

		pb = e.physics
		if (pb is None):
			new_rects.append(None)
			continue

		newrect = pb.rect().copy()

		# add all forces
		sum_forces = sum_tuples(pb.forces)
		# divide out mass
		ddp = tuple_mult(sum_forces, 1/pb.mass)

		# if horizontal velocity is sufficiently close to zero, just make it zero
		if (pb.dp[0] < VEL_CLAMTOZERO_RANGE and pb.dp[0] > -VEL_CLAMTOZERO_RANGE):
			pb.dp = (0.0, pb.dp[1])	

		# update velocity with integration of accel
		pb.dp = v2_add(pb.dp, tuple_mult(ddp, PHYSICS_TIME_STEP))

		'''
		# move() using kinematics and old velocity
		deltapos = v2_add(tuple_mult(ddp, PHYSICS_TIME_STEP*PHYSICS_TIME_STEP*0.5), tuple_mult(pb.dp, PHYSICS_TIME_STEP))
		newrect.move(deltapos)
		'''

		# move() using kinematics and old velocity
		deltapos = tuple_mult(pb.dp, PHYSICS_TIME_STEP)
		newrect.move(deltapos)

		# put it in the list
		new_rects.append(newrect)

		# clear forces
		pb.clearforces()

		# clear collisions
		pb.clearcollisions()

	# if rect collides with geometry, clamp to nearest tile boundary
	for ri in range(numentities):
		rect = new_rects[ri]
		if (rect is None):
			continue

		tiles = geometry.get_tilesfromrect(rect)

		if (len(tiles) > 0):
			# if there are any tiles in get_tilesfromrect(rect), 
			# then there is a collision with geometry

			global highlight

			pb = entities[ri].physics
			pbdp = pb.dp
			nearesttilepos = geometry.get_nearesttilepos(*pb.get_pos())

			highlight.append((Rect(nearesttilepos, (TILE_WIDTH, TILE_WIDTH)), 'green'))

			newrecth = pb.rect().copy()
			newrecth.x += pbdp[0] * PHYSICS_TIME_STEP
			newrecth.y = nearesttilepos[1] # this makes you fall into corners??

			newrectv = pb.rect().copy()
			newrectv.x = nearesttilepos[0] # this prevents getting caught on corners
			newrectv.y += pbdp[1] * PHYSICS_TIME_STEP

			horzcollide = False
			vertcollide = False

			for tile in tiles:
				if (pbdp[0] != 0 and newrecth.collides_rect(tile)):
					horzcollide = True
					if (pbdp[0] > 0):
						pb.collide_right()
						highlight.append((tile, 'black'))
					elif (pbdp[0] < 0):
						pb.collide_left()
						highlight.append((tile, 'black'))

				if (pbdp[1] != 0 and newrectv.collides_rect(tile)):
					vertcollide = True
					if (pbdp[1] > 0):
						pb.collide_down()
						highlight.append((tile, 'red'))
					elif (pbdp[1] < 0):
						pb.collide_up()
						highlight.append((tile, 'red'))

			# if you've collided, and you're moving diagonally, then
			# you would be in a horz or vert collision,
			# UNLESS you've collided perfectly diagonally on a corner.
			diag_tile = None
			diag_direction = (0, 0)
			if (pbdp[0] != 0 and pbdp[1] != 0 and not (vertcollide or horzcollide)):
				# check if moving into the block or away from it
				for tile in tiles:
					diag_direction = (tile.x - pb.rect().x, tile.y - pb.rect().y)
					if (sign(pbdp[0]) == sign(diag_direction[0])):
						diag_tile = tile

			# wall
			if (not pb.get_collidesvert() and pb.get_collideshorz()):
				newrectv.x = nearesttilepos[0]-sign(pbdp[0]) # nudge away from walls
				new_rects[ri] = newrectv
				entities[ri].physics.dp = (0, pbdp[1])

			# floor and ceiling
			elif (pb.get_collidesvert() and not pb.get_collideshorz()):
				newrecth.y = nearesttilepos[1]
				new_rects[ri] = newrecth
				entities[ri].physics.dp = (pbdp[0], 0)

			# concave corner
			elif (pb.get_collidesvert() and pb.get_collideshorz()):
				new_rects[ri] = Rect(nearesttilepos, pb.get_dim())
				entities[ri].physics.dp = (0, 0)

			# convex corner, basically perfect diagonal velocity
			elif (not diag_tile is None and 
				not pb.get_collidesvert() and 
				not pb.get_collideshorz()):
				# corner is above
				if (diag_direction[1] < 0):
					# if falling, continue falling
					if (pbdp[1] > 0):
						new_rects[ri] = Rect(nearesttilepos, pb.get_dim())
						entities[ri].physics.dp = (0, pbdp[1])
					# if rising, stop velocity
					elif (pbdp[1] < 0):
						newrecth.y = nearesttilepos[1]
						new_rects[ri] = newrecth
						entities[ri].physics.dp = (0, 0)
				# corner is below
				elif (diag_direction[1] > 0):
					# if falling, check for the fat catch, otherwise hit like a wall
					if (pbdp[1] > 0):
						fatrectv = newrectv.get_fat()
						if (pbdp[1] != 0 and fatrectv.collides_rect(diag_tile)):
							pb.collide_down()
							highlight.append((tile, 'red'))
							new_rects[ri] = newrecth
							entities[ri].physics.dp = (pbdp[0], 0)
						else:
							newrectv.x = nearesttilepos[0]
							new_rects[ri] = newrectv
							entities[ri].physics.dp = (0, pbdp[1])
					# if rising, continue rising
					elif (pbdp[1] < 0):
						newrecth.y = nearesttilepos[1]
						new_rects[ri] = newrecth
						entities[ri].physics.dp = (0, pbdp[1])


	# if rect collides with other physics bodies and is "solid", 
	# don't move (apply backwards force??)

	# if rect is collides with an attack, don't move

	# resolve rects
	for pbi in range(numentities):
		entities[pbi].x = new_rects[pbi].x
		entities[pbi].y = new_rects[pbi].y

"""
NOTE: implementation of collision assumes all physics bodies have
height and width as integer multiples of TILE_WIDTH
"""
class PhysicsBody:
	def __init__(self, widthintiles=1, heightintiles=1, mass=1.0):
		self.entity = None
		self.widthintiles = widthintiles
		self.heightintiles = heightintiles
		self.dim = (float(widthintiles*TILE_WIDTH), float(heightintiles*TILE_WIDTH))
		self.mass = mass
		self.dp = (0, 0)
		self.forces = []

		# bounding boxes completely within self.rect??

		self.collisions = [0]*4

	def rect(self):
		result = Rect((self.entity.x, self.entity.y), self.dim)
		return result

	def get_pos(self):
		result = (self.entity.x, self.entity.y)
		return result

	def set_pos(self, pos):
		self.entity.x = pos[0]
		self.entity.y = pos[1]

	def get_dim(self):
		result = self.dim
		return result

	def clearforces(self):
		self.forces = []

	def addforce(self, force):
		self.forces.append(tuple_mult(force, TILE_WIDTH))

	def clearcollisions(self):
		self.collisions = [0]*4

	def collide_up(self):
		self.collisions[0] += 1
	def get_collideup(self):
		result = self.collisions[0]
		return result

	def collide_down(self):
		self.collisions[1] += 1
	def get_collidedown(self):
		result = self.collisions[1]
		return result

	def collide_left(self):
		self.collisions[2] += 1
	def get_collideleft(self):
		result = self.collisions[2]
		return result

	def collide_right(self):
		self.collisions[3] += 1
	def get_collideright(self):
		result = self.collisions[3]
		return result

	def get_collidesvert(self):
		result = (self.get_collideup() + self.get_collidedown() > 0)
		return result

	def get_collideshorz(self):
		result = (self.get_collideright() + self.get_collideleft() > 0)
		return result

	def halt_vert_vel(self):
		self.dp = (self.dp[0], 0.0)

class EntityLoader:
	def __init__(self, spritebatch):
		fin = open('./data/entitydata.json')
		self.entitydata = json.load(fin)
		fin.close()

		self.spritebatch = spritebatch

	def create_entity(self, ename, position=(0,0)):
		assert(ename in self.entitydata)

		position = position

		edata = self.entitydata[ename]
		
		spritedata = edata["spritedata"]
		physicsdata = edata["physicsdata"]
		playerenable = edata["player"]

		spriteindex = None
		if (not spritedata is None):
			spriteindex = self.spritebatch.add(spritedata["spritename"], 'actor')

		physics = None
		if (not physicsdata is None):
			physics = PhysicsBody(
				widthintiles=int(physicsdata["width"]), 
				heightintiles=int(physicsdata["height"]))
			# push position up by heightintiles
			position = (position[0], position[1]-(int(physicsdata["height"])*TILE_WIDTH))

		player = None
		if (not playerenable is None):
			player = Player()

		entity = Entity(position=position, spriteindex=spriteindex, physics=physics, player=player)
		return entity

class Entity:
	def __init__(self, position=(0, 0), physics=None, spriteindex=None, animator=None, player=None):
		# common state vars
		self.x, self.y = position
		self.facing_direction = 1 # TODO: encode starting facing dir in spawn_loc on map

		# components
		self.physics = physics
		self.physics.entity = self

		self.player = player
		if (not self.player is None):
			self.player.entity = self

		self.animator = animator
		if (self.animator is None):
			assert(not spriteindex is None)
			self.animator = StaticAnimator(spriteindex)
		self.animator.entity = self

	def draw(self, sb, camera):
		result = self.animator.draw(sb, camera, self.facing_direction)
		return result

class StaticAnimator:
	def __init__(self, spriteindex):
		self.entity = None
		self.spriteindex = spriteindex

	def draw(self, sb, camera, facingdir):
		rect = self.entity.physics.rect()
		rect = camera.get_screenrect(rect)
		fliphorz = (facingdir <= 0)
		blit = sb.draw(self.spriteindex, rect, fliphorz=fliphorz)
		return blit

class Player:
	def __init__(self):
		self.entity = None

		# movement input stuff
		self.jumps_remaining = 0
		self.jump_timer = 0.0
		self.fall_timer = 0
		self.attack_timer = 0

		self.prevjump = False
		self.prevatk = False
		self.atkexecuted = False

		# magic stuff
		self.max_mana = 6
		self.curr_mana = self.max_mana

		self.time_between_recover_mana = 0.8
		self.time_until_recover_mana = 3.0
		self.time_remaining_to_recover = self.time_until_recover_mana

		self.magic_soul = E_FIRE
		self.magic_body = E_FIRE
		self.magic_mind = E_FIRE

		self.last_element = -1

	def get_pos(self):
		result = self.entity.physics.get_pos()
		return result

	def set_pos(self, pos):
		self.entity.physics.set_pos(pos)

def player_update(player):
	# add physics forces (movement force handled in input handling)
	gravity = (0, GRAVITY_ACCEL)
	player.entity.physics.addforce(gravity)

	# apply friction
	fric = (
		-1*sign(player.entity.physics.dp[0])*(player.entity.physics.dp[0]**2)*HORZ_FRIC, 
		-1*sign(player.entity.physics.dp[1])*(player.entity.physics.dp[1]**2)*VERT_FRIC
	)
	player.entity.physics.addforce(fric)

	# jumping logic
	# anything less than max jumps guarantees no coyote-time
	if (player.jumps_remaining == 0 or 
		(player.jumps_remaining < 2 and player.magic_soul == E_WIND)):

		# cooldown should never prevent jumping from ground, only double jumping
		if (player.jump_timer >= JUMP_COOLDOWN_SEC):
			if (player.entity.physics.get_collidedown()):
				# reset jump timer when you hit the ground
				if (player.magic_soul == E_WIND):
					player.jumps_remaining = 2
				else:
					player.jumps_remaining = 1
				player.jump_timer = 0.0
				player.fall_timer = 0
		else:
			player.jump_timer += PHYSICS_TIME_STEP

	# coyote time only occurs at max jumps (walking off a surface)
	elif (not player.entity.physics.get_collidedown()):
		player.fall_timer += 1 # depends on FPS
		if (player.fall_timer >= COYOTE_FRAMES):
			if (player.magic_soul == E_WIND):
				player.jumps_remaining = 1
			else:
				player.jumps_remaining  = 0

	# handle magic and stamina
	if (player.curr_mana < player.max_mana):
		player.time_remaining_to_recover -= PHYSICS_TIME_STEP
		if (player.time_remaining_to_recover < 0.0):
			player.spells_used = []
			player.spells_used_len = 0
			if (player.time_remaining_to_recover < -player.time_between_recover_mana):
				player.time_remaining_to_recover = 0.0
				player.curr_mana += 1
				return '+'

def player_handleinput(playerentity, inputdata):
	output = []

	player = playerentity.player

	# and get current stuff
	movedir = inputdata.get_var(InputDataIndex.MOVE_DIR)
	jump = (inputdata.get_var(InputDataIndex.JUMP) > 0)
	attack = (inputdata.get_var(InputDataIndex.ATTACK) > 0)

	uniquejumppress = (jump and not player.prevjump)

	# move left and right
	if (movedir == InputMoveDir.LEFT or 
		movedir == InputMoveDir.UP_LEFT or 
		movedir == InputMoveDir.DOWN_LEFT):
		playerentity.facing_direction = -1
		force = (-SIDEWAYS_ACCEL, 0)
		playerentity.physics.addforce(force)
	elif (movedir == InputMoveDir.RIGHT or 
		movedir == InputMoveDir.UP_RIGHT or 
		movedir == InputMoveDir.DOWN_RIGHT):
		playerentity.facing_direction = 1
		force = (SIDEWAYS_ACCEL, 0)
		playerentity.physics.addforce(force)

	# jumping & long jumping
	if (uniquejumppress and player.jumps_remaining > 0):
		if (False):#player.sliding):
			pass
		else:
			playerentity.physics.halt_vert_vel()
			force = (0, -JUMP_ACCEL)
			playerentity.physics.addforce(force)
			playerentity.player.jumps_remaining -= 1

	# attacking
	if (attack and not player.prevatk):
			# start attack on new button press
			playerentity.player.atkexecuted = False
			playerentity.player.attack_timer = 0.0
			print("winding up attack")
	elif (playerentity.player.attack_timer > HOLDBUTTONTIMESHORT and 
		not player.atkexecuted):
		# after holding the button sufficiently long, transition to heavy attack
		playerentity.player.atkexecuted = True
		print("heavy attack")
		print()
	elif (player.prevatk and not attack):
		if (player.attack_timer < HOLDBUTTONTIMESHORT):
			# on button release before hold, transition to light attack
			playerentity.player.atkexecuted = True
			print("light attack")
			print()	

	if (player.prevatk and not player.atkexecuted):
		playerentity.player.attack_timer += PHYSICS_TIME_STEP
			

	# dodging

	# ducking & sliding

	# check for spells
	'''
	DOWN -> DOWN_DIR -> DIR -> ATTACK
	UP -> UP_DIR -> DIR -> ATTACK
	'''

	# set prev inputs
	playerentity.player.prevjump = jump
	playerentity.player.prevatk = attack

	return output

class InputMoveDir(IntEnum):
	NONE = 0
	RIGHT = 1
	UP_RIGHT = 2
	UP = 3
	UP_LEFT = 4
	LEFT = 5
	DOWN_LEFT = 6
	DOWN = 7
	DOWN_RIGHT = 8

class InputDataIndex(IntEnum):
	MOVE_DIR = 0
	DUCK = 1
	JUMP = 2
	ATTACK = 3

class InputDataBuffer:
	def __init__(self):
		self.queuelength = 0

		self.vars = []

		# append in order of input data index enum
		for inputtype in InputDataIndex:
			self.vars.append([])

	''' 
	~ joystick event info ~
	JOYAXISMOTION     joy, axis, value
	JOYBALLMOTION     joy, ball, rel
	JOYHATMOTION      joy, hat, value
	JOYBUTTONUP       joy, button
	JOYBUTTONDOWN     joy, button
	'''

	def newinput(self, curr_input):
		if (self.queuelength == MAXINPUTQUEUELEN):
			for varlist in self.vars:
				varlist.pop(0)
		else:
			self.queuelength += 1

		# put in default values
		for varlist in self.vars:
			varlist.append(0)

		# movement
		moveinputvecx, moveinputvecy = (0, 0)

		# check out current input events
		for event in curr_input:
			# keyboard directions
			if (event.type == pygame.KEYDOWN):
				if event.key == pygame.K_LEFT:
					moveinputvecx += -1
				if event.key == pygame.K_RIGHT:
					moveinputvecx += 1
				if event.key == pygame.K_DOWN:
					moveinputvecy += 1
				if event.key == pygame.K_UP:
					moveinputvecy += -1

			# joystick directions
			if (event.type == pygame.JOYAXISMOTION):
				pass
			if (event.type == pygame.JOYHATMOTION):
				if event.hat == 0:
					# haven't checked whether y-value is good on this
					moveinputvecx, moveinputvecy = event.value

			if (event.type == pygame.KEYDOWN):
				# jumping
				if event.key == pygame.K_SPACE:
					self.set_var(InputDataIndex.JUMP, 1)

				# guarding & attacking
				'''
				if event.key == pygame.K_g:
					self.set_var(InputDataIndex.GUARD, 1)
				'''
				if event.key == pygame.K_f:
					self.set_var(InputDataIndex.ATTACK, 1)

			# more joystick actions
			if (event.type == pygame.JOYBUTTONDOWN):
				# jumping & dodging
				if event.button == 0:
					self.set_var(InputDataIndex.JUMP, 1)

		# discrete thumbstick/keyboard directions
		if moveinputvecx > 0:
			slope = moveinputvecy/moveinputvecx
			if (slope < -2.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.DOWN)
				self.set_var(InputDataIndex.DUCK, 1)
			elif (slope > -2.41 and slope < -0.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.DOWN_RIGHT)
				self.set_var(InputDataIndex.DUCK, 1)
			elif (slope > -0.41 and slope < 0.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.RIGHT)
			elif (slope > 0.41 and slope < 2.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.UP_RIGHT)
			elif (slope > 2.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.UP)
		elif moveinputvecx < 0:
			slope = moveinputvecy/moveinputvecx
			if (slope < -2.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.UP)
			elif (slope > -2.41 and slope < -0.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.UP_LEFT)
			elif (slope > -0.41 and slope < 0.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.LEFT)
			elif (slope > 0.41 and slope < 2.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.DOWN_LEFT)
				self.set_var(InputDataIndex.DUCK, 1)
			elif (slope > 2.41):
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.DOWN)
				self.set_var(InputDataIndex.DUCK, 1)
		else:
			if moveinputvecy > 0:
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.DOWN)
				self.set_var(InputDataIndex.DUCK, 1)
			elif moveinputvecy < 0:
				self.set_var(InputDataIndex.MOVE_DIR, InputMoveDir.UP)

	def set_var(self, var_idi, val):
		self.vars[var_idi][self.queuelength-1] = val
		return val

	def get_var(self, var_idi):
		result = self.vars[var_idi][self.queuelength-1]
		return result

class SpriteSheet:
	def __init__(self, data, name):
		self.name = name

		self.image = None
		self.tileswide = 0
		self.tilestall = 0
		self.frameswide = 0
		self.framestall = 0

		self.loadsprite(data, name)

		# use this var to determine when to unload
		self.numloadedmapsusing = 1

	def loadsprite(self, data, name):
		# parse the spritedata.json file in ./data
		datatype = data['datatype']

		if (datatype == 'scene'):
			self.image = pygame.image.load(data[name]['file'])
			self.frameswide = int(data[name]['frameswide'])
			self.framestall = int(data[name]['framestall'])
		elif (datatype == 'actor'):
			self.image = pygame.image.load(data[name]['file'])
			self.tileswide = int(data[name]['tileswide'])
			self.tilestall = int(data[name]['tilestall'])
			self.frameswide = int(data[name]['frameswide'])
			self.framestall = int(data[name]['framestall'])

	def get_image(self):
		result = self.image
		return result

	'''
	maybe more info required here to parse the json file that Aseprite exports
	'''

# one spritebatch for animated sprites, one for not (i.e. geometry)
class SpriteBatch:
	def __init__(self):
		self.length = 0
		self.sprites = []

		fin = open('./data/graphics/scenespritedata.json')
		self.scenespritedata = json.load(fin)
		fin.close()

		fin = open('./data/graphics/actorspritedata.json')
		self.actorspritedata = json.load(fin)
		fin.close()

	def get(self, spriteindex):
		if (spriteindex >= self.length):
			return None
		result = self.sprites[spriteindex]
		return result

	def print(self):
		result = ''
		for i in range(self.length):
			spritename = self.sprites[i].name
			result += '%d\t%s\n' % (i, spritename)
		print(result)

	def add(self, spritename, datatype):
		result = -1
		for i in range(self.length):
			if spritename == self.sprites[i].name:
				result = i
				self.sprites[i].numloadedmapsusing += 1
		if (result < 0):
			# load the new sprite in
			if (datatype == 'actor'):
				newspritesheet = SpriteSheet(self.actorspritedata, spritename)
			elif (datatype == 'scene'):
				newspritesheet = SpriteSheet(self.scenespritedata, spritename)
			self.sprites.append(newspritesheet)
			result = self.length
			self.length += 1

		return result

	def remove(self, spritename):
		# check numloadedmapsusing -- if zero, then unload
		pass

	def draw(self, spriteindex, rect, fliphorz=False):
		image = self.sprites[spriteindex].get_image()
		# scale image to the rect (already zoomed)
		scale = rect.get_dim()
		image = pygame.transform.scale(image, scale)

		result = None

		if (fliphorz):
			image = pygame.transform.flip(image, True, False)
			result = (image, rect.get_pyrect())
		else:
			result = (image, rect.get_pyrect())

		return result

# use for multiplayer
class WorldState:
	def __init__(self):
		self.numentities = 0
		self.entities = []

	def load_ws(self, serialized_world):
		pass

	def serialize(self):
		pass

	def add_entity(self, e):
		self.entities.append(e)
		self.numentities += 1


def main():
	pygame.init()

	# Set the width and height of the screen (width, height).
	screendim = (1024, 720) #use this value when move to C++
	flags = DOUBLEBUF
	window = pygame.display.set_mode(screendim, flags)
	window.set_alpha(None)
	pygame.display.set_caption("swords")

	done = False
	clock = pygame.time.Clock()

	# load data
	spritebatch = SpriteBatch()
	entityloader = EntityLoader(spritebatch)

	# input stuff
	prev_input = []
	curr_input = [] # int list
	inputdata = InputDataBuffer()

	num_joysticks = pygame.joystick.get_count()
	joystick = None
	# TODO: if-statement isn't working very well
	'''
	if num_joysticks > 0:
		joystick = pygame.joystick.Joystick(0) # 0 -> player 1
		joystick.init()	
	'''

	# world state
	worldstate = WorldState()

	# geometry never changes, so no need to be in worldstate
	geometry = MapData()
	geometry.load("widemap", spritebatch)

	# add player
	player = entityloader.create_entity("player-local", position=geometry.get_spawn())
	worldstate.add_entity(player)

	# load fonts
	font = pygame.font.Font('./data/fonts/ARI.ttf', 32)

	'''
	Probably going to be setting up some memory constructs around here
	'''

	camera = Camera(geometry.get_tile2pos(*geometry.spawn), screendim)
	screen = camera.get_camerascreen(window)

	# timing stuff
	t = 0.0
	accum = 0.0

	while not done:
		frametime = clock.tick() # time passed in millisecondss
		accum += frametime/1000.0

		# display FPS
		fps_text = font.render(str(int(clock.get_fps())), 0, red)

		global highlight
		highlight.clear()

		# poll input and update physics 100 times a second
		while (accum >= PHYSICS_TIME_STEP):
			accum -= PHYSICS_TIME_STEP
			t += PHYSICS_TIME_STEP

			# poll input, put in curr_input and prev_input
			events = pygame.event.get()

			# add values to curr_input on input
			for event in events:
				if event.type == pygame.QUIT:
					done = True
				elif (event.type == pygame.JOYBUTTONDOWN or
					event.type == pygame.KEYDOWN):
					curr_input.append(event)

				# if new axis/hat, then remove previous (if any) from curr_input
				elif (event.type == pygame.JOYAXISMOTION or
					event.type == pygame.JOYHATMOTION):
					for cev in curr_input:
						if (event.type == cev.type):
							curr_input.remove(cev)
					if (event.value != (0, 0)):
						curr_input.append(event)

			# remove values from curr_input on release of input
			for r_event in events:
				if (r_event.type == pygame.JOYBUTTONUP):
					for event in curr_input:
						if (event.type == pygame.JOYBUTTONDOWN and
							event.button == r_event.button):
							curr_input.remove(event)
							break
				elif (r_event.type == pygame.KEYUP):
					for event in curr_input:
						if (event.type == pygame.KEYDOWN and 
							event.key == r_event.key):
							curr_input.remove(event)
							break

			# skip update and quit if directed
			for event in curr_input:
				if (event.type == pygame.KEYDOWN and
					event.key == pygame.K_ESCAPE):
					done = True
				elif (event.type == pygame.JOYBUTTONDOWN and
					event.button == 6):
					done = True
			if (done):
				break

			inputdata.newinput(curr_input)

			# update player state/forces by reading inputdata structure
			player_handleinput(player, inputdata)

			# physics and logic updates
			player_update(player.player)

			update_physicsbodies(worldstate.entities, worldstate.numentities, geometry)

			camera.update_pos(player.physics)

		# handle AI less often than physics?
		#megabrain.update()

		# start drawing
		screen.fill(grey)

		# get camera maptile range
		camerabounds = camera.get_maptilebounds(geometry)
		camera_minx = max(camerabounds.x-1, 0)
		camera_miny = max(camerabounds.y-1, 0)
		camera_maxx = min(camerabounds.x + camerabounds.width, geometry.width)
		camera_maxy = min(camerabounds.y + camerabounds.height, geometry.height)

		# draw sprites
		blitlist = []

		# draw background

		# draw middle ground sprites
		for j in range(camera_miny, camera_maxy):
			for i in range(camera_minx, camera_maxx):
				si = geometry.get_mgspriteindex(i, j)
				if (si >= 0):
					rect = Rect(
						geometry.get_tile2pos(i, j, offset=False), 
						(TILE_WIDTH*2, TILE_WIDTH*2)
					)
					rect = camera.get_screenrect(rect)
					blitlist.append(spritebatch.draw(si, rect))
		screen.blits(blitlist)
		blitlist.clear()

		# draw geometry sprites
		for j in range(camera_miny, camera_maxy):
			for i in range(camera_minx, camera_maxx):
				si = geometry.get_geospriteindex(i, j)
				if (si >= 0):
					rect = Rect(
						geometry.get_tile2pos(i, j, offset=False), 
						(TILE_WIDTH*2, TILE_WIDTH*2)
					)
					rect = camera.get_screenrect(rect)
					blitlist.append(spritebatch.draw(si, rect))
		screen.blits(blitlist)
		blitlist.clear()

		# draw player
		playerblit = player.draw(spritebatch, camera)
		screen.blit(*playerblit)
		

		# highlight tiles for debug
		# TODO: fix this to align to cameras
		DEBUG = False
		if (DEBUG):
			colorlines = {}
			ci = 0
			for tile, color in highlight:
				if not color in colorlines:
					colorlines[color] = ci
					ci += 1
				rect = camera.get_screenrect(
					Rect(
						(tile.x+ci, tile.y+ci),
						(tile.width-ci*2, tile.height-ci*2)
					)
				)
				pygame.draw.rect(screen, pygame.Color(color), rect.get_pyrect(), 1)

		screen.blit(fps_text, (1, 1))
		
		pygame.display.flip()

	pygame.quit()

if __name__=='__main__':
	main()