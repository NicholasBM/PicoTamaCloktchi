import framebuf
from machine import Pin, Timer
from time import sleep
from os import listdir
import gc

class Icon():
    """ Models an icon and all the properties it requires """
    image = None # the image data type buf
    x = 0
    y = 0
    __invert = False
    width = 16
    height = 16
    name = "Empty"

    def __init__(self, filename:None, width=None, height=None, x=None, y=None, name=None):
        """ Sets up the default values """
        if width: 
            self.width = width
        if height: 
            self.height = height
        if name: 
            self.name = name
        if x: 
            self.x = x
        if y: 
            self.y = y
        if filename is not None: 
            self.image = self.loadicons(filename)
    
    @property
    def invert(self)->bool:
        """ Flips the bits in the image so white become black etc and returns the image """
        print("Invert is", self.__invert)
        return self.__invert

    @invert.setter
    def invert(self, value:bool):
        """ Inverts the icon colour """
        
        image = self.image
        for x in range(0,self.width):
            for y in range(0, self.height):
                pxl = image.pixel(x,y)
                if pxl == 0:
                    image.pixel(x,y,1)
                else:
                    image.pixel(x,y,0)
                
        self.image = image
        self.__invert = value
        # print("Invert is", self.__invert)

    def loadicons(self, file):
        # print(file)
        with open(file, 'rb') as f:
            f.readline() # magic number
            f.readline() # creator comment
            f.readline() # dimensions
            data = bytearray(f.read())
        frame_buffer = framebuf.FrameBuffer(data, self.width,self.height, framebuf.MONO_HLSB)
        print(self.name, self.width, self.height)
        return frame_buffer

    def loadicon2(self, library, icon_data):
        __import__(library, icon_data)
        # frame_buffer = framebuf.FrameBuffer(name, self.width,self.height, framebuf.MONO_HLSB)
        # frame_buffer = bytearray(self.width * self.height // 8)
        frame_buffer = bytearray(icon_data)
        return frame_buffer
        

class Toolbar():
    """ Models the toolbar """
    __icon_array = []
    __framebuf = framebuf.FrameBuffer(bytearray(160*64*1), 160, 16, framebuf.MONO_HLSB)
    spacer = 1
    __selected_item = None
    __selected_index = -1 # -1 means no item selected
  
    def __init__(self):
        # print("building toolbar")
        self.__framebuf = framebuf.FrameBuffer(bytearray(160*64*8), 160, 16, framebuf.MONO_HLSB)

    def additem(self, icon):
        self.__icon_array.append(icon)

    def remove(self, icon):
        self.__icon_array.remove(icon)

    @property
    def data(self):
        """ Returns the toolbar array as a buffer"""
        x = 0
        count = 0
        for icon in self.__icon_array:
            # print("x:",x)
            count += 1
            if type(icon) is Icon: # check if the icon is a static icon
                self.__framebuf.blit(icon.image, x, 0) 
            if type(icon) is Animate: # check if the icon is an animated icon
                if icon.__frames and len(icon.__frames) > 0 and icon.__current_frame < len(icon.__frames):
                    self.__framebuf.blit(icon.__frames[icon.__current_frame].image, x, 0)
            fb = self.__framebuf
            x += icon.width + self.spacer
        return fb

    def show(self, display):
        if self.data is None:
            print(f"Data is None")
            raise ValueError
#         display.set_framebuffer(self.data)
        
        display.blit(self.data, 0,0)
        # oled.show()
    
    def select(self, index, oled):
        """ Set the item in the index to inverted """
        # for item in self.__icon_array:
        #     item.invert = False
        if 0 <= index < len(self.__icon_array):
            self.__icon_array[index].invert = True
            self.__selected_index = index
            self.show(oled)
        else:
            print(f"Invalid index: {index}, array length: {len(self.__icon_array)}")

    def unselect(self, index, oled):
        if 0 <= index < len(self.__icon_array):
            self.__icon_array[index].invert = False
            self.__selected_index = -1
            self.show(oled)
        else:
            print(f"Invalid index: {index}, array length: {len(self.__icon_array)}")

    @property
    def selected_item(self):
        """ Returns the name of the currently selected icon """
        if 0 <= self.__selected_index < len(self.__icon_array):
            self.__selected_item = self.__icon_array[self.__selected_index].name
            return self.__selected_item
        else:
            return None

class Animate():
    __frames = []
    __current_frame = 0
    __speed = "normal" # Other speeds are 'fast' and 'slow' - it just adds frames or skips frames
    __speed_value = 0
    __done = False # Has the animation completed
    __loop_count = 0
    __bouncing = False
    __animation_type = "default"
    __pause = 0
    __set = False
    __x = 0
    __y = 0
    __width = 16
    __height = 16
    __cached = False
    filename = None
    """ other animations types: 
        - loop
        - bounce
        - reverse
    """
    @property
    def set(self)->bool:
        return self.__set

    @set.setter
    def set(self, value:bool):
        self.__set = value
        if value: # if value is True
            self.load()
        else:
            self.unload()
            
    @property
    def speed(self):
        """ Returns the current speed """
        return self.__speed

    @speed.setter
    def speed(self, value:str):
        if value in ['very slow','slow','normal','fast']:
            self.__speed = value
            if value == 'very slow':
                self.__pause = 10
                self.__speed_value = 10
            if value == 'slow':
                self.__pause = 1
                self.__speed_value = 1
            if value == "normal":
                self.__pause = 0
                self.__speed_value = 0
        else:
            print(value, "is not a valid value, try 'fast','normal' or 'slow'")

    @property
    def animation_type(self):
        return self.__animation_type

    @animation_type.setter
    def animation_type(self, value):
        if value in ['default','loop','bounce','reverse']:
            self.__animation_type = value
        else:
            print(value," is not a valid Animation type - it should be 'loop','bounce','reverse' or 'default'")

    def __init__(self, frames=None, animation_type:str=None,x:int=None,y:int=None, width:int=None, height:int=None, filename=None):
       """ setup the animation """ 
       print(f"initialising animation: {filename}")
       if x:
           self.__x = x
       if y:
           self.__y = y
       if width:
           self.__width = width
       if height:
           self.__height = height  
       self.__current_frame = 0
       if frames is not None:
        self.__frames = frames
       self.__done = False
       self.__loop_count = 1
       if animation_type is not None:
            self.animation_type = animation_type
       if filename:
           self.filename = filename 

    def forward(self):
        """ progress the current frame """
        if self.__speed == 'normal':
            self.__current_frame +=1

        if self.__speed in ['very slow','slow']:
            if self.__pause > 0:
                self.__pause -= 1
            else:
                self.__current_frame +=1
                self.__pause = self.__speed_value

        if self.__speed == 'fast':
            if self.__current_frame < self.frame_count +2:
                self.__current_frame +=2
            else:
                self.__current_frame +=1

    def reverse(self):
        if self.__speed == 'normal':
            self.__current_frame -=1

        if self.__speed in ['very slow','slow']:
            if self.__pause > 0:
                self.__pause -= 1
            else:
                self.__current_frame -=1                
                self.__pause = self.__speed_value

        if self.__speed == 'fast':
            if self.__current_frame < self.frame_count +2:
                self.__current_frame -=2
            else:
                self.__current_frame -=1
    
    def load(self):
        """ load the animation files """

        # load the files from disk
        if not self.__cached:
            try:
                # Check if filename contains a directory path
                if '/' in self.filename:
                    # Extract directory and base filename
                    directory = '/'.join(self.filename.split('/')[:-1])
                    base_filename = self.filename.split('/')[-1]
                    
                    # Look in the specified directory
                    print(f"Looking for animation files in {directory}")
                    try:
                        files = listdir(directory)
                        array = []
                        
                        for file in files:
                            if (file.startswith(base_filename)) and (file.endswith('.pbm')):
                                full_path = f"{directory}/{file}"
                                print(f"Loading animation frame: {full_path}")
                                array.append(Icon(filename=full_path, width=self.__width, height=self.__height, x=self.__x, y=self.__y, name=file))
                    except:
                        print(f"Error accessing directory {directory}")
                        array = []
                else:
                    # First try to look in gui/bitmaps directory
                    bitmap_dir = "gui/bitmaps"
                    print(f"Looking for animation files in {bitmap_dir}")
                    files = listdir(bitmap_dir)
                    array = []
                    base_filename = self.filename
                    
                    for file in files:
                        if (file.startswith(base_filename)) and (file.endswith('.pbm')):
                            full_path = f"{bitmap_dir}/{file}"
                            print(f"Loading animation frame: {full_path}")
                            array.append(Icon(filename=full_path, width=self.__width, height=self.__height, x=self.__x, y=self.__y, name=file))
                
                # If no files found in specified directory, try current directory
                if not array:
                    print(f"No animation frames found for {self.filename}, trying current directory")
                    files = listdir()
                    for file in files:
                        if (file.startswith(base_filename)) and (file.endswith('.pbm')):
                            print(f"Loading animation frame: {file}")
                            array.append(Icon(filename=file, width=self.__width, height=self.__height, x=self.__x, y=self.__y, name=file))
                
                if array:
                    self.__frames = array
                    self.__cached = True
                    print(f"Loaded {len(array)} animation frames")
                else:
                    print(f"WARNING: No animation frames found for {self.filename}")
                    # Create a dummy frame to prevent crashes
                    dummy_data = bytearray(self.__width * self.__height // 8)
                    dummy_buffer = framebuf.FrameBuffer(dummy_data, self.__width, self.__height, framebuf.MONO_HLSB)
                    dummy_icon = Icon(None, width=self.__width, height=self.__height, x=self.__x, y=self.__y, name="dummy")
                    dummy_icon.image = dummy_buffer
                    self.__frames = [dummy_icon]
                    self.__cached = True
                    print("Created dummy frame to prevent crashes")
            except Exception as e:
                print(f"Error loading animation frames: {e}")
                # Create a dummy frame to prevent crashes
                dummy_data = bytearray(self.__width * self.__height // 8)
                dummy_buffer = framebuf.FrameBuffer(dummy_data, self.__width, self.__height, framebuf.MONO_HLSB)
                dummy_icon = Icon(None, width=self.__width, height=self.__height, x=self.__x, y=self.__y, name="dummy")
                dummy_icon.image = dummy_buffer
                self.__frames = [dummy_icon]
                self.__cached = True
                print("Created dummy frame to prevent crashes")

    def unload(self):
        """ free up memory """

        self.__frames = None
        self.__cached = False
        gc.collect()

    def animate(self, oled):
        """ Animates the frames based on the animation type and for the number of times specified """

        # Safety check to prevent index errors
        if not self.__frames or len(self.__frames) == 0:
            print("No frames to animate")
            return
        
        # Ensure current_frame is within bounds
        if self.__current_frame >= len(self.__frames):
            print(f"Frame index out of range: {self.__current_frame} >= {len(self.__frames)}")
            self.__current_frame = 0
        
        current_frame = self.__current_frame # Current Frame number - used to index the frames array
        frame = self.__frames[current_frame]        
        oled.blit(frame.image, frame.x, frame.y)
       
        if self.__animation_type == "loop":
            # Loop from the first frame to the last, for the number of cycles specificed, and then set done to True
            self.forward()
           
            if self.__current_frame > self.frame_count:
                self.__current_frame = 0
                self.__loop_count -= 1
                if self.__loop_count == 0:
                    self.__done = True
            
        if self.__animation_type == "bouncing":
           
            # Loop from the first frame to the last, and then back to the first again, then set done to True
            if self.__bouncing:
                # We're in the reverse phase (going from last frame back to first)
                self.reverse()  # Always move backward in this phase
                
                # If we've reached the first frame, switch direction
                if self.__current_frame == 0:
                    self.__bouncing = False  # Switch to forward phase
                    
                    # Check if we should continue or end
                    if self.__loop_count == 0:
                        self.__done = True  # Animation complete
                    elif self.__loop_count > 0:
                        self.__loop_count -= 1  # Decrement loop counter
                        self.forward()  # Start moving forward again
                    elif self.__loop_count == -1:
                        # Bounce infinitely
                        self.forward()  # Start moving forward again
            else:
                # We're in the forward phase (going from first frame to last)
                if self.__current_frame == 0:
                    # At the first frame
                    if self.__loop_count == 0:
                        self.__done = True  # Animation complete
                    elif self.__loop_count == -1:
                        # Bounce infinitely
                        self.forward()  # Move to next frame
                    else:
                        self.forward()  # Move to next frame
                elif self.__current_frame >= self.frame_count:
                    # Reached the last frame, switch direction
                    self.__bouncing = True  # Switch to reverse phase
                    self.reverse()  # Start moving backward
                else:
                    # In the middle of the sequence, keep moving forward
                    self.forward()
            
        if self.__animation_type == "default":
            # loop through from first frame to last, then set done to True
            
            if self.__current_frame == self.frame_count:
                self.__current_frame = 0
                self.__done = True
            else:
                self.forward()
   
    @property
    def frame_count(self):
        """ Returns the total number of frames in the animation """
        if not self.__frames:
            return 0
        return len(self.__frames)-1
    
    @property
    def done(self):
        """ Has the animation completed """
        if self.__done:
            self.__done = False # reset the done flag to false
            return True
        else:
            return False

    def loop(self, no:int=None):
        """ Loops the animation
        if no is None or -1 the animation will continue looping until animate.stop() is called """

        if no is not None:
            self.__loop_count = no
        else:
            self.__loop_count = -1
        self.__animation_type = "loop"

    def stop(self):
        self.__loop_count = 0
        self.__bouncing = False
        self.__done = True

    def bounce(self, no:int=None):
        """ Loops the animation forward, then backward, the number of time specified in no,
         if there is no number provided it will animate infinately """

        self.__animation_type = "bouncing"
        if no is not None:
            self.__loop_count = no
        else:
            self.__loop_count = -1

    @property
    def width(self):
        """ Gets the icon width """
        return self.__width
    
    @width.setter
    def width(self, value):
        """ Sets the icon width """
        self.__width = value
    
    @property
    def height(self):
        """ Gets the icon height """
        return self.__width
    
    @height.setter
    def height(self, value):
        """ Sets the icon height """
        self.__height = value

    def __str__(self):
        message = f"Animate: {self.filename}, {self.__current_frame}, {self.__loop_count}, {self.__done}, x: {self.__x}, y: {self.__y}"
        return message

class Button():
    """ Models a button, check the status with is_pressed """

    # The private variables
    __pressed = False
    __pin = 0
    __button_down = False

    def __init__(self, pin:int):
        """ Sets up the button """

        self.__pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.__pressed = False

    @property
    def is_pressed(self)->bool:
        """ Returns the current state of the button """

        if self.__pin.value() == 0:
            self.__button_down = True
            print("button pressed")
            return True
        if self.__pin.value() == 1:
            self.__button_down = False
            return False
            # if not self.__button_down:
                
            #     self.__button_down = False
            #     return True
            # else:
            #     return False

class Event():
    """ Models events that can happen, with timers and pop up messages """
    name = ""
    value = 0
    sprite = None
    timer = -1 # -1 means no timer set
    timer_ms = 0
    __callback = None
    message = ""
    done = False
    _timer_instance = None # holds the timer instance

    def __init__(self, name=None, sprite=None, value=None, callback=None):
        """ Create a new event """

        if name:
            self.name = name
        if sprite:
            self.sprite = sprite
        if value:
            self.value = value
        if callback is not None:
            self.__callback = callback
    
    def popup(self, display):
        # display popup window
        # show sprite
        # show message

        fbuf = framebuf.FrameBuffer(bytearray(128 * 48 * 1), 128, 48, framebuf.MONO_HLSB)
        fbuf.rect(0,0,128,48, 1)
        fbuf.blit(self.sprite.image, 5, 10)
        
        # Split message into multiple lines if it's too long
        # With the icon at x=5 and text starting at x=32, we have about 12 characters per line
        # (128 - 32) / 8 = 12 characters
        max_chars_per_line = 12
        
        if len(self.message) > max_chars_per_line:
            # Find a good split point (space) near the middle
            split_point = max_chars_per_line
            while split_point > 0 and self.message[split_point-1] != ' ':
                split_point -= 1
            
            # If no space found, just split at max_chars_per_line
            if split_point == 0:
                split_point = max_chars_per_line
            
            # Split the message into two lines
            line1 = self.message[:split_point].strip()
            line2 = self.message[split_point:].strip()
            
            # Display both lines
            fbuf.text(line1, 32, 12)  # First line a bit higher
            fbuf.text(line2, 32, 24)  # Second line a bit lower
        else:
            # Display single line (centered vertically)
            fbuf.text(self.message, 32, 18)
        
        display.blit(fbuf,0,16)
        display.show()
        sleep(3)  # Changed from 2 to 3 seconds
    
    def tick(self):
        """ Progresses the animation on frame """

        self.timer_ms += 1
        if self.timer_ms >= self.timer:
            if self.__callback is not None:
                print("poop check callback")
                self.__callback
                self.timer = -1
                self.timer_ms = 0
            else:
                # print("Timer Alert!")
                self.done = True
    def reset(self):
        self.done = False
        
    def start(self, duration):
        """ Start a timer that will run a callback routine when complete """
#         print(f"Starting Timer for {duration/1000} seconds")
        self.done = False

        if self._timer_instance:
            self._timer_instance.deinit()  # Stop any previous timer
        
        self._timer_instance = Timer(-1)  # Create a one-shot timer
        self._timer_instance.init(period=duration, mode=Timer.ONE_SHOT, callback=self._timer_callback)

    def _timer_callback(self, t):
        """ Internal method to handle the timer callback """
        if self.__callback:
#             print("Timer completed, executing callback.")
            self.__callback()
#         else:
#             print("Timer complete, but no callback")
        self.done = True
#         self.timer = -1

class GameState():
    states = {}
    
    def __init__(self):
        pass
    
    def __str__(self):
        """ shows the current game state """
        message = "Game State: "
#         for state in self.states:
#             message += ", ".join(f"{key}: {value}" for key, value in self.states.items())
        message += ", ".join(f"{key}: {value}" for key, value in self.states.items())
        message += "."
        return message
