import pygame
from math import sqrt
from enum import IntEnum
import json

# constants
TILE_WIDTH = 16
MAXINPUTQUEUELEN = 10

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

grey = pygame.Color(200, 200, 200)
lightgrey = pygame.Color(125, 125, 125)
darkred = pygame.Color(80, 0, 0)
lightred = pygame.Color(250, 100, 100)
lightgreen = pygame.Color(100, 250, 100)
lightblue = pygame.Color(100, 100, 250)
red = pygame.Color('red')
black = pygame.Color('black')

class EntityLoader:
	def __init__(self, spritebatch, animationloader):
		fin = open('./data/entitydata.json')
		self.entitydata = json.load(fin)
		fin.close()

		self.spritebatch = spritebatch
		self.animationloader = animationloader

	def create_entity(self, ename, position=(0,0)):
		assert(ename in self.entitydata)

		position = position

		edata = self.entitydata[ename]

		spritedata = edata["spritedata"]
		physicsdata = edata["physicsdata"]
		animationdata = edata["animationdata"]
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

		animator = None
		if (not animationdata is None):
			animatortype = animationdata["type"]
			if (animatortype == "skelly"):
				animator = SkellyAnimator(self.animationloader)
				#animator.scale = pixelheight * TILE_WIDTH / tileheight
			elif (animatortype == "frameby"):
				pass
			else:
				assert(False, "malformed animation data on entity %s" % ename)

			animations = animationdata["animations"]
			for a in animations:
				aindex = self.animationloader.add(self.spritebatch, a, animatortype)
				animator.animations.append(aindex)
				'''
				Each entity can only use animations of the same type as 
				its own single animator. No entity has two animators.
				'''

			defaultanimname = animationdata["default"]
			animator.defaultanimationname = defaultanimname

		player = None
		if (not playerenable is None):
			player = Player()

		entity = Entity(
			position=position, 
			spriteindex=spriteindex, 
			physics=physics, 
			animator=animator,
			player=player)
		return entity

class Entity:
	def __init__(self, position=(0, 0), physics=None, spriteindex=None, animator=None, player=None):
		# common state vars
		self.x, self.y = position
		self.facing_direction = 1 # TODO: encode starting facing dir in spawn_loc on map

		# components
		''' # comment out for animation editor
		self.physics = physics
		self.physics.entity = self
		'''

		self.animator = animator
		if (self.animator is None):
			assert(not spriteindex is None)
			self.animator = StaticAnimator(spriteindex)
		self.animator.entity = self

		'''
		self.player = player
		if (not self.player is None):
			self.player.entity = self
			self.player.loadshit() <- like animator.defaultanimationname
		'''

	def draw(self, camera, sb):
		result = animator.draw(sb, camera, self.facing_direction)
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

class AnimationLoader:
	def __init__(self):
		self.length = 0
		self.animations = []

		fin = open('./data/graphics/skellyanimationdata.json')
		self.skellyanimdata = json.load(fin)
		fin.close()

		fin = open('./data/graphics/framebyanimationdata.json')
		self.framebyanimdata = json.load(fin)
		fin.close()

	def get(self, animindex):
		if (animindex >= self.length):
			return None
		result = self.animations[animindex]
		return result

	def add(self, sb, animname, datatype):
		result = -1
		for i in range(self.length):
			if animname == self.animations[i].name:
				result = i
				self.animations[i].numentitiesusing += 1
		if (result < 0):
			# load the new animation in
			if (datatype == 'skelly'):
				newanimation = Animation(sb, self.skellyanimdata, animname)
			elif (datatype == 'frameby'):
				newanimation = Animation(sb, self.framebyanimdata, animname)
			self.animations.append(newanimation)
			result = self.length
			self.length += 1

		return result

class Animation:
	#def __init__(self, name, numbones, numframes, repeat):
	def __init__(self, sb, data, name):
		self.name = name

		anim = data[name]

		self.numbones = int(anim["numbones"])
		self.numframes = int(anim["numframes"])

		self.repeat = False
		if (not anim["repeat"] is None):
			self.repeat = True

		self.bonesprites = []
		for bsname in anim["bonesprites"]:
			self.bonesprites.append(sb.add(bsname))

		self.bonepos = [][]
		self.bonerot = [][]

		self.numentitiesusing = 0

class SkellyAnimator:
	def __init__(self, animationloader):
		self.entity = None
		self.animationloader = animationloader
		self.animations = []
		self.scale = 1.0
		self.defaultanimationname = ''

		self.nextanimationindexs = []
		self.numnext = 0

		self.load(name)
		self.curranimation = self.get_animation(self.defaultanimationname)

		# draw counter
		self.currframe = 0

	def draw(self, sb, camera, facingdir):
		animation = self.curranimation
		result = []

		indexstart = self.currframe * self.numbones

		epos = (self.entity.x, self.entity.y)

		for bi in range(animation.numbones):
			si = animation.bonesprites[bi]
			pos = animation.bonepos[indexstart + bi]
			rot = animation.bonerot[indexstart + bi]
			pos = v2_add(pos, epos)
			isrot = (pos, rot, self.scale)
			result.append(sb.draw_isrot(si, isrot, fliphorz=fliphorz))

		# increase frame counter, set next animation if needed
		self.currframe += 1
		if (self.currframe >= animation.numframes):
			self.currframe = 0
			if (not animation.repeat):
				if (self.numnext > 0):
					nextanimname = self.nextanimations.pop(0)
					self.curranimation = self.get_animation(nextanimname)
					self.numnext -= 1
				elif (animation.name != self.defaultanimationname):
					self.curranimation = self.get_animation(self.defaultanimationname)

		return result

	def clear_queue(self):
		self.nextanimations.clear()
		self.numnext = 0

	def get_animation(self, animname):
		result = None
		for aindex in self.animations:
			a = self.animationloader.get(aindex)
			if a.name == animname:
				result = a
				break
		return result

	def stop_and_play(self, animname):
		self.clear_queue()
		animation = self.get_animation(animname)
		self.currframe = 0
		self.curranimation = animation

	def queue_next(self, animname):
		self.nextanimations.append(animname)
		self.numnext += 1

	def set_defaultanimation(self, animname):
		self.defaultanimationname = animname

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
	LIGHT_ATK = 3
	HEAVY_ATK = 4
	DODGE = 5
	ACTIVATE = 6
	GUARD = 7

class InputDataBuffer:
	def __init__(self):
		self.maxqueuelength = MAXINPUTQUEUELEN
		self.queuelength = 0

		self.vars = []

		# append in order of input data index enum
		for inputtype in InputDataIndex:
			self.vars.append([])

	def newinput(self, curr_input, prev_input):
		if (self.queuelength == self.maxqueuelength):
			for varlist in self.vars:
				varlist.pop(0)
		else:
			self.queuelength += 1

		# put in default values
		for varlist in self.vars:
			varlist.append(0)

		# movement
		moveinputvecx, moveinputvecy = (0, 0)

		# keyboard directions
		if pygame.K_LEFT in curr_input:
			moveinputvecx += -1
		if pygame.K_RIGHT in curr_input:
			moveinputvecx += 1
		if pygame.K_DOWN in curr_input:
			moveinputvecy += 1
		if pygame.K_UP in curr_input:
			moveinputvecy += -1
		
		# jumping & dodging
		if pygame.K_SPACE in curr_input and not pygame.K_SPACE in prev_input:
			self.set_var(InputDataIndex.JUMP, 1)
		if pygame.K_LSHIFT in curr_input and not pygame.K_LSHIFT in prev_input:
			self.set_var(InputDataIndex.DODGE, 1)

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

	def draw_isrot(self, spriteindex, isrot, fliphorz=False):
		image = self.sprites[spriteindex].get_image()

		pos, scale, degrees = isrot

		# scale image to the rect (already zoomed)
		image = pygame.transform.scale(image, scale)

		# rotate image
		image = pygame.transform.rotate(image, degrees)

		# create rect from new scaled & rotated image
		rect = Rect(pos, image.get_size())

		result = None
		if (fliphorz):
			image = pygame.transform.flip(image, True, False)
			result = (image, rect.get_pyrect())
		else:
			result = (image, rect.get_pyrect())

		return result

### Animation Editor Code ##########################################

def saveanimation():
	# pixelheight = lowest sprite pos-y + image.get_height()
	pass

def add_frame(animation):
	bonepos = [(0, 0)] * animation.numbones
	animation.bonepos.append(bonepos)
	bonerot = [0] * animation.numbones
	animation.bonerot.append(bonerot)
	animation.numframes += 1

####################################################################

def main():
	pygame.init()

	# Set the width and height of the screen (width, height).
	screendim = (800, 600)
	screen = pygame.display.set_mode(screendim)
	pygame.display.set_caption("swords animator")

	done = False
	editmode = True
	clock = pygame.time.Clock()

	# load data
	spritebatch = SpriteBatch()
	animationloader = AnimationLoader()
	entityloader = EntityLoader(spritebatch, animationloader)

	# input stuff
	prev_input = []
	curr_input = [] # int list
	inputdata = InputDataBuffer()

	# load fonts
	font = pygame.font.Font('./data/fonts/ARI.ttf', 32)

	# editor stuff
	current_entity = None

	while not done:

		# poll input, put in curr_input and prev_input
		prev_input = curr_input[:]
		
		for event in pygame.event.get(): # User did something.
			if event.type == pygame.QUIT: # If user clicked close.
				done = True # Flag that we are done so we exit this loop.
			elif event.type == pygame.KEYDOWN:
				curr_input.append(event.key)
			elif event.type == pygame.KEYUP:
				if event.key in curr_input:
					curr_input.remove(event.key)

		# keypad handle input
		if pygame.K_ESCAPE in curr_input:
			done = True

		inputdata.newinput(curr_input, prev_input)

		if (editmode):
			pass
		else: 
			# play mode
			pass


		# start drawing
		screen.fill(grey)

		# draw sprites
		blitlist = []

		# draw entity
		blitlist.append(current_entity.draw(spritebatch))
		screen.blits(blitlist)
		blitlist.clear()
		
		# display screen
		pygame.display.flip()

	pygame.quit()

if __name__=='__main__':
	main()