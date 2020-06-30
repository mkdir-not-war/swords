import pygame
from math import sqrt
from enum import IntEnum
from tkinter import Tk 
from tkinter.filedialog import askopenfilename
import sys
import json

# constants
TILE_WIDTH = 16
FPS = 60
MAXINPUTQUEUELEN = 10

# input codes
MOUSE_LEFT = 1
MOUSE_MID = 2
MOUSE_RIGHT = 3

# camera
ZOOM_MULT = 3.0
CAMERA_WIDTH = 1050
CAMERA_HEIGHT = 750
MOUSE_MOVE_BORDER_MULT = .8
MOUSE_MOVE_SPEED_MULT = 1.9

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

	def get_dim(self):
		result = (self.width, self.height)
		return result

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
green = pygame.Color(0, 250, 0)
lightgreen = pygame.Color(100, 250, 100)
lightblue = pygame.Color(100, 100, 250)
red = pygame.Color('red')
black = pygame.Color('black')

pygame.font.init()
font_arial = pygame.font.Font("./data/fonts/ARI.ttf", 16)

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
		self.zoom = int(self.width / CAMERA_WIDTH * ZOOM_MULT)

		# game pos
		self.pos = (
			pos[0] - CAMERA_WIDTH/2/ZOOM_MULT, 
			pos[1] - CAMERA_HEIGHT/2/ZOOM_MULT)

	def update_pos(self, newpos):
		self.pos = newpos

	def get_center(self):
		result = (self.width//2 + self.x_offset, self.height//2 + self.y_offset)
		return result

	def game2screen(self, x, y):
		xpos = x - self.pos[0]
		ypos = y - self.pos[1]

		result = (
			xpos * self.zoom,
			ypos * self.zoom
		)

		return result

	def screen2cam(self, x, y):
		xpos = (x - self.x_offset) // self.zoom
		ypos = (y - self.y_offset) // self.zoom

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

	def gamerect2screen(self, rect):
		result = Rect(
			self.game2screen(rect.x, rect.y),
			tuple_mult((rect.width, rect.height), self.zoom))
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

	def get_mousemoverect(self):
		borderdistx = (1.0-MOUSE_MOVE_BORDER_MULT)/2 * self.width
		borderdisty = (1.0-MOUSE_MOVE_BORDER_MULT)/2 * self.height
		result = Rect(
			(self.x_offset + borderdistx, self.y_offset + borderdisty),
			(self.width * MOUSE_MOVE_BORDER_MULT, self.height * MOUSE_MOVE_BORDER_MULT)
		)
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

'''
doesn't fuck with self.geo because it doesn't matter for the editor
'''
def newmap(spritebatch):
	filename = input('filename: ')

	width = int(input('map width: '))*2
	height = int(input('map height: '))*2

	result = MapData(filename=filename, dim=(width, height))

	result.spriteindex_geo = [-1] * (width * height)
	result.spriteindex_mg = [-1] * (width * height)

	result.spawn = (2, self.height-3)

	# greybox collision border around the map
	index = spritebatch.add('bluebox')
	result.spriteindexset.append(('bluebox', index))

	xs = [0, width//2-1]
	ys = [0, height//2-1]

	for j in range(height//2):
		for i in range(width//2):
			if (i in xs or j in ys):
				x, y = i*2, j*2
				result.spriteindex_geo[x + width * y] = index

	return result

class MapData:
	def __init__(self, filename=None, dim=(0,0)):
		self.filename = filename

		self.width = dim[0]
		self.height = dim[1]
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
		print(len(self.spriteindex_mg), x+self.width*y)

		result = self.spriteindex_mg[x + self.width * y]
		return result

	def get_geo(self, x, y):
		result = self.geo[x + self.width * y]
		return result

	'''
	doesn't fuck with self.geo because it doesn't matter for the editor
	'''
	def add_geosprite(self, spritename, spriteindex, mappos):
		mtx, mty = mappos
		if (mtx > 0 and mtx < self.width//2-1 and mty > 0 and mty < self.height//2-1):
			x, y = mtx*2, mty*2
			# confirm that we're not overwriting some existing geo sprite
			assert(self.get_geospriteindex(x, y) == -1)

			# add the geo sprite to the array
			self.spriteindex_geo[x + self.width * y] = spriteindex
			newindex = True
			for name, index in self.spriteindexset:
				if (index == spriteindex):
					newindex = False
					assert(name == spritename)
					break
			if (newindex):
				self.spriteindexset.append((spritename, spriteindex))

	'''
	doesn't fuck with self.geo because it doesn't matter for the editor
	'''
	def remove_geosprite(self, mappos):
		mtx, mty = mappos
		if (mtx > 0 and mtx < self.width//2-1 and mty > 0 and mty < self.height//2-1):
			x, y = mtx*2, mty*2

			# remove the geo sprite from the array
			self.spriteindex_geo[x + self.width * y] = -1

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
			(y+TILE_WIDTH/2)//TILE_WIDTH*TILE_WIDTH
		)
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

	def set_spawn(self, x, y):
		self.spawn = (x*2, y*2+1)

	def load(self, spritebatch):
		fin = open('./data/maps/%s.txt' % self.filename)

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
				index = spritebatch.add(name)
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
						self.geo.append(True)
						self.geo.append(True)
						botline.append(True)
						botline.append(True)
					else:
						self.geo.append(False)
						self.geo.append(False)
						botline.append(False)
						botline.append(False)

					colnum += 2

				for char in botline:
					self.geo.append(char)

			
			linenum += 1
				
		fin.close()
		return spritebatch

	'''
	loading infers collision geometry from sprite locations, doesn't actually save it
	'''
	def save(self, spritebatch):
		fileoutput = []
		spriteindextranslator = [None]

		# map dimensions
		fileoutput.append('%d,%d\n' % (self.width//2, self.height//2))
		fileoutput.append('~\n')

		# spawn location
		fileoutput.append('%d,%d\n' % (self.spawn[0]//2, self.spawn[1]//2))
		fileoutput.append('~\n')

		# sprite indexs
		for index in range(len(self.spriteindexset)):
			name, si = self.spriteindexset[index]
			fileoutput.append('%d,%s\n' % (index+1, name))
		fileoutput.append('~\n')

		# middleground sprite indexs
		for j in range(self.height//2):
			line = []
			for i in range(self.width//2):
				si = self.spriteindex_mg[j*2 * self.width + i*2]
				if (si >= 0):
					name = spritebatch.sprites[si].name
					mapindex = None
					for index in range(len(self.spriteindexset)):
						sname, si = self.spriteindexset[index]
						if (name == sname):
							mapindex = index+1
					line.append('%d,' % mapindex)
				else:
					line.append('0,')
			fileoutput.append(''.join(line).strip(',') + '\n')
		fileoutput.append('~\n')

		# geometry sprite indexs
		for j in range(self.height//2):
			line = []
			for i in range(self.width//2):
				si = self.spriteindex_geo[j*2 * self.width + i*2]
				if (si >= 0):
					name = spritebatch.sprites[si].name
					mapindex = None
					for index in range(len(self.spriteindexset)):
						sname, si = self.spriteindexset[index]
						if (name == sname):
							mapindex = index+1
					line.append('%d,' % mapindex)
				else:
					line.append('0,')
			fileoutput.append(''.join(line).strip(',') + '\n')

		# open file, write fileoutput to it
		# strip the last '\n' from the fileoutput before writing
		fileoutput[-1] = fileoutput[-1][:-1]
		# write out file
		filename = './data/maps/%s.txt' % self.filename
		fout = open(filename, 'w')
		for line in fileoutput:
			fout.write(line)
		fout.close()

		return filename

class InputDataIndex(IntEnum):
	MOVE_DIR = 0
	DUCK = 1
	JUMP = 2

class InputMode(IntEnum):
	NORMAL = 0
	PAINT = 1

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

class HUD_Function:
	def __init__(self, name, func):
		self.func = func
		self.surface = font_arial.render(name, True, (0, 128, 0))
		self.highlighted = font_arial.render(name, True, (200, 0, 0))
		self.yoff = 0
		self.mousehover = False
		self.visible = True # use this to hide "add geo" if there's already geo, etc

class HUD_Element:
	def __init__(self, geometry, spritebatch):
		self.active = False
		self.pos = None
		self.maptile = None

		self.geometry = geometry
		self.spritebatch = spritebatch

		self.functions = []
		self.functions.append(HUD_Function('add geometry', self.add_geometry))
		self.functions.append(HUD_Function('remove geometry', self.remove_geometry))
		self.functions.append(HUD_Function('set spawn', self.set_spawn))

		self.xoff = 10
		self.yoff = 10
		self.width = 160
		self.heightperfunc = 24

		self.rectdim = (
			self.width+self.xoff, self.heightperfunc*len(self.functions)+self.yoff*2)

		y_offset = 0
		for f in self.functions:
			f.y_offset = y_offset
			y_offset += self.heightperfunc

	def activate(self, pos, maptile):
		self.pos = pos 
		self.maptile = maptile
		self.active = True

	def deactivate(self):
		self.pos = None
		self.maptile = None
		self.active = False

	def checkmouse(self, camera, mpos):
		assert(self.active)
		screenpos = camera.game2screen(*self.pos)
		mouse_screenpos = camera.game2screen(*mpos)
		for func in self.functions:
			func.mousehover = False
			rect = Rect(
				(screenpos[0], 
					screenpos[1] + func.y_offset + self.yoff - self.heightperfunc*.05),
				(self.width, self.heightperfunc*.8)
			)
			if (rect.contains_point(mouse_screenpos)):
				func.mousehover = True
				return func.func

		return None

	def draw(self, camera, screen):
		screenpos = camera.game2screen(*self.pos)
		rect = pygame.Rect(screenpos, self.rectdim)
		pygame.draw.rect(screen, black, rect, 3)
		screen.fill(pygame.Color(220, 220, 220), rect)
		for func in self.functions:
			text = func.surface
			if (func.mousehover):
				text = func.highlighted
			screen.blit(text, 
				(screenpos[0]+self.xoff, 
					screenpos[1] + func.y_offset + self.yoff)
			)
			if (func.mousehover):
				pygame.draw.rect(
					screen,
					black,
					Rect(
						(screenpos[0] + self.xoff//2, 
							screenpos[1] + func.y_offset + self.yoff - self.heightperfunc*.05),
						(self.width, self.heightperfunc*.9)
					).get_pyrect(),
					2
				)

	def add_geometry(self, paintindex=None, maptile=None):
		index = -1
		if (paintindex == None):
			print('adding geometry...\ncurrent spritebatch:')
			# print out the spritebatch
			self.spritebatch.print()
			spritename = input('geo sprite (name or num): ')
			try:
				index = int(spritename)
			except:
				index = self.spritebatch.add(spritename)
		else:
			index = paintindex

		spritename = self.spritebatch.get(index).name

		mt = maptile
		if (maptile is None):
			mt = self.maptile

		self.geometry.add_geosprite(spritename, index, mt)

	def remove_geometry(self, maptile=None):
		mt = maptile
		if (maptile is None):
			mt = self.maptile

		self.geometry.remove_geosprite(mt)

	def set_spawn(self):
		self.geometry.set_spawn(*self.maptile)

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
			self.frameswide = data[name]['frameswide']
			self.framestall = data[name]['framestall']

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

	def add(self, spritename):
		result = -1
		for i in range(self.length):
			if spritename == self.sprites[i].name:
				result = i
				self.sprites[i].numloadedmapsusing += 1
		if (result < 0):
			# load the new sprite in
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

		if (fliphorz):
			image = pygame.transform.flip(image, True, False)
			screen.blit(image, rect.get_pyrect())
		else:
			screen.blit(image, rect.get_pyrect())

def main(argv):
	pygame.init()
	Tk().withdraw()

	# Set the width and height of the screen (width, height).
	screendim = (800, 600)#(1050, 750)
	window = pygame.display.set_mode(screendim)
	pygame.display.set_caption("swords")

	done = False
	clock = pygame.time.Clock()

	# cache structure for all sprite flyweights
	spritebatch = SpriteBatch()

	# input stuff
	pygame.joystick.init()

	# input stuff
	prev_input = []
	curr_input = [] # int list
	# may have to make input lists into dicts, with "key" and "mouse" keys
	mouse_pos = None
	inputdata = InputDataBuffer()

	# Load in the test map
	mapname = None
	geometry = None
	if (len(argv) > 0):
		mapname = argv[0]
		geometry = MapData(mapname)
		geometry.load(spritebatch)
	else:
		geometry = newmap(spritebatch)

	camera = Camera(geometry.get_tile2pos(*geometry.spawn), screendim)
	screen = camera.get_camerascreen(window)

	hudbox = HUD_Element(geometry, spritebatch)

	inputmode = InputMode.NORMAL
	paintmodeindex = None

	while not done:
		clock.tick(FPS)

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

		# keypad handle input
		if pygame.K_ESCAPE in curr_input:
			done = True
		if pygame.K_SPACE in curr_input and pygame.K_SPACE not in prev_input:
			pass

		# swap input modes
		if (pygame.K_0 in curr_input and pygame.K_0 not in prev_input and 
			inputmode!=InputMode.NORMAL):
			inputmode = InputMode.NORMAL
			print("switching to normal mode.")

		elif pygame.K_1 in curr_input and pygame.K_1 not in prev_input:
			spritename = ''
			if (inputmode == InputMode.NORMAL):
				inputmode = InputMode.PAINT
				print("switching to geo paint mode.")
				if (paintmodeindex is None):
					print("current spritebatch:")
					spritebatch.print()
					spritename = input('geo sprite (name or num): ')
					try:
						index = int(spritename)
					except:
						index = spritebatch.add(spritename)
					paintmodeindex = index
			elif (inputmode == InputMode.PAINT):
				print('switching geo sprite for painting.')
				print("current spritebatch:")
				spritebatch.print()
				spritename = input('geo sprite (name or num): ')
				try:
					index = int(spritename)
				except:
					index = spritebatch.add(spritename)
				paintmodeindex = index
			print("current geo sprite is <%s>." % spritename)
			print("to switch geo sprites, press 1 again.")

		if (pygame.K_LCTRL in curr_input and 
			pygame.K_s in curr_input and 
			pygame.K_s not in prev_input):
			filename = geometry.save(spritebatch) 
			print('%s saved.' % filename)

		if (pygame.K_LCTRL in curr_input and 
			pygame.K_n in curr_input and 
			pygame.K_n not in prev_input):

			print('Creating new map.')
			filename = input('filename: ')
			width = input('width: ')
			height = input('height: ')
			geometry = MapData(filename, (int(width), int(height)))
			geometry.save()

		# mouse input
		screenmousepos = pygame.mouse.get_pos()
		mouse_pos = camera.screen2cam(*screenmousepos)
		mouse_maptile = None
		# screen coords -> world coords -> tile
		if (not mouse_pos is None):
			x, y = geometry.get_pos2tile(*mouse_pos) 
			mouse_maptile = (x//2, y//2)

		# check input modes
		if (inputmode == InputMode.NORMAL):
			# check for mouse hover on HUD functions
			hudfunc = None
			if (hudbox.active):
				hudfunc = hudbox.checkmouse(camera, mouse_pos)

			if MOUSE_LEFT in curr_input and not MOUSE_LEFT in prev_input:
				if (hudbox.active):
					if (not hudfunc is None):
						hudfunc()
					hudbox.deactivate()

			if MOUSE_MID in curr_input:
				if (not camera.get_mousemoverect().contains_point(screenmousepos)):
					center = camera.get_center()
					delta = (screenmousepos[0]-center[0], screenmousepos[1]-center[1])
					delta = tuple_mult(normalize(delta), MOUSE_MOVE_SPEED_MULT)
					camera.update_pos(v2_add(camera.pos, delta))

			if MOUSE_RIGHT in curr_input and not MOUSE_RIGHT in prev_input:
				hudbox.activate(mouse_pos, mouse_maptile)

		elif (inputmode == InputMode.PAINT):
			if MOUSE_LEFT in curr_input:
				if (geometry.get_geospriteindex(mouse_maptile[0]*2, mouse_maptile[1]*2) == -1):
					hudbox.add_geometry(paintmodeindex, mouse_maptile)
			
			elif MOUSE_RIGHT in curr_input:
				if (geometry.get_geospriteindex(mouse_maptile[0]*2, mouse_maptile[1]*2) > -1):
					hudbox.remove_geometry(mouse_maptile)

			if MOUSE_MID in curr_input:
				if (not camera.get_mousemoverect().contains_point(screenmousepos)):
					center = camera.get_center()
					delta = (screenmousepos[0]-center[0], screenmousepos[1]-center[1])
					delta = tuple_mult(normalize(delta), MOUSE_MOVE_SPEED_MULT)
					camera.update_pos(v2_add(camera.pos, delta))
				

		# start drawing
		screen.fill(grey) # TODO: change this to off-black??

		# get camera maptile range
		camerabounds = camera.get_maptilebounds(geometry)
		camera_minx = max(camerabounds.x-1, 0)
		camera_miny = max(camerabounds.y-1, 0)
		camera_maxx = min(camerabounds.x + camerabounds.width, geometry.width)
		camera_maxy = min(camerabounds.y + camerabounds.height, geometry.height)

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
					spritebatch.draw(screen, si, rect)

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
					spritebatch.draw(screen, si, rect)

		# draw spawn location
		spawnpos = geometry.spawn
		pygame.draw.rect(screen, green, 
			Rect(camera.game2screen(
				*geometry.get_tile2pos(spawnpos[0], spawnpos[1]-1, offset=False)),
				(TILE_WIDTH*2*camera.zoom, TILE_WIDTH*2*camera.zoom)
			).get_pyrect(), 
			3
		)

		# draw outline of selected/hover tile
		if (not mouse_pos is None):
			mpos = mouse_pos
			if (hudbox.active):
				mpos = hudbox.pos
			pygame.draw.rect(screen, black, 
				Rect(camera.game2screen(
					mpos[0] - mpos[0]%(TILE_WIDTH*2), 
					mpos[1] - mpos[1]%(TILE_WIDTH*2)),
					(TILE_WIDTH*2*camera.zoom, TILE_WIDTH*2*camera.zoom)
				).get_pyrect(), 
				1
			)

		if (hudbox.active):
			hudbox.draw(camera, screen)

		pygame.display.flip()


	pygame.quit()

if __name__=='__main__':
	main(sys.argv[1:])