import pygame
from math import sqrt
from enum import IntEnum
from tkinter import Tk 
from tkinter.filedialog import askopenfilename

# constants
TILE_WIDTH = 16
FPS = 60
MAXINPUTQUEUELEN = 10

# input codes
MOUSE_LEFT = 1
MOUSE_MID = 2
MOUSE_RIGHT = 3

# camera
ZOOM_MULT = 2.0
CAMERA_WIDTH = 1050
CAMERA_HEIGHT = 750
MOUSE_MOVE_BORDER_MULT = .8
MOUSE_MOVE_SPEED_MULT = 1.7

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
		self.zoom = self.width / CAMERA_WIDTH * ZOOM_MULT

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

	def get_camerascreen(self, window):
		result = window.subsurface(
			pygame.Rect(
				(self.x_offset, self.y_offset),
				(self.width, self.height)
			)
		)
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

class MapData:
	def __init__(self, filename, dim=(0, 0)):
		self.filename = filename

		self.width = dim[0]*2
		self.height = dim[1]*2
		self.geo = [False] * (self.width * self.height)
		self.spawn = (0, 0) # bottom left!! of spawn loc

		self.newmap()

	def newmap(self):
		xs = [0, self.width//2-1]
		ys = [0, self.height//2-1]

		for j in range(self.height//2):
			for i in range(self.width//2):
				if (i in xs or j in ys):
					x, y = i*2, j*2					
					self.set_geoon(x, y)
					self.set_geoon(x+1, y)
					self.set_geoon(x, y+1)
					self.set_geoon(x+1, y+1)

		self.spawn = (2, self.height-3)

	def get_geo(self, x, y):
		result = self.geo[x + self.width * y]
		return result

	def set_geoon(self, x, y):
		self.geo[x + self.width * y] = True

	def set_geooff(self, x, y):
		self.geo[x + self.width * y] = False

	def maptile_add(self, mtx, mty):
		if (mtx > 0 and mtx < self.width//2-1 and mty > 0 and mty < self.height//2-1):
			x, y = mtx*2, mty*2
			if (not self.get_geo(x, y)):
				self.set_geoon(x, y)
				self.set_geoon(x+1, y)
				self.set_geoon(x, y+1)
				self.set_geoon(x+1, y+1)

	def maptile_remove(self, mtx, mty):
		if (mtx > 0 and mtx < self.width//2-1 and mty > 0 and mty < self.height//2-1):
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
		fileoutput.append('%d,%d\n' % (self.width//2, self.height//2))

		# walls(#), spaces( ) or spawn(@)
		for j in range(self.height//2):
			line = []
			for i in range(self.width//2):
				geo = self.get_geo(i*2, j*2)
				if (geo):
					line.append('#')
				elif ((i*2, j*2+1) == self.spawn):
					line.append('@')
				else:
					line.append(' ')
			fileoutput.append(''.join(line) + '\n')

		# open file, write fileoutput to it
		# strip the last '\n' from the fileoutput before writing
		fileoutput[-1] = fileoutput[-1][:-1]
		# write out file
		filename = './data/%s.txt' % self.filename
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

class HUD_Element:
	def __init__(self, geometry):
		self.active = False
		self.pos = None
		self.maptile = None

		self.geometry = geometry

		self.functions = []
		self.functions.append(HUD_Function('add geometry', self.add_geometry))
		self.functions.append(HUD_Function('remove geometry', self.remove_geometry))

		self.xoff = 10
		self.yoff = 10
		self.width = 160
		self.heightperfunc = 24

		self.rectdim = (self.width+self.xoff, self.heightperfunc*len(self.functions)+self.yoff*2)

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

	def add_geometry(self):
		self.geometry.maptile_add(*self.maptile)

	def remove_geometry(self):
		self.geometry.maptile_remove(*self.maptile)

def main():
	pygame.init()
	Tk().withdraw()

	# Set the width and height of the screen (width, height).
	screendim = (800, 750)#(1050, 750)
	window = pygame.display.set_mode(screendim)
	pygame.display.set_caption("swords")

	done = False
	clock = pygame.time.Clock()

	# input stuff
	pygame.joystick.init()

	# input stuff
	prev_input = []
	curr_input = [] # int list
	# may have to make input lists into dicts, with "key" and "mouse" keys
	mouse_pos = None
	inputdata = InputDataBuffer()

	# Load in the test map
	geometry = MapData('map2')
	geometry.load()

	camera = Camera(geometry.get_tile2pos(*geometry.spawn), screendim)
	screen = camera.get_camerascreen(window)

	hudbox = HUD_Element(geometry)

	inputmode = InputMode.NORMAL
	paintmodefile = None

	while not done:
		clock.tick(FPS)

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

		# keypad handle input
		if pygame.K_ESCAPE in curr_input:
			done = True
		if pygame.K_SPACE in curr_input and pygame.K_SPACE not in prev_input:
			pass

		# swap input modes
		if (pygame.K_0 in curr_input and pygame.K_0 not in prev_input and 
			inputmode==InputMode.PAINT):
			inputmode = InputMode.NORMAL
			print("switching to normal mode.")
		elif pygame.K_1 in curr_input and pygame.K_1 not in prev_input:
			if (inputmode == InputMode.NORMAL):
				inputmode = InputMode.PAINT
				print("switching to paint mode.")
				if (paintmodefile is None):
					sobjfilename = askopenfilename().split("/")
					if ('res' in sobjfilename):
						# assumes only one "res" folder in the path
						resindex = sobjfilename.index('res')
						paintmodefile = './' + '/'.join(sobjfilename[resindex:])
						print('paint object changed to %s' % paintmodefile)
				else:
					print("to switch objects, press 1 again.")
			elif (inputmode == InputMode.PAINT):
				sobjfilename = askopenfilename().split("/")
				if ('res' in sobjfilename):
					# assumes only one "res" folder in the path
					resindex = sobjfilename.index('res') 
					paintmodefile = './' + '/'.join(sobjfilename[resindex:])
					print('paint object changed to %s' % paintmodefile)

		if (pygame.K_LCTRL in curr_input and 
			pygame.K_s in curr_input and 
			pygame.K_s not in prev_input):
			filename = geometry.save()
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
				geometry.maptile_add(*mouse_maptile)
			elif MOUSE_RIGHT in curr_input:
				geometry.maptile_remove(*mouse_maptile)
				

		# start drawing
		screen.fill(grey)

		for line in output:
			if (not line is None):
				print(line)

		for j in range(geometry.height):
			for i in range(geometry.width):
				if geometry.get_geo(i, j):
					pos = camera.game2screen(*geometry.get_tile2pos(i, j, offset=False))
					pygame.draw.rect(screen, lightgrey, 
						pygame.Rect(pos, (TILE_WIDTH*camera.zoom+1, TILE_WIDTH*camera.zoom+1)))		

		
		if (not mouse_pos is None):
			mpos = mouse_pos
			if (hudbox.active):
				mpos = hudbox.pos
			pygame.draw.rect(screen, black, 
				Rect(camera.game2screen(
					mpos[0] - mpos[0]%(TILE_WIDTH*2), 
					mpos[1] - mpos[1]%(TILE_WIDTH*2)),
					(TILE_WIDTH*2*camera.zoom+1, TILE_WIDTH*2*camera.zoom+1)
				).get_pyrect(), 
				1
			)

		if (hudbox.active):
			hudbox.draw(camera, screen)

		pygame.display.flip()


	pygame.quit()

if __name__=='__main__':
	main()