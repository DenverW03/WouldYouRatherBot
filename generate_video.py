from moviepy.video.VideoClip import ImageClip, TextClip
from moviepy.editor import CompositeVideoClip
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
    image_path = "resources/background.png"
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
        final_clip = CompositeVideoClip([self.clip, upper_clip, lower_clip, upper_clip_text.crossfadein(self.animation_duration).crossfadeout(self.animation_duration).set_start(self.text_start), lower_clip_text.crossfadein(self.animation_duration).crossfadeout(self.animation_duration).set_start(self.text_start)]).set_fps(30)

        # Saving the final clip
        final_clip.write_videofile("out/test.mp4", fps=30)

    # Creates a text clip and returns it
    # y_offset (int) = the position on screen, to place with upper or lower choice
    # text (str) = the text to add
    def add_text(self, y_offset, text):
        # Creating the text clip
        text_clip = TextClip(text, fontsize=100, color='white', font='Arial Black', stroke_color='black', stroke_width=4)
        text_clip = text_clip.set_position(('center', y_offset)).set_duration(self.duration - self.text_start)
        return text_clip

    # Adds an image and animates int
    # y_offset (int) = the y offset on the screen, to dictate whether upper or lower
    # side (bool) = the side the entrance animation starts from, true = left, false = right
    # image (str) = a str containing the path to the image
    def add_image(self, y_offset, side, image):
        image = ImageClip(image, duration=self.duration)

        # Animation functions used as parameters
        def translate_clip(t, clip):
            x = (1080 / 2) - (clip.h / 2) # clip.h represents with here for some reason, cba figuring it out

            # Exit translation animation
            if t >= self.duration - self.image_exit_offset:
                if not side: # right
                    # Because this entered on the right it should leave on the left
                    offscreen_x = -self.max_dimension
                    current_x = x + (offscreen_x - x) * min(1, (t - (self.duration - self.image_exit_offset)) / self.animation_duration)
                else: # left
                    # Entered on the left so leave on the right
                    offscreen_x = 1080
                    current_x = x - (x - offscreen_x) * min(1, (t - (self.duration - self.image_exit_offset)) / self.animation_duration)

                return current_x, y_offset


            if not side: # right
                offscreen_x = -self.max_dimension
                current_x = offscreen_x + (x - offscreen_x) * min(1, t / self.animation_duration)
            else: # left
                offscreen_x = 1080
                current_x = offscreen_x - (offscreen_x - x) * min(1, t / self.animation_duration)

            return current_x, y_offset

        # Frame rotation function with rotation angle based resizing
        def rotate_frame(gf, t):
            # Getting the frame at the time step
            frame = gf(t)

            # Safely getting the height and width dimensions
            if frame.ndim == 2:
                height, width = frame.shape
            else:
                height, width, _ = frame.shape

            # Calculating the scaling multiplier
            largest_dimension = width if width > height else height
            scale_mult = self.max_dimension / largest_dimension

            # Resizing to the intended standard dimensions (max size on largest dimension)
            width = int(width * scale_mult)
            height = int(height * scale_mult)

            # Calculating the current angle of rotation at time step
            start_angle = 90
            end_angle = 0
            current_angle = start_angle + (end_angle - start_angle) * min(1, t / self.animation_duration)
            current_angle_rad = current_angle * (np.pi / 180)

            # Calculating the new bounding box of the rotated image
            new_width = int(abs(width * np.cos(current_angle_rad)) + abs(height * np.sin(current_angle_rad)))
            new_height = int(abs(width * np.sin(current_angle_rad)) + abs(height * np.cos(current_angle_rad)))

            # Applying the rotation and resize
            image = Image.fromarray(frame)
            rotated_image = image.rotate(current_angle, expand=True)
            resized_image = rotated_image.resize((new_width, new_height))

            return np.array(resized_image)

        # Adding the animations
        image = image.add_mask()
        image = image.fl(rotate_frame, apply_to='mask')
        image = image.set_position(lambda t: translate_clip(t, image)).set_duration(self.duration)

        # Returning the composite clip
        return image

    # This function calculates the resize multiplier for a clip
    def calc_resize_mult(self, clip):
        # Calculating scaling dimension used from clip
        largest_dimension = clip.w if clip.w > clip.h else clip.h

        # Calculating the downsize multiplier
        size_mult = self.max_dimension / largest_dimension

        # Applying the resize
        return size_mult
