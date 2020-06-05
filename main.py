import pygame
from math import sqrt

#constants
TILE_WIDTH = 32
FPS = 30

# physics
GROUND_FRIC = 0.75
AIR_FRIC = TILE_WIDTH*2
GRAVITY_ACCEL = TILE_WIDTH*15
TIME_STEP = 1.0/FPS

VEL_CLAMTOZERO_RANGE = 0.02

# movement
SIDEWAYS_ACCEL = TILE_WIDTH*15

# debug tiles
highlight = []

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
		result = (
			point[0] >= self.x and
			point[0] < self.x+self.width and
			point[1] >= self.y and
			point[1] < self.y+self.height
		)
		return result

	def collides_rect(self, rect):
		sum_rect = Rect(
			(self.x-rect.width/2, self.y-rect.height/2), 
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
				self.width = int(spline[0])
				self.height = int(spline[1])
			else:
				# load geometry
				line = line.strip('\n')
				colnum = 0
				for char in line.strip('\n'):
					if (char == '#'):
						self.geo.append(True)
					else:
						self.geo.append(False)
					if (char == '@'):
						self.spawn = (colnum, linenum-1)
					colnum += 1
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

		# if velocity is sufficiently close to zero, just make it zero
		'''
		if (pb.dp[0] < VEL_CLAMTOZERO_RANGE and pb.dp[0] > -VEL_CLAMTOZERO_RANGE):
			pb.dp = (0.0, pb.dp[1])
		if (pb.dp[1] < VEL_CLAMTOZERO_RANGE and pb.dp[1] > -VEL_CLAMTOZERO_RANGE):
			pb.dp = (pb.dp[0], 0.0)
		'''

		# move() using kinematics and old velocity
		newrect.move(v2_add(tuple_mult(ddp, TIME_STEP*TIME_STEP*0.5), tuple_mult(pb.dp, TIME_STEP)))

		# update velocity with integration of accel
		pb.dp = v2_add(pb.dp, tuple_mult(ddp, TIME_STEP))

		# put it in the list
		new_rects.append(newrect)

		# clear forces
		pb.clearforces()

	marked = [False]*length

	# if rect collides with geometry, clamp to nearest tile boundary
	for ri in range(length):
		rect = new_rects[ri]
		tiles = geometry.get_tilesfromrect(rect)

		# if there are any tiles in get_tilesfromrect(rect), then there is a collision with geometry
		for tile in tiles:

			pb = physicsbodies[ri]
			pbdp = pb.dp

			nearesttilepos = geometry.get_nearesttilepos(*pb.get_pos())
			newrecth = pb.rect.copy()
			newrectv = pb.rect.copy()

			newrecth.move(tuple_mult((pbdp[0], 0), TIME_STEP))
			newrectv.move(tuple_mult((0, pbdp[1]), TIME_STEP))
			
			if (not newrecth.collides_rect(tile)):
				new_rects[ri] = newrecth
				physicsbodies[ri].dp = (pbdp[0], 0)
			elif (not newrectv.collides_rect(tile)):
				new_rects[ri] = newrectv
				physicsbodies[ri].dp = (0, pbdp[1])
			else:
				new_rects[ri] = nearesttilepos
				physicsbodies[ri].dp = (0, 0)

	# if rect collides with other physics bodies and is "solid", don't move

	# if rect is collides with an attack, don't move

	# resolve rects
	for pbi in range(length):
		if (not marked[pbi]):
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
		self.forces.append(force)

class Player:
	def __init__(self):
		# physics stuff
		self.physicsbody = PhysicsBody()

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
	#player.physicsbody.addforce(gravity)

	# apply friction based on whether in the air or not
	if (False):
		airfric = tuple_mult((player.physicsbody.dp), -AIR_FRIC)
		player.physicsbody.addforce(airfric)
	else:
		groundfric = tuple_mult((player.physicsbody.dp[0], 0), -GROUND_FRIC)
		#player.physicsbody.addforce(groundfric)

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

class InputData:
	def __init__(self):
		self.movedirection = 0 # left or right

	def clear(self):
		self.movedirection = 0

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
	geometry.load('flatmap')
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

		if pygame.K_q in curr_input and len(prev_input) == 0:
			output.append(use_element(player, equipped_element_Q))
		elif pygame.K_w in curr_input and len(prev_input) == 0:
			output.append(use_element(player, equipped_element_W))
		elif pygame.K_e in curr_input and len(prev_input) == 0:
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

		# highlight tiles for debug
		for tile in highlight:
			pygame.draw.rect(screen, black, tile.get_pyrect(), 1)

		# draw player
		pygame.draw.rect(screen, red, 
			player.physicsbody.rect.get_pyrect())

		pygame.display.flip()

	pygame.quit()

if __name__=='__main__':
	main()