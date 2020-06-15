import pygame
from math import sqrt
from enum import IntEnum

# constants
TILE_WIDTH = 16
FPS = 60
MAXINPUTQUEUELEN = 10

# input codes
MOUSE_LEFT = 1
MOUSE_MID = 2
MOUSE_RIGHT = 3

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



class MapData:
	def __init__(self, filename):
		self.filename = filename

		self.width = 0
		self.height = 0
		self.geo = [] # start in top left
		self.spawn = (0, 0) # bottom left!! of spawn loc

	def get_geo(self, x, y):
		result = self.geo[x + self.width * y]
		return result

	def set_geoon(self, x, y):
		self.geo[x + self.width * y] = True

	def set_geooff(self, x, y):
		self.geo[x + self.width * y] = False

	def maptile_add(self, mtx, mty):
		x, y = mtx*2, mty*2
		if (not self.get_geo(x, y)):
			self.set_geoon(x, y)
			self.set_geoon(x+1, y)
			self.set_geoon(x, y+1)
			self.set_geoon(x+1, y+1)

	def maptile_remove(self, mtx, mty):
		x, y = mtx*2, mty*2
		if (self.get_geo(x, y)):
			self.set_geooff(x, y)
			self.set_geooff(x+1, y)
			self.set_geooff(x, y+1)
			self.set_geooff(x+1, y+1)

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

	def load(self):
		fin = open('./data/%s.txt' % self.filename)
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
		fin.close()

	def save(self):
		fileoutput = []

		# first line: <width>,<height>
		fileoutput.append('%d,%d' % (self.width//2, self.height//2))

		# walls(#), spaces( ) or spawn(@)
		for i in range(10):
			fileoutput.append('poop')

		# open file, write fileoutput to it
		splitfile = self.filename.split('(')
		filenum = 1
		if (len(splitfile) > 1):
			filenum += int(splitfile[1][:-1])
		self.filename = '%s(%d)' % (splitfile[0], filenum)

		filename = './data/%s.txt' % self.filename
		fout = open(filename, 'w')
		for line in fileoutput:
			fout.write(line + '\n')
		fout.close()

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

def handle_input(cin, geometry):
	if (cin == 'save'):
		geometry.save()

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

	# input stuff
	prev_input = []
	curr_input = [] # int list
	# may have to make input lists into dicts, with "key" and "mouse" keys
	mousepos = None
	inputdata = InputDataBuffer()

	# Load in the test map
	geometry = MapData('map2')
	geometry.load()

	while not done:
		clock.tick(FPS)

		cin = None
		output = []

		# poll input, put in curr_input and prev_input
		prev_input = curr_input[:]
		inputdata.newinput()
		for event in pygame.event.get(): # User did something.
			if event.type == pygame.QUIT: # If user clicked close.
				done = True # Flag that we are done so we exit this loop.
			elif event.type == pygame.KEYDOWN:
				curr_input.append(event.key)
			elif event.type == pygame.KEYUP:
				# idk if this is even necessary??
				if event.key in curr_input:
					curr_input.remove(event.key)
			elif event.type == pygame.MOUSEBUTTONDOWN:
				curr_input.append(event.button)
			elif event.type == pygame.MOUSEBUTTONUP:
				# same quesiton as keyup
				if event.button in curr_input:
					curr_input.remove(event.button)

		def f():
			return '*************'
		debug_func = f

		# keypad handle input
		if pygame.K_ESCAPE in curr_input:
			done = True
		if pygame.K_RETURN in curr_input and pygame.K_RETURN not in prev_input:
			cin = input('>> ')
			handle_input(cin, geometry)
		if pygame.K_SPACE in curr_input and pygame.K_SPACE not in prev_input:
			pass

		# mouse input
		mouse_pos = pygame.mouse.get_pos()
		mouse_maptile = None
		# screen coords -> world coords -> tile
		if (not mouse_pos is None):
			x, y = geometry.get_pos2tile(*mouse_pos) 
			mouse_maptile = (x//2, y//2)

		if MOUSE_LEFT in curr_input:
			geometry.maptile_add(*mouse_maptile)
		if MOUSE_MID in curr_input:
			geometry.maptile_remove(*mouse_maptile)
		if MOUSE_RIGHT in curr_input and MOUSE_RIGHT not in prev_input:
			print('poop right')

		# start drawing
		screen.fill(grey)

		for line in output:
			if (not line is None):
				print(line)

		for j in range(geometry.height):
			for i in range(geometry.width):
				if geometry.get_geo(i, j):
					pos = geometry.get_tile2pos(i, j, offset=False)
					pygame.draw.rect(screen, lightgrey, 
						pygame.Rect(pos, (TILE_WIDTH, TILE_WIDTH)))		

		if (not mouse_pos is None):
			pygame.draw.rect(screen, black, 
				Rect(
					(mouse_pos[0] - mouse_pos[0]%(TILE_WIDTH*2), 
					mouse_pos[1] - mouse_pos[1]%(TILE_WIDTH*2)),
					(TILE_WIDTH*2, TILE_WIDTH*2)
				).get_pyrect(), 
				1
			)

		pygame.display.flip()


	pygame.quit()

if __name__=='__main__':
	main()