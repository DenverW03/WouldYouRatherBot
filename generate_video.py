import moviepy.editor
from moviepy.video.VideoClip import ImageClip, np
from moviepy.editor import CompositeVideoClip
import moviepy.video.fx.all
import numpy as np

class video_builder:
    # Settings class variables
    duration = 10
    animation_duration = 0.5
    max_dimension = 500
    upper_offset = ((1920 / 2) - max_dimension) / 2
    lower_offset = (1920 - upper_offset) - max_dimension

    # General class variables
    image_path = "background.png"
    clip = ImageClip(image_path, duration=duration)

    # Function to build the video
    def build(self):
        # Getting composite clips for each piece
        upper_clip = self.add_upper_image()
        lower_clip = self.add_lower_image()

        # Piecing the composite clips together
        final_clip = CompositeVideoClip([self.clip, upper_clip, lower_clip]).set_fps(30)

        # Saving the final clip
        self.output_video(final_clip)

    def output_video(self, clip):
        clip.write_videofile("test.mp4", fps=30)

    def add_upper_image(self):
        upper_image = ImageClip("upper.jpg", duration=self.duration)

        # Animation functions used as parameters
        def upper_image_translation(t):
            y = self.upper_offset
            offscreen_y = -self.max_dimension
            current_y = offscreen_y + (y - offscreen_y) * min(1, t / self.animation_duration)
            return 'center', current_y

        def upper_image_rotation(t):
            return 0 + (360 - 0) * min(1, t / self.animation_duration)

        def resize_frame(gf, t):
            frame = gf(t)
            print(type(frame))
            height, width, third = frame.shape # Third value is because video is RGB
            print(f"Width: {width}, Height: {height}")

            # Calculating the dimension multipliers and maintaining th aspect ratio
            if width < height:
                height_mult = self.max_dimension / height
                width_mult = height_mult * (9 / 16)
            else:
                width_mult = self.max_dimension / width
                height_mult = width_mult * (16 / 9)

            return np.resize(frame, (int(width * width_mult), int(height * height_mult), third))

        # Adding the animations
        upper_image = upper_image.set_position(upper_image_translation).set_duration(self.duration)
        upper_image = upper_image.add_mask().rotate(upper_image_rotation, expand=True)
        upper_image = upper_image.fl(resize_frame, apply_to='mask')

        # Resizing the clip
        resize_mult = self.calc_resize_mult(upper_image)
        upper_image = upper_image.resize(resize_mult)

        # Returning the composite clip
        return upper_image

    
    def add_lower_image(self):
        lower_image = ImageClip("lower.png", duration=self.duration)

        def lower_image_animation(t):
            y = self.lower_offset
            offscreen_y = 1920
            current_y = offscreen_y + (y - offscreen_y) * min(1, t / self.animation_duration)
            return 'center', current_y


        # Setting the position
        lower_image = lower_image.set_position(lower_image_animation).set_duration(self.duration)

        # Resizing the clip
        resize_mult = self.calc_resize_mult(lower_image)
        lower_image = lower_image.resize(resize_mult)

        # Returning the composite clip
        return lower_image

    # This function calculates the resize multiplier for a clip
    def calc_resize_mult(self, clip):
        # Calculating scaling dimension used from clip
        largest_dimension = clip.w if clip.w > clip.h else clip.h

        # Calculating the downsize multiplier
        size_mult = self.max_dimension / largest_dimension

        # Applying the resize
        return size_mult
