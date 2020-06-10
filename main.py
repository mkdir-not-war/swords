import pygame
from math import sqrt

#constants
TILE_WIDTH = 16
FPS = 60
MAXINPUTQUEUELEN = 10

# physics
HORZ_FRIC = 0.00975 #0.156/16 @ 30 FPS
VERT_FRIC = 0.00075 #0.012/16 @ 30 FPS
GRAVITY_ACCEL = 80 #55 @ 30 FPS
TIME_STEP = 1.0/FPS

# fudge factors
VEL_CLAMTOZERO_RANGE = 5.0
RECT_FAT_MOD = 1.05

# movement
SIDEWAYS_ACCEL = 230 #130 @ 30 FPS
JUMP_ACCEL = 2800 #1460 @ 30 FPS
JUMP_COOLDOWN_SEC = 0.2

COYOTE_FRAMES = 5
EARLYJUMP_FRAMES = 8

# magic
E_NEUTRAL = 0
E_WATER = 1
E_FIRE = 2
E_WIND = 3

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
		result = pygame.Rect((self.x, self.y), (self.width, self.height))
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

spell_elements = [E_NEUTRAL, E_WATER, E_FIRE, E_WIND]

element_colors = {}
element_colors[E_NEUTRAL] = lightgrey
element_colors[E_WATER] = lightblue
element_colors[E_FIRE] = lightred
element_colors[E_WIND] = lightgreen

magic_combos = {}
for e in spell_elements:
	magic_combos[e] = {}

# EE - attack, EN - buff, NE - shield

magic_combos[E_NEUTRAL][E_FIRE] = 'inner flame'
magic_combos[E_FIRE][E_NEUTRAL] = 'burn souls'
magic_combos[E_FIRE][E_FIRE] = 'soul flare'

magic_combos[E_NEUTRAL][E_WIND] = 'refresh jump'
magic_combos[E_WIND][E_NEUTRAL] = 'tornado'
magic_combos[E_WIND][E_WIND] = 'air pistol'

class MapData:
	def __init__(self, dim=(0, 0)):
		self.width = dim[0]
		self.height = dim[1]
		self.geo = [] # start in top left
		self.spawn = (0, 0) # bottom left!! of spawn loc

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

	def load(self, filename):
		fin = open('./data/%s.txt' % filename)
		linenum = 0
		for line in fin:
			if (linenum == 0):
				spline = line.split(',')
				self.width = int(spline[0])*2
				self.height = int(spline[1])*2
			else:
				# load geometry, each char is 2x2 tiles
				line = line.strip('\n')
				colnum = 0
				botline = []
				for char in line.strip('\n'):
					if (char == '#'):
						self.geo.append(True)
						self.geo.append(True)
						botline.append(True)
						botline.append(True)
					else:
						self.geo.append(False)
						self.geo.append(False)
						botline.append(False)
						botline.append(False)

					if (char == '@'):
						# +1 on y pos to push the pos to bottom left of tile
						self.spawn = (colnum, (linenum-1)*2+1)

					colnum += 2
				for char in botline:
					self.geo.append(char)
			linenum += 1

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
	def __init__(self):
		# physics stuff
		self.physicsbody = PhysicsBody(widthintiles=2, heightintiles=3)
		self.jumps_remaining = 0
		self.jump_timer = 0.0
		self.fall_timer = 0

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

def player_update(player, inputdata):
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

	movedirection = inputdata.get_movedirection()
	jump = inputdata.get_jump()
	recent_jump = inputdata.had_jump(True, frames=EARLYJUMP_FRAMES)
	element = inputdata.get_element()

	# move left and right
	if (movedirection != 0):
		force = tuple_mult((movedirection, 0), SIDEWAYS_ACCEL)
		player.physicsbody.addforce(force)

	# jump
	if (jump and player.jumps_remaining > 0):
		player.halt_vert_vel()
		force = (0, -JUMP_ACCEL)
		player.physicsbody.addforce(force)
		player.jumps_remaining -= 1

	# use magic
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

	return output

class InputDataBuffer:
	def __init__(self):
		self.maxqueuelength = MAXINPUTQUEUELEN
		self.queuelength = 0

		self.movedirection = [] #left or right
		self.jump = []
		self.element = []

	def newinput(self):
		if (self.queuelength == self.maxqueuelength):
			self.movedirection.pop(0)
			self.jump.pop(0)
			self.element.pop(0)
		else:
			self.queuelength += 1

		# put in default values
		self.movedirection.append(0)
		self.jump.append(False)
		self.element.append(-1)

	def set_movedirection(self, val):
		self.movedirection[self.queuelength-1] = val
		return val

	def get_movedirection(self):
		result = self.movedirection[self.queuelength-1]
		return result

	def had_movedirection(self, val, frames=MAXINPUTQUEUELEN):
		assert(frames > 0)
		frame = self.queuelength-1
		result = False
		while (frame >= 0 and frame >= self.queuelength-frames):
			if (self.movedirection[frame] == val):
				result = True
				return result
			frame -= 1
		return result

	def set_jump(self, val):
		self.jump[self.queuelength-1] = val
		return val

	def get_jump(self):
		result = self.jump[self.queuelength-1]
		return result

	def had_jump(self, val, frames=MAXINPUTQUEUELEN):
		assert(frames > 0)
		frame = self.queuelength-1
		result = False
		while (frame >= 0 and frame >= self.queuelength-frames):
			if (self.jump[frame] == val):
				result = True
				return result
			frame -= 1
		return result

	def set_element(self, val):
		self.element[self.queuelength-1] = val
		return val

	def get_element(self):
		result = self.element[self.queuelength-1]
		return result

	def had_element(self, val, frames=MAXINPUTQUEUELEN):
		assert(frames > 0)
		frame = self.queuelength-1
		result = False
		while (frame >= 0 and frame >= self.queuelength-frames):
			if (self.element[frame] == val):
				result = True
				return result
			frame -= 1
		return result



def main():
	pygame.init()

	# Set the width and height of the screen (width, height).
	screendim = (1050, 750)
	midscreen = (screendim[0]//2, screendim[1]//2)
	screen = pygame.display.set_mode(screendim)
	pygame.display.set_caption("swords")

	done = False
	clock = pygame.time.Clock()

	# input stuff
	pygame.joystick.init()

	# player stuff
	player = Player()

	# input stuff
	prev_input = []
	curr_input = [] # int list
	inputdata = InputDataBuffer()

	equipped_element_Q = E_NEUTRAL
	equipped_element_W = E_FIRE
	equipped_element_E = E_WIND


	# Load in the test map
	geometry = MapData()
	geometry.load('map2')
	player.set_pos(geometry.get_spawn(player.physicsbody))

	# physics
	physicsbodies = [player.physicsbody]

	while not done:
		clock.tick(FPS)

		output = []

		global highlight
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
			return '*************'
		debug_func = f

		# keypad handle input
		if pygame.K_ESCAPE in curr_input:
			done = True
		if pygame.K_SPACE in curr_input and pygame.K_SPACE not in prev_input:
			output.append(debug_func())

		moveinput = 0 # only left or right
		if pygame.K_LEFT in curr_input:
			inputdata.set_movedirection(-1)
		if pygame.K_RIGHT in curr_input:
			inputdata.set_movedirection(1)

		if pygame.K_UP in curr_input and not pygame.K_UP in prev_input:
			inputdata.set_jump(True)

		if pygame.K_q in curr_input and not pygame.K_q in prev_input:
			inputdata.set_element(equipped_element_Q)
		elif pygame.K_w in curr_input and not pygame.K_w in prev_input:
			inputdata.set_element(equipped_element_W)
		elif pygame.K_e in curr_input and not pygame.K_e in prev_input:
			inputdata.set_element(equipped_element_E)

		output.extend(player_handleinput(player, inputdata))

		# updates
		output.append(player_update(player, inputdata))

		update_physicsbodies(physicsbodies, geometry)

		# start drawing
		screen.fill(grey)

		for line in output:
			if (not line is None):
				print(line)

		#pygame.draw.circle(screen, lightgrey, (i, j), 1, 1)

		for j in range(geometry.height):
			for i in range(geometry.width):
				if geometry.get_geo(i, j):
					pos = geometry.get_tile2pos(i, j, offset=False)
					pygame.draw.rect(screen, lightgrey, 
						pygame.Rect(pos, (TILE_WIDTH, TILE_WIDTH)))		

		# draw player
		pygame.draw.rect(screen, lightblue, 
			player.physicsbody.rect.get_pyrect())

		# highlight tiles for debug
		DEBUG = True
		if (DEBUG):
			colorlines = {}
			ci = 0
			for tile, color in highlight:
				if not color in colorlines:
					colorlines[color] = ci
					ci += 1
				pygame.draw.rect(screen, pygame.Color(color), 
					Rect(
						(tile.x+ci, tile.y+ci),
						(tile.width-ci*2, tile.height-ci*2)
					).get_pyrect(), 
					1
				)
		

		pygame.display.flip()

		'''
		if (len(highlight) > 0):
			input()
		'''

	pygame.quit()

if __name__=='__main__':
	main()