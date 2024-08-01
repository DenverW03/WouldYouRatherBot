import moviepy.editor
from moviepy.video.VideoClip import ImageClip, np
from moviepy.editor import CompositeVideoClip
import moviepy.video.fx.all
import numpy as np
from PIL import Image

class video_builder:
    # Settings class variables
    duration = 10
    animation_duration = 0.3
    max_dimension = 500
    upper_offset = ((1920 / 2) - max_dimension) / 2
    lower_offset = (1920 - upper_offset) - max_dimension

    # General class variables
    image_path = "background.png"
    clip = ImageClip(image_path, duration=duration)

    # Function to build the video
    def build(self):
        # Getting composite clips for each piece
        upper_clip = self.add_image(self.upper_offset, False, "upper.jpg")
        lower_clip = self.add_image(self.lower_offset, True, "lower.png")

        # Piecing the composite clips together
        final_clip = CompositeVideoClip([self.clip, upper_clip, lower_clip]).set_fps(30)

        # Saving the final clip
        self.output_video(final_clip)

    def output_video(self, clip):
        clip.write_videofile("test.mp4", fps=30)

    # Adds an image and animates int
    # y_offset (int) = the y offset on the screen, to dictate whether upper or lower
    # side (bool) = the side the entrance animation starts from, true = left, false = right
    # image (str) = a str containing the path to the image
    def add_image(self, y_offset, side, image):
        upper_image = ImageClip(image, duration=self.duration)

        # Animation functions used as parameters
        def translate_clip(t, clip):
            x = (1080 / 2) - (clip.h / 2) # clip.h represents with here for some reason, cba figuring it out

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
        upper_image = upper_image.add_mask()
        upper_image = upper_image.fl(rotate_frame, apply_to='mask')
        upper_image = upper_image.set_position(lambda t: translate_clip(t, upper_image)).set_duration(self.duration)

        # Returning the composite clip
        return upper_image

    # This function calculates the resize multiplier for a clip
    def calc_resize_mult(self, clip):
        # Calculating scaling dimension used from clip
        largest_dimension = clip.w if clip.w > clip.h else clip.h

        # Calculating the downsize multiplier
        size_mult = self.max_dimension / largest_dimension

        # Applying the resize
        return size_mult
