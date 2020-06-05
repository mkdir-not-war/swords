import pygame

#constants
TILE_WIDTH = 32
FPS = 30

# physics
GROUND_FRIC = 1.0
AIR_FRIC = 1.0
GRAVITY_ACCEL = 10
TIME_STEP = 1.0/FPS

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
		self.pos = pos
		self.x = pos[0]
		self.y = pos[1]
		self.dim = dim
		self.width = dim[0]
		self.height = dim[1]

	def move(self, dp):
		self.x += dp[0]
		self.y += dp[1]
		return self

	def get_center(self):
		result = ((self.x + self.width)/2.0, (self.y + self.height)/2.0)
		return result

	def contains_point(self, point):
		result = (
			point >= self.x and
			point < self.x+self.width and
			point >= self.y and
			point < self.y+self.height
		)
		return result

	def collides_rect(self, rect):
		sumrect = ()

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

def update_physicsbodies(physicsbodies):
	# get all new rects
	length = 0
	new_rects = []
	for pb in physicsbodies:
		newrect = pb.rect
		length += 1

		# add all forces
		sum_forces = sum_tuples(pb.forces)
		# divide out mass and apply gravity
		ddp = tuple_mult((sum_forces[0]/pb.mass, sum_forces[1]/pb.mass + GRAVITY_ACCEL), TIME_STEP/2.0)

		# apply to velocity
		pb.dp = sum_tuples([pb.dp, ddp])

		# get delta position and apply with move()
		newrect.move(tuple_mult(pb.dp, TIME_STEP))

		# put it in the list
		new_rects.append(newrect)

	# if rect collides with geometry, clamp to nearest tile boundary

	# if rect collides with other physics bodies and is "solid", mark

	# if rect is collides with an attack, mark

	# resolve rects
	for pbi in range(length):
		physicsbodies[pbi].rect = new_rects[pbi]

class PhysicsBody:
	def __init__(self, pos=(0, 0), width=TILE_WIDTH, height=TILE_WIDTH, mass=1.0):
		self.rect = Rect(pos, (width, height))
		self.mass = mass
		self.dp = (0, 0)
		self.forces = []

	def get_pos(self):
		result = (self.rect.x, self.rect.y)
		return result

	def get_dim(self):
		result = (self.rect.width, self.rect.height)
		return result

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

def player_update(player):
	# thirty frames per second => 33 ms per frame
	if (player.curr_mana < player.max_mana):
		player.time_remaining_to_recover -= 1.0/30.0
		if (player.time_remaining_to_recover < 0.0):
			player.spells_used = []
			player.spells_used_len = 0
			if (player.time_remaining_to_recover < -player.time_between_recover_mana):
				player.time_remaining_to_recover = 0.0
				player.curr_mana += 1
				return '+'

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
		result = (x//TILE_WIDTH, y//TILE_WIDTH)
		return result

	def get_tile2pos(self, x, y, offset=(0.5, 0.5)):
		if (offset == False):
			offset = (0, 0)
		result = ((x+offset[0])*TILE_WIDTH, (y+offset[1])*TILE_WIDTH)
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

	equipped_element_Q = 'neutral'
	equipped_element_W = 'fire'
	equipped_element_E = 'wind'


	# Load in the test map
	geometry = MapData()
	geometry.load('map1')

	# physics
	physicsbodies = [player.physicsbody]

	while not done:
		clock.tick(FPS)

		output = []

		# poll input, put in curr_input and prev_input
		prev_input = curr_input[:]
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
		moveinput_dir = [0, 0]
		if pygame.K_ESCAPE in curr_input:
			done = True
		if pygame.K_SPACE in curr_input and len(prev_input) == 0:
			output.append(debug_func())

		if pygame.K_q in curr_input and len(prev_input) == 0:
			output.append(use_element(player, equipped_element_Q))
		elif pygame.K_w in curr_input and len(prev_input) == 0:
			output.append(use_element(player, equipped_element_W))
		elif pygame.K_e in curr_input and len(prev_input) == 0:
			output.append(use_element(player, equipped_element_E))

		# updates
		output.append(player_update(player))

		update_physicsbodies(physicsbodies)

		# start drawing
		screen.fill(grey)

		for line in output:
			if (not line is None):
				print(line)

		#pygame.draw.circle(screen, lightgrey, (i, j), 1, 1)

		for j in range(geometry.height):
			for i in range(geometry.width):
				if geometry.get_geo(i, j):
					pos = geometry.get_tile2pos(i, j)
					pygame.draw.rect(screen, lightgrey, 
						pygame.Rect(pos, (TILE_WIDTH, TILE_WIDTH)))

		pygame.display.flip()

	pygame.quit()

if __name__=='__main__':
	main()