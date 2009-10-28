import weakref
from sys import getrefcount
import string
import pyglet
from pyglet.gl import *
from rect import *

class Visible(object):
    instanceCount = 0

    def __init__(self, p, name, x=0, y=0, w=10, h=10):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.name = name

        self.__parent__ = None
        self.setParent(p)
        
        self.__class__.instanceCount += 1
        
    def __del__(self):
        self.__class__.instanceCount -= 1
        
    def getParent(self):
        if self.__parent__ == None: return None
        return self.__parent__()
    
    def setParent(self, newParent):
        if self.__parent__ != None:
            if self.__parent__() == newParent:
                return
        else:        
            if newParent == None:
                return
                
        if newParent != None:
            newParent.__addChild__(self)
        
        if self.__parent__ != None:
            self.__parent__().__removeChild__(self)
        
        if newParent != None:
            self.__parent__ = weakref.ref(newParent) 
        else:
            self.__parent__ = None
    parent = property(getParent, setParent)
  
    def contains(self, x, y):
        if x >= self.x and y >= self.y and x < self.x + self.w and y < self.y + self.h:
            return True
        else:
            return False
    
    def _getPosition(self): return (self.x, self.y)
    def _setPosition(self, value): self.x, self.y = value
    position = property(_getPosition, _setPosition)

    def _getExtent(self): return (self.w, self.h)
    def _setExtent(self, value): self.w, self.h = value     
    extent = property(_getExtent, _setExtent)

    def draw(self):
        pass

class Rect(Visible):
    instanceCount = 0

    def __init__(self, p, name, x=0, y=0, w=0, h=0, color="#00ff00", opacity=1.0):
        Visible.__init__(self, p, name, x, y, w, h)
        self.color = color
        self.opacity = opacity
        
    def _setColor(self, c):
        self.r, self.g, self.b = self.splitColorChannels(c)
    def _getColor(self):
        return self.mergeColorChannels(self.r, self.g, self.b)
    color = property(_getColor, _setColor)
    
    def splitColorChannels(self, c):
        return (
            string.atoi(c[1:3], 16) / 255.0,
            string.atoi(c[3:5], 16) / 255.0,
            string.atoi(c[5:7], 16) / 255.0
        )

    def mergeColorChannels(self, r,g,b):
        return "#%2.2X%2.2X%2.2X" % (r*255,g*255,b*255)

    def _setCOLORFADE(self, cf):
        self._COLORFADE= cf
        r1, g1, b1 = self.splitColorChannels(self._color_fade_value1)
        r2, g2, b2 = self.splitColorChannels(self._color_fade_value2)

        self.r = int(r1 + float(r2 - r1) * cf)
        self.g = int(g1 + float(g2 - g1) * cf)
        self.b = int(b1 + float(b2 - b1) * cf)
    def _getCOLORFADE(self):
        return self._COLORFADE
    _color_fade = property(_getCOLORFADE, _setCOLORFADE)

    def draw(self):
        #glColor3f(self.r,self.g,self.b)
        pyglet.graphics.draw_indexed(4, pyglet.gl.GL_TRIANGLES,
            [0, 1, 2, 0, 2, 3],
            ('v2i', (self.x, self.y,
                     self.x+self.w, self.y,
                     self.x+self.w, self.y+self.h,
                     self.x, self.y+self.h)),
            ('c4f', (self.r, self.g, self.b, self.opacity)*4)
        )
        
class Text(Rect):
    def __init__(self, p, name, x=0, y=0, w=None, h=0, color="#00ff00", opacity=1.0, text=None):
        Rect.__init__(self, p, name, x, y, w if w != None else 0, h, color, opacity)
        self.text = text if text != None else name
        self.label = pyglet.text.Label(self.text, font_name='Helvetica',
                                    font_size=h,
                                    x=0, y=0)
        if w == None:
            self.w = self.label.content_width
    
    def draw(self):
        glMatrixMode(gl.GL_MODELVIEW)
        glPushMatrix()
        glTranslatef(self.x, self.y + self.h, 0);
        glScalef(float(self.w) / float(self.label.content_width), -1, 1);
        self.label.color = (int(self.r*255), int(self.g*255), int(self.b*255), int(self.opacity*255))
        self.label.draw()
        glPopMatrix()

class ClippingContainer(Visible):
    instanceCount = 0

    def __init__(self, p, name, x=0, y=0, w=10, h=10, ox=0, oy=0, clip=True):
        Visible.__init__(self, p, name, x, y, w, h)
        self.ox = ox
        self.oy = oy
        self.clip = clip

    def _getOffset(self): return (self.ox, self.oy)
    def _setOffset(self, value): self.ox, self.oy = value     
    offset = property(_getOffset, _setOffset)

    def draw(self):
        if self.clip:
            self.drawClipped()
        else:
            self.drawUnclipped()

    def drawUnclipped(self):
        pass

    def drawClipped(self):
        # get screen coordinates of lower left corner
        x = self.x
        y = self.y + self.h

        model_view_matrix = (GLdouble * 16)() 
        projection_matrix = (GLdouble * 16)() 
        viewport = (GLint * 4)() 
        glGetDoublev(GL_MODELVIEW_MATRIX, model_view_matrix)
        glGetDoublev(GL_PROJECTION_MATRIX, projection_matrix)
        glGetIntegerv(GL_VIEWPORT, viewport)
        s_x, s_y, s_z = GLdouble(), GLdouble(), GLdouble()

        gluProject(x, y, 0.0, model_view_matrix, projection_matrix, viewport, s_x, s_y, s_z)

        scissor_was_enabled = glIsEnabled(GL_SCISSOR_TEST)
        
        old_scissor  = (GLint*4)();
        r = ((int(s_x.value), int(s_y.value)), self.extent)
        if scissor_was_enabled:
            glGetIntegerv(GL_SCISSOR_BOX, old_scissor);
            osr = (old_scissor[0:2], old_scissor[2:4])
            r = clip_rect(r, osr)
            
        glScissor(*flatten_rect(r))

        glEnable(GL_SCISSOR_TEST)

        self.drawUnclipped()

        if not scissor_was_enabled:
            glDisable(GL_SCISSOR_TEST)
        else:
            glScissor(old_scissor[0], old_scissor[1], old_scissor[2], old_scissor[3])
                          
class Group(ClippingContainer):
    instanceCount = 0
    
    def __init__(self, p, name, x=0, y=0, w=10, h=10, ox=0, oy=0, clipChildren=True):
        ClippingContainer.__init__(self, p, name, x, y, w, h, ox, oy, clipChildren)     
        self.__children__ = []
        
    def __addChild__(self, c):
        if not c in self.__children__:
            self.__children__.append(c)
    
    def __removeChild__(self, c):
        self.__children__.remove(c)
        
    def __iter__(self):
        return self.__children__.__iter__()
   
    def __len__(self):
        return len(self.__children__)
     
    def drawUnclipped(self):
        glMatrixMode(gl.GL_MODELVIEW)
        glPushMatrix()
        glTranslatef(self.x - self.ox, self.y - self.oy, 0);
        for x in self:
            x.draw()
        glPopMatrix()


class Viewport(ClippingContainer):
    instanceCount = 0

    def __init__(self, p, name, x=0, y=0, w=10, h=10, ox=0, oy=0, world = None):
        ClippingContainer.__init__(self, p, name, x, y, w, h, ox, oy, True)     
        self.world = world 

    def drawUnclipped(self):
        if not self.world: return
        glMatrixMode(gl.GL_MODELVIEW)
        glPushMatrix()
        glTranslatef(self.x - self.ox, self.y - self.oy, 0);
        self.world.draw()
        glPopMatrix()

##
# Regression Tests
##
import unittest
from test import test_support

class TestVisuals(unittest.TestCase):
    # Only use setUp() and tearDown() if necessary

    def setUp(self):
        pass

    def tearDown(self):
        pass
        
    def test_Group(self):
        v = Visible(None, "test1")
        assert(Visible.instanceCount == 1)
        assert(v.parent == None)
        assert(getrefcount(v) == 2)
        del v
        assert(Visible.instanceCount == 0)

        v = Visible(None, "test1")
        assert(Visible.instanceCount == 1)
        assert(v.parent == None)
        assert(getrefcount(v) == 2)

        g = Group(None, "group")
        assert(Group.instanceCount == 1)
        assert(Visible.instanceCount == 1)
        assert(g.parent == None)
        assert(len(g)==0)

        v.parent = g
        assert(getrefcount(v) == 3)
        assert(g.parent == None)
        assert(v.parent == g)
        assert(len(g)==1)
        for x in g: assert(x==v)

        del v
        for x in g: assert(getrefcount(x) == 3)

        assert(Visible.instanceCount == 1)

        for x in g: assert(x.parent==g)

        for x in g: x.parent = None
        del x
        assert(len(g)==0)
        assert(Visible.instanceCount == 0)
        
        g.ox=10
        g.oy=20
        assert(g.offset==(10,20))
        g.offset = (20,40)
        assert(g.ox==20)
        assert(g.oy==40)

    def test_color_properties(self):
        r = Rect(None, "Rect")
        r.color = "#ff7f00"
        assert(r.r==1.0)
        assert(r.g==0x7f/255.0)
        assert(r.b==0)
        r.b = 10/255.0
        assert(r.color == "#FF7F0A")

    def test_basic_properties(self):
        r = Rect(None, "Rect")
        r.x=10
        r.y=20
        assert(r.position==(10,20))
        r.position = (20,40)
        assert(r.x==20)
        assert(r.y==40)
        
        r.w=10
        r.h=20
        assert(r.extent==(10,20))
        r.extent = (20,40)
        assert(r.w==20)
        assert(r.h==40)
        assert(r.contains(20,40)==True)
        assert(r.contains(19,40)==False)
        assert(r.contains(20,39)==False)
        assert(r.contains(20+20,40+40)==False)
        assert(r.contains(20+19,40+39)==True)


def test_main():
    test_support.run_unittest(
        TestVisuals,
        #... list other tests ...
    )
                 
if __name__ == "__main__":
    # run some tests on Node hierarchy
    test_main()
    
    