import pygame
from math import sqrt
from enum import IntEnum
import json

#constants
TILE_WIDTH = 16
FPS = 60
MAXINPUTQUEUELEN = 10

# camera
ZOOM_MULT = 2.2
CAMERA_WIDTH = 1050
CAMERA_HEIGHT = 750
MOUSE_MOVE_BORDER_MULT = .8
MOUSE_MOVE_SPEED_MULT = 1.7

# physics
HORZ_FRIC = 0.00975
VERT_FRIC = 0.00081
GRAVITY_ACCEL = 68
TIME_STEP = 1.0/FPS

# fudge factors
VEL_CLAMTOZERO_RANGE = 5.0
RECT_FAT_MOD = 1.05

# movement
SIDEWAYS_ACCEL = 245
JUMP_ACCEL = 3830
JUMP_COOLDOWN_SEC = 0.2

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

def v2_dot(v1, v2):
	result = v1[0]*v2[0] + v1[1]*v2[1]
	return result

def v2_add(v1, v2):
	result = (v1[0]+v2[0], v1[1]+v2[1])
	return result

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

grey = pygame.Color(200, 200, 200)
lightgrey = pygame.Color(125, 125, 125)
darkred = pygame.Color(80, 0, 0)
lightred = pygame.Color(250, 100, 100)
lightgreen = pygame.Color(100, 250, 100)
lightblue = pygame.Color(100, 100, 250)
red = pygame.Color('red')
black = pygame.Color('black')

spell_elements = [E_WATER, E_FIRE, E_WIND]

ASPECT_RATIO_YX = 1.4

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

		# screen pixels
		self.width = width
		self.height = height

		self.x_offset = x_off
		self.y_offset = y_off

		# gamepixels * zoom = screenpixels
		self.zoom = self.width / CAMERA_WIDTH * ZOOM_MULT

		# game pos
		self.pos = (
			pos[0] - CAMERA_WIDTH/2/ZOOM_MULT, 
			pos[1] - CAMERA_HEIGHT/2/ZOOM_MULT)

	def update_pos(self, player):
		# TODO: do this smarter
		newpos = player.physicsbody.get_pos()
		pwidth, pheight = player.physicsbody.get_dim()
		self.pos = (
			newpos[0] - CAMERA_WIDTH/2/ZOOM_MULT + pwidth//2, 
			newpos[1] - CAMERA_HEIGHT/2/ZOOM_MULT + pheight//2)

	def get_center(self):
		result = (self.width//2 + self.x_offset, self.height//2 + self.y_offset)
		return result

	def game2screen(self, x, y):
		xpos = x - self.pos[0]
		ypos = y - self.pos[1]

		result = (
			int(xpos * self.zoom + 0.5),
			int(ypos * self.zoom + 0.5)
		)

		return result

	def screen2cam(self, x, y):
		xpos = int((x - self.x_offset) // self.zoom + 0.5)
		ypos = int((y - self.y_offset) // self.zoom + 0.5)

		result = (
			xpos + self.pos[0],
			ypos + self.pos[1]
		)

		return result

	def get_screenrect(self, rect):
		result = Rect(
			self.game2screen(rect.x, rect.y),
			(
				int(rect.width * self.zoom + 0.5), 
				int(rect.height * self.zoom + 0.5)
			)
		)
		return result

	def get_camerascreen(self, window):
		result = window.subsurface(
			pygame.Rect(
				(int(self.x_offset), int(self.y_offset)),
				(int(self.width), int(self.height))
			)
		)
		return result

	def get_maptilebounds(self, geometry):
		mtx, mty = geometry.get_pos2tile(*self.pos)

		width = self.width // (TILE_WIDTH*2/self.zoom)
		height = self.height // (TILE_WIDTH*2/self.zoom)

		result = Rect((int(mtx), int(mty)), (int(width), int(height)))

		return result

	'''
	def get_mousemoverect(self):
		borderdistx = (1.0-MOUSE_MOVE_BORDER_MULT)/2 * self.width
		borderdisty = (1.0-MOUSE_MOVE_BORDER_MULT)/2 * self.height
		result = Rect(
			(self.x_offset + borderdistx, self.y_offset + borderdisty),
			(self.width * MOUSE_MOVE_BORDER_MULT, self.height * MOUSE_MOVE_BORDER_MULT)
		)
		return result
	'''

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
		result = ((x+TILE_WIDTH/2)//TILE_WIDTH*TILE_WIDTH, (y+TILE_WIDTH/2)//TILE_WIDTH*TILE_WIDTH)
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

	def get_spawn(self, physicsbody):
		location = (self.spawn[0], self.spawn[1]-physicsbody.heightintiles)
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
				# load middleground, each char is 2x2 tiles
				sline = line.strip('\n').split(',')
				colnum = 0

				for char in sline:
					if (char != '0'):
						# set sprite index
						spriteindex = spriteindextranslator[int(char)]
						self.spriteindex_mg[linenum*2 * self.width + colnum] = spriteindex
					colnum += 2

			elif (loadphase == 4):
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
			
			linenum += 1
				
		fin.close()
		return spritebatch

def update_physicsbodies(physicsbodies, geometry):
	# get all new rects by moving them and reconciling with collisions

	# first, try assuming zero collisions and just move in direction of velocity
	length = 0
	new_rects = []
	for pb in physicsbodies:
		newrect = pb.rect.copy()
		length += 1

		# add all forces
		sum_forces = sum_tuples(pb.forces)
		# divide out mass
		ddp = tuple_mult(sum_forces, 1/pb.mass)

		# if horizontal velocity is sufficiently close to zero, just make it zero
		if (pb.dp[0] < VEL_CLAMTOZERO_RANGE and pb.dp[0] > -VEL_CLAMTOZERO_RANGE):
			pb.dp = (0.0, pb.dp[1])	

		# move() using kinematics and old velocity
		deltapos = v2_add(tuple_mult(ddp, TIME_STEP*TIME_STEP*0.5), tuple_mult(pb.dp, TIME_STEP))
		newrect.move(deltapos)

		# update velocity with integration of accel
		pb.dp = v2_add(pb.dp, tuple_mult(ddp, TIME_STEP))

		# put it in the list
		new_rects.append(newrect)

		# clear forces
		pb.clearforces()

		# clear collisions
		pb.clearcollisions()

	# if rect collides with geometry, clamp to nearest tile boundary
	for ri in range(length):
		rect = new_rects[ri]
		tiles = geometry.get_tilesfromrect(rect)

		if (len(tiles) > 0):
			# if there are any tiles in get_tilesfromrect(rect), 
			# then there is a collision with geometry

			global highlight

			pb = physicsbodies[ri]
			pbdp = pb.dp
			nearesttilepos = geometry.get_nearesttilepos(*pb.get_pos())

			highlight.append((Rect(nearesttilepos, (TILE_WIDTH, TILE_WIDTH)), 'green'))

			newrecth = pb.rect.copy()
			newrecth.x += pbdp[0] * TIME_STEP
			newrecth.y = nearesttilepos[1] # this makes you fall into corners??

			newrectv = pb.rect.copy()
			newrectv.x = nearesttilepos[0] # this prevents getting caught on corners
			newrectv.y += pbdp[1] * TIME_STEP

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
					diag_direction = (tile.x - pb.rect.x, tile.y - pb.rect.y)
					if (sign(pbdp[0]) == sign(diag_direction[0])):
						diag_tile = tile

			# wall
			if (not pb.get_collidesvert() and pb.get_collideshorz()):
				newrectv.x = nearesttilepos[0]-sign(pbdp[0]) # nudge away from walls
				new_rects[ri] = newrectv
				physicsbodies[ri].dp = (0, pbdp[1])

			# floor and ceiling
			elif (pb.get_collidesvert() and not pb.get_collideshorz()):
				newrecth.y = nearesttilepos[1]
				new_rects[ri] = newrecth
				physicsbodies[ri].dp = (pbdp[0], 0)

			# concave corner
			elif (pb.get_collidesvert() and pb.get_collideshorz()):
				new_rects[ri] = Rect(nearesttilepos, pb.get_dim())
				physicsbodies[ri].dp = (0, 0)

			# convex corner, basically perfect diagonal velocity
			elif (not diag_tile is None and not pb.get_collidesvert() and not pb.get_collideshorz()):
				# corner is above
				if (diag_direction[1] < 0):
					# if falling, continue falling
					if (pbdp[1] > 0):
						new_rects[ri] = Rect(nearesttilepos, pb.get_dim())
						physicsbodies[ri].dp = (0, pbdp[1])
					# if rising, stop velocity
					elif (pbdp[1] < 0):
						newrecth.y = nearesttilepos[1]
						new_rects[ri] = newrecth
						physicsbodies[ri].dp = (0, 0)
				# corner is below
				elif (diag_direction[1] > 0):
					# if falling, check for the fat catch, otherwise hit like a wall
					if (pbdp[1] > 0):
						fatrectv = newrectv.get_fat()
						if (pbdp[1] != 0 and fatrectv.collides_rect(diag_tile)):
							pb.collide_down()
							highlight.append((tile, 'red'))
							new_rects[ri] = newrecth
							physicsbodies[ri].dp = (pbdp[0], 0)
						else:
							newrectv.x = nearesttilepos[0]
							new_rects[ri] = newrectv
							physicsbodies[ri].dp = (0, pbdp[1])
					# if rising, continue rising
					elif (pbdp[1] < 0):
						newrecth.y = nearesttilepos[1]
						new_rects[ri] = newrecth
						physicsbodies[ri].dp = (0, pbdp[1])


	# if rect collides with other physics bodies and is "solid", don't move (apply backwards force??)

	# if rect is collides with an attack, don't move

	# resolve rects
	for pbi in range(length):
		physicsbodies[pbi].rect = new_rects[pbi]

"""
NOTE: implementation of collision assumes all physics bodies have
height and width as integer multiples of TILE_WIDTH
"""
class PhysicsBody:
	def __init__(self, pos=(0, 0), widthintiles=1, heightintiles=1, mass=1.0):
		self.widthintiles = widthintiles
		self.heightintiles = heightintiles
		self.rect = Rect(pos, (float(widthintiles*TILE_WIDTH), float(heightintiles*TILE_WIDTH)))
		self.mass = mass
		self.dp = (0, 0)
		self.forces = []

		# bounding boxes completely within self.rect??

		self.collisions = [0]*4

	def get_pos(self):
		result = (self.rect.x, self.rect.y)
		return result

	def set_pos(self, pos):
		self.rect.x = pos[0]
		self.rect.y = pos[1]

	def get_dim(self):
		result = (self.rect.width, self.rect.height)
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

class Player:
	def __init__(self, spritebatch):
		# draw stuff
		self.spriteindex = spritebatch.add('tallknight', 'actor')
		sprite = spritebatch.get(self.spriteindex)
		width, height = sprite.tileswide, sprite.tilestall

		# physics stuff
		self.physicsbody = PhysicsBody(widthintiles=width, heightintiles=height)
		self.jumps_remaining = 0
		self.jump_timer = 0.0
		self.fall_timer = 0

		# state stuff
		self.facing_direction = 1 # start facing right? Maybe encoded in spawn location on map?

		# magic stuff
		self.max_mana = 6
		self.curr_mana = self.max_mana

		self.time_between_recover_mana = 0.8
		self.time_until_recover_mana = 3.0
		self.time_remaining_to_recover = self.time_until_recover_mana

		self.magic_soul = E_FIRE#E_WIND
		self.magic_body = E_FIRE
		self.magic_mind = E_FIRE

		# spell chain breaks when mana begins recovering
		self.last_element = -1

	def get_pos(self):
		result = self.physicsbody.get_pos()
		return result

	def set_pos(self, pos):
		self.physicsbody.set_pos(pos)

	def halt_vert_vel(self):
		self.physicsbody.dp = (self.physicsbody.dp[0], 0.0)

def player_update(player):
	# add physics forces (movement force handled in input handling)
	gravity = (0, GRAVITY_ACCEL)
	player.physicsbody.addforce(gravity)

	# apply friction
	fric = (
		-1*sign(player.physicsbody.dp[0])*(player.physicsbody.dp[0]**2)*HORZ_FRIC, 
		-1*sign(player.physicsbody.dp[1])*(player.physicsbody.dp[1]**2)*VERT_FRIC
	)
	player.physicsbody.addforce(fric)

	# jumping logic
	# anything less than max jumps guarantees no coyote-time
	if (player.jumps_remaining == 0 or 
		(player.jumps_remaining < 2 and player.magic_soul == E_WIND)):

		# cooldown should never prevent jumping from ground, only double jumping
		if (player.jump_timer >= JUMP_COOLDOWN_SEC):
			if (player.physicsbody.get_collidedown()):
				# reset jump timer when you hit the ground
				if (player.magic_soul == E_WIND):
					player.jumps_remaining = 2
				else:
					player.jumps_remaining = 1
				player.jump_timer = 0.0
				player.fall_timer = 0
		else:
			player.jump_timer += TIME_STEP

	# coyote time only occurs at max jumps (walking off a surface)
	elif (not player.physicsbody.get_collidedown()):
		player.fall_timer += 1 # depends on FPS
		if (player.fall_timer >= COYOTE_FRAMES):
			if (player.magic_soul == E_WIND):
				player.jumps_remaining = 1
			else:
				player.jumps_remaining  = 0

	# handle magic and stamina
	if (player.curr_mana < player.max_mana):
		player.time_remaining_to_recover -= TIME_STEP
		if (player.time_remaining_to_recover < 0.0):
			player.spells_used = []
			player.spells_used_len = 0
			if (player.time_remaining_to_recover < -player.time_between_recover_mana):
				player.time_remaining_to_recover = 0.0
				player.curr_mana += 1
				return '+'

def player_handleinput(player, inputdata):
	output = []

	movedirection = inputdata.get_var(InputDataIndex.MOVE_DIR)
	jump = (inputdata.get_var(InputDataIndex.JUMP) > 0)
	recent_jump = inputdata.had_var(InputDataIndex.JUMP, 1, frames=EARLYJUMP_FRAMES)

	# move left and right
	if (movedirection != 0):
		player.facing_direction = movedirection
		force = tuple_mult((movedirection, 0), SIDEWAYS_ACCEL)
		player.physicsbody.addforce(force)

	# jump
	if (jump and player.jumps_remaining > 0):
		player.halt_vert_vel()
		force = (0, -JUMP_ACCEL)
		player.physicsbody.addforce(force)
		player.jumps_remaining -= 1

	# use magic
	'''
	if element >= 0:
		if player.curr_mana > 0:
			lastelement = player.last_element
			output.append(element)
			if lastelement >= 0 and element in magic_combos[lastelement]:
				# don't expend mana until a combo is successful
				output.append('%d+%s -> %s' % (lastelement, element, magic_combos[lastelement][element]))
				player.curr_mana -= 1
				player.time_remaining_to_recover = player.time_until_recover_mana
				# refresh last element so as not to overlap combos
				player.last_element = -1
			else:
				player.last_element = element
		else:
			output.append('out of mana')
	'''

	return output

class InputDataIndex(IntEnum):
	MOVE_DIR = 0
	DUCK = 1
	JUMP = 2

class InputDataBuffer:
	def __init__(self):
		self.maxqueuelength = MAXINPUTQUEUELEN
		self.queuelength = 0

		self.vars = []

		# append in order of input data index enum
		self.vars.append([]) # movedir 0
		self.vars.append([]) # duck 1
		self.vars.append([]) # jump 2

	def newinput(self):
		if (self.queuelength == self.maxqueuelength):
			for varlist in self.vars:
				varlist.pop(0)
		else:
			self.queuelength += 1

		# put in default values
		for varlist in self.vars:
			varlist.append(0)

	def set_var(self, var_idi, val):
		self.vars[var_idi][self.queuelength-1] = val
		return val

	def get_var(self, var_idi):
		result = self.vars[var_idi][self.queuelength-1]
		return result

	def had_var(self, var_idi, val, frames=MAXINPUTQUEUELEN):
		assert(frames > 0)
		frame = self.queuelength-1
		result = False
		while (frame >= 0 and frame >= self.queuelength-frames):
			if (self.vars[var_idi][frame] == val):
				result = True
				return result
			frame -= 1
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

		fin = open('./data/scenespritedata.json')
		self.scenespritedata = json.load(fin)
		fin.close()

		fin = open('./data/actorspritedata.json')
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

	def draw(self, screen, spriteindex, rect, fliphorz=False):
		image = self.sprites[spriteindex].get_image()
		# scale image to the rect (already zoomed)
		scale = (int(rect.width), int(rect.height))
		image = pygame.transform.scale(image, scale)

		result = None

		if (fliphorz):
			image = pygame.transform.flip(image, True, False)
			result = (image, rect.get_pyrect())
		else:
			result = (image, rect.get_pyrect())

		return result


def main():
	pygame.init()

	# Set the width and height of the screen (width, height).
	screendim = (800, 600)
	window = pygame.display.set_mode(screendim)
	pygame.display.set_caption("swords")

	done = False
	clock = pygame.time.Clock()

	# cache structure for all sprite flyweights
	spritebatch = SpriteBatch()

	# input stuff
	pygame.joystick.init()

	# player stuff
	player = Player(spritebatch)

	# input stuff
	prev_input = []
	curr_input = [] # int list
	inputdata = InputDataBuffer()

	# DEBUGGING
	filename = 'widemap'

	# Load in the test map
	geometry = MapData()
	geometry.load(filename, spritebatch)
	player.set_pos(geometry.get_spawn(player.physicsbody))

	# physics
	physicsbodies = [player.physicsbody]


	# load images
	playerimg = pygame.image.load('./res/actors/player/knight01.png')

	# load fonts
	''' sample font code, but pretty pygame specific.
	# font = pygame.font.Font('fontname.ttf', 32)
	# text = font.render('test', True, black, white)
	# screen.blit(text, rect)
	'''

	'''
	Probably going to be setting up some memory constructs around here
	'''

	camera = Camera(geometry.get_tile2pos(*geometry.spawn), screendim)
	screen = camera.get_camerascreen(window)

	while not done:
		clock.tick(FPS)

		output = []

		global highlight
		global drawcalls
		highlight.clear()

		# poll input, put in curr_input and prev_input
		prev_input = curr_input[:]
		inputdata.newinput()
		for event in pygame.event.get(): # User did something.
			if event.type == pygame.QUIT: # If user clicked close.
				done = True # Flag that we are done so we exit this loop.
			elif event.type == pygame.JOYBUTTONDOWN:
				print("Joystick button pressed.")
			elif event.type == pygame.KEYDOWN:
				curr_input.append(event.key)
			elif event.type == pygame.KEYUP:
				if event.key in curr_input:
					curr_input.remove(event.key)

		def f():
			return '~~~~~~~~~~~~~~'
		debug_func = f

		# keypad handle input
		if pygame.K_ESCAPE in curr_input:
			done = True
		if pygame.K_SPACE in curr_input and pygame.K_SPACE not in prev_input:
			output.append(debug_func())

		# movement
		moveinput = 0 # only left or right
		if pygame.K_LEFT in curr_input:
			inputdata.set_var(InputDataIndex.MOVE_DIR, -1)
		if pygame.K_RIGHT in curr_input:
			inputdata.set_var(InputDataIndex.MOVE_DIR, 1)
		if pygame.K_DOWN in curr_input:
			inputdata.set_var(InputDataIndex.DUCK, 1)

		if pygame.K_UP in curr_input and not pygame.K_UP in prev_input:
			inputdata.set_var(InputDataIndex.JUMP, 1)
		


		# attacks & combos
		if pygame.K_UP in curr_input and not pygame.K_UP in prev_input:
			pass
			#inputdata.set_jump(True)

		output.extend(player_handleinput(player, inputdata))

		# updates
		output.append(player_update(player))

		update_physicsbodies(physicsbodies, geometry)

		camera.update_pos(player)

		# start drawing
		screen.fill(grey)

		for line in output:
			if (not line is None):
				print(line)

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
					blitlist.append(spritebatch.draw(screen, si, rect))
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
					blitlist.append(spritebatch.draw(screen, si, rect))
		screen.blits(blitlist)
		blitlist.clear()

		# draw player
		playerpos = player.physicsbody.get_pos()
		playerrect = Rect(playerpos, player.physicsbody.get_dim())
		playerrect = camera.get_screenrect(playerrect)
		playerblit = spritebatch.draw(
			screen, player.spriteindex, playerrect, fliphorz=(player.facing_direction <= 0))
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


		# draw all geo
		'''
		for j in range(geometry.height):
			for i in range(geometry.width):
				if (geometry.get_geo(i, j)):
					rect = camera.get_screenrect(
						Rect(
							geometry.get_tile2pos(i, j, offset=False),
							(TILE_WIDTH, TILE_WIDTH)
						)
					)
					pygame.draw.rect(screen, black, rect.get_pyrect(), 1)
		'''
		

		pygame.display.flip()

		'''
		if (len(highlight) > 0):
			input()
		'''

	pygame.quit()

if __name__=='__main__':
	main()