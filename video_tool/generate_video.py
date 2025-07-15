from moviepy import *
import numpy as np
from PIL import Image

class video_builder:
    # Settings class variables
    duration = 10
    animation_duration = 0.3
    image_exit_offset = 0.6 # How long before the end of the video (duration) should the image exit animations play
    spin_animation_offset = 0.3
    text_start = 1 # How long before the text starts to fade in
    max_dimension = 500
    upper_offset = ((1920 / 2) - max_dimension) / 2
    lower_offset = (1920 - upper_offset) - max_dimension
    upper_offset_text = (1920 / 2) - 200
    lower_offset_text = (1920 / 2) + 40

    # General class variables
    image_path = "resources/background.jpg"
    clip = ImageClip(image_path, duration=duration)

    # Constructor, sets the text strings
    # upper_text (str) = the text for the upper choice
    # lower_text (str) = the text for the lower choice
    def __init__(self, upper_text, lower_text, upper_image, lower_image):
        self.upper_text = upper_text
        self.lower_text = lower_text
        self.upper_image = upper_image
        self.lower_image = lower_image

    # Function to build the video
    def build(self):
        # Getting composite clips for each piece
        upper_clip = self.add_image(self.upper_offset, False, self.upper_image)
        lower_clip = self.add_image(self.lower_offset, True, self.lower_image)

        # Creating the text clips
        upper_clip_text = self.add_text(self.upper_offset_text, self.upper_text)
        lower_clip_text = self.add_text(self.lower_offset_text, self.lower_text)

        # Piecing the composite clips together
        final_clip = CompositeVideoClip([self.clip, upper_clip, lower_clip, upper_clip_text.with_start(self.text_start), lower_clip_text.with_start(self.text_start)]).with_fps(30)

        # Saving the final clip
        final_clip.write_videofile("out/test.mp4", fps=30)

    # Creates a text clip and returns it
    # y_offset (int) = the position on screen, to place with upper or lower choice
    # text (str) = the text to add
    def add_text(self, y_offset, text):
        # Creating the text clip
        text_clip = TextClip(text=text, size=(1080, round(1920/20)), font_size=100, color='white', font='Arial Black', stroke_color='black', stroke_width=4)
        text_clip = text_clip.with_position(('center', y_offset)).with_duration(self.duration - self.text_start)
        return text_clip

    # Adds an image and animates it
    # y_offset (int) = the y offset on the screen, to dictate whether upper or lower
    # side (bool) = the side the entrance animation starts from, true = left, false = right
    # image_path (str) = a str containing the path to the image
    def add_image(self, y_offset, side, image_path):
        # Load the image
        image = ImageClip(image_path, duration=self.duration)
        
        # Resize the image to fit max_dimension
        image = image.resized(self.calc_resize_mult(image))
        
        # Create the rotation and translation transformation
        def rotate_and_translate(get_frame, t):
            frame = get_frame(t)
            
            # Calculate rotation angle
            start_angle = 90
            end_angle = 0
            current_angle = start_angle + (end_angle - start_angle) * min(1, t / self.animation_duration)
            
            # Apply rotation
            image_pil = Image.fromarray(frame)

            # Converting to RGBA and masking with a second image without alpha layer removes PIL rotate&expand background
            im2 = image_pil.convert('RGBA')
            rotated_image = im2.rotate(current_angle, expand=True)
            fff = Image.new('RGBA', rotated_image.size, (255, 255, 255, 0)) # No alpha layer image to combine regular image with
            out = Image.composite(rotated_image, fff, rotated_image)

            return np.array(out)
        
        # Apply the rotation transformation
        image = image.transform(rotate_and_translate)
        
        # Create position animation function
        def get_position(t):
            x = (1080 / 2) - (image.w / 2)
            
            # Exit translation animation
            if t >= self.duration - self.image_exit_offset:
                if not side:  # right
                    offscreen_x = -self.max_dimension
                    current_x = x + (offscreen_x - x) * min(1, (t - (self.duration - self.image_exit_offset)) / self.animation_duration)
                else:  # left
                    offscreen_x = 1080
                    current_x = x - (x - offscreen_x) * min(1, (t - (self.duration - self.image_exit_offset)) / self.animation_duration)
                return current_x, y_offset
            
            # Entrance animation
            if not side:  # right
                offscreen_x = -self.max_dimension
                current_x = offscreen_x + (x - offscreen_x) * min(1, t / self.animation_duration)
            else:  # left
                offscreen_x = 1080
                current_x = offscreen_x - (offscreen_x - x) * min(1, t / self.animation_duration)
            
            return current_x, y_offset
        
        # Apply position animation
        image = image.with_position(get_position).with_duration(self.duration)
        
        return image

    # This function calculates the resize multiplier for a clip
    def calc_resize_mult(self, clip):
        # Calculating scaling dimension used from clip
        largest_dimension = clip.w if clip.w > clip.h else clip.h

        # Calculating the downsize multiplier
        size_mult = self.max_dimension / largest_dimension

        # Applying the resize
        return size_mult
