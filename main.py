import pygame
from math import sqrt

#constants
TILE_WIDTH = 16
FPS = 60

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
COYOTE_FRAMES = 2

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

spell_elements = ['neutral', 'water', 'fire', 'wind']

element_colors = {}
element_colors['neutral'] = lightgrey
element_colors['water'] = lightblue
element_colors['fire'] = lightred
element_colors['wind'] = lightgreen

magic_combos = {}
for e in spell_elements:
	magic_combos[e] = {}

# EE - attack, EN - buff, NE - shield

magic_combos['neutral']['fire'] = 'inner flame'
magic_combos['fire']['neutral'] = 'burn souls'
magic_combos['fire']['fire'] = 'soul flare'

magic_combos['neutral']['wind'] = 'refresh jump'
magic_combos['wind']['neutral'] = 'tornado'
magic_combos['wind']['wind'] = 'air pistol'

class MapData:
	def __init__(self, dim=(0, 0)):
		self.width = dim[0]
		self.height = dim[1]
		self.geo = [] # start in top left
		self.spawn = (0, 0)

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
						self.spawn = (colnum*2, (linenum-1)*2)
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
				assert(len(tiles) == 1)
				diag_direction = (tiles[0].x - pb.rect.x, tiles[0].y - pb.rect.y)
				if (sign(pbdp[0]) == sign(diag_direction[0])):
					diag_tile = tiles[0]

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
							newrecth.y = nearesttilepos[1]
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
						physicsbodies[ri].dp = (0, 0)


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
		self.physicsbody = PhysicsBody(widthintiles=2, heightintiles=2)
		self.can_jump = False
		self.jump_timer = 0.0
		self.fall_timer = 0

		# magic stuff
		self.max_mana = 6
		self.curr_mana = self.max_mana

		self.time_between_recover_mana = 0.8
		self.time_until_recover_mana = 3.0
		self.time_remaining_to_recover = self.time_until_recover_mana

		# spell chain breaks when mana begins recovering
		self.max_spells_saved = self.max_mana
		self.spells_used = [] 
		self.spells_used_len = 0

	def get_pos(self):
		result = self.physicsbody.get_pos()
		return result

	def set_pos(self, pos):
		self.physicsbody.set_pos(pos)

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
	if (not player.can_jump):
		if (player.jump_timer >= JUMP_COOLDOWN_SEC):
			# TODO: update this for coyote-time later
			if (player.physicsbody.get_collidedown()):
				# reset jump timer when you hit the ground
				player.can_jump = True
				player.jump_timer = 0.0
				player.fall_timer = 0
		else:
			player.jump_timer += TIME_STEP
	else:
		if (not player.physicsbody.get_collidedown()):
			player.fall_timer += 1
			if (player.fall_timer >= COYOTE_FRAMES):
				player.can_jump = False

	# handle magic and stamina
	if (player.curr_mana < player.max_mana):
		player.time_remaining_to_recover -= 1.0/30.0
		if (player.time_remaining_to_recover < 0.0):
			player.spells_used = []
			player.spells_used_len = 0
			if (player.time_remaining_to_recover < -player.time_between_recover_mana):
				player.time_remaining_to_recover = 0.0
				player.curr_mana += 1
				return '+'

def player_handleinput(player, inputdata):
	# move left and right
	if (inputdata.movedirection != 0):
		force = tuple_mult((inputdata.movedirection, 0), SIDEWAYS_ACCEL)
		player.physicsbody.addforce(force)

	# jump
	if (inputdata.jump and player.can_jump):
		force = (0, -JUMP_ACCEL)
		player.physicsbody.addforce(force)
		player.can_jump = False

class InputData:
	def __init__(self):
		self.movedirection = 0 # left or right
		self.jump = False

	def clear(self):
		self.movedirection = 0
		self.jump = False

def use_element(player, e):
	if player.curr_mana > 0:
		last_element = None
		if player.spells_used_len > 0:
			last_element = player.spells_used[player.spells_used_len-1]

		player.spells_used.append(e)
		player.spells_used_len += 1
		while (player.spells_used_len > player.max_spells_saved):
			player.spells_used.pop(0)
			player.spells_used_len -= 1

		player.curr_mana -= 1
		player.time_remaining_to_recover = player.time_until_recover_mana

		if not last_element is None and e in magic_combos[last_element]:
			return magic_combos[last_element][e]
		else:
			#return e
			pass
		
	else:
		return 'out of mana'


def main():
	pygame.init()

	# Set the width and height of the screen (width, height).
	screendim = (1050, 750)
	midscreen = (screendim[0]//2, screendim[1]//2)
	screen = pygame.display.set_mode(screendim)
	pygame.display.set_caption("B4J prototype")

	done = False
	clock = pygame.time.Clock()

	# input stuff
	pygame.joystick.init()

	# player stuff
	player = Player()

	# input stuff
	prev_input = []
	curr_input = [] # int list
	inputdata = InputData()

	equipped_element_Q = 'neutral'
	equipped_element_W = 'fire'
	equipped_element_E = 'wind'


	# Load in the test map
	geometry = MapData()
	geometry.load('map1')
	player.set_pos(geometry.get_tile2pos(*geometry.spawn, offset=False))

	# physics
	physicsbodies = [player.physicsbody]

	while not done:
		clock.tick(FPS)

		output = []

		global highlight
		highlight.clear()

		# poll input, put in curr_input and prev_input
		prev_input = curr_input[:]
		inputdata.clear()
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

		debug_func = player.get_pos

		# keypad handle input
		if pygame.K_ESCAPE in curr_input:
			done = True
		if pygame.K_SPACE in curr_input and len(prev_input) == 0:
			output.append(debug_func())

		moveinput = 0 # only left or right
		if pygame.K_LEFT in curr_input:
			inputdata.movedirection = -1
		if pygame.K_RIGHT in curr_input:
			inputdata.movedirection = 1

		if pygame.K_UP in curr_input and not pygame.K_UP in prev_input:
			inputdata.jump = True

		if pygame.K_q in curr_input and not pygame.K_q in prev_input:
			output.append(use_element(player, equipped_element_Q))
		elif pygame.K_w in curr_input and not pygame.K_w in prev_input:
			output.append(use_element(player, equipped_element_W))
		elif pygame.K_e in curr_input and not pygame.K_e in prev_input:
			output.append(use_element(player, equipped_element_E))

		player_handleinput(player, inputdata)

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