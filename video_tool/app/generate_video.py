from moviepy import *
import numpy as np
from PIL import Image

# Global variables (video settings)
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

def build_video(upper_text, lower_text, upper_image, lower_image, save_uri):
    """Build the resulting composite video clip and save it to the specified location."""
    # Getting composite clips for each piece
    upper_clip = add_image(upper_offset, False, upper_image)
    lower_clip = add_image(lower_offset, True, lower_image)

    # Creating the text clips
    upper_clip_text = add_text(upper_offset_text, upper_text)
    lower_clip_text = add_text(lower_offset_text, lower_text)

    # Piecing the composite clips together
    final_clip = CompositeVideoClip([clip, upper_clip, lower_clip, upper_clip_text.with_start(text_start), lower_clip_text.with_start(text_start)]).with_fps(30)

    # Saving the final clip
    final_clip.write_videofile(save_uri, fps=30)

def add_text( y_offset, text):
    """Create and return a text clip.

    Args:
        y_offset (int): The vertical position on the screen.
        text (str): The text to add.

    Returns:
        TextClip: The created text clip.
    """
    # Creating the text clip
    text_clip = TextClip(text=text, size=(1080, 1920), vertical_align="top", font_size=100, color='white', font='Arial Black', stroke_color='black', stroke_width=4)
    text_clip = text_clip.with_position(('center', y_offset)).with_duration(duration - text_start)
    return text_clip

def add_image( y_offset, side, image_path):
    """Add and animate an image.

    Args:
        y_offset (int): The y offset on the screen.
        side (bool): The side the entrance animation starts from (True for left, False for right).
        image_path (str): The path to the image.

    Returns:
        ImageClip: The animated image clip.
    """
    # Load the image
    image = ImageClip(image_path, duration=duration)
    
    # Resize the image to fit max_dimension
    image = image.resized(calc_resize_mult(image))
    
    # Create the rotation and translation transformation
    def rotate_and_translate(get_frame, t):
        frame = get_frame(t)
        
        # Calculate rotation angle
        start_angle = 90
        end_angle = 0
        current_angle = start_angle + (end_angle - start_angle) * min(1, t / animation_duration)
        
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
        if t >= duration - image_exit_offset:
            if not side:  # right
                offscreen_x = -max_dimension
                current_x = x + (offscreen_x - x) * min(1, (t - (duration - image_exit_offset)) / animation_duration)
            else:  # left
                offscreen_x = 1080
                current_x = x - (x - offscreen_x) * min(1, (t - (duration - image_exit_offset)) / animation_duration)
            return current_x, y_offset
        
        # Entrance animation
        if not side:  # right
            offscreen_x = -max_dimension
            current_x = offscreen_x + (x - offscreen_x) * min(1, t / animation_duration)
        else:  # left
            offscreen_x = 1080
            current_x = offscreen_x - (offscreen_x - x) * min(1, t / animation_duration)
        
        return current_x, y_offset
    
    # Apply position animation
    image = image.with_position(get_position).with_duration(duration)
    
    return image

def calc_resize_mult( clip):
    """Calculate the resize multiplier for a clip.

    Args:
        clip (ImageClip): The clip to calculate the resize for.

    Returns:
        float: The resize multiplier.
    """
    # Calculating scaling dimension used from clip
    largest_dimension = clip.w if clip.w > clip.h else clip.h

    # Calculating the downsize multiplier
    size_mult = max_dimension / largest_dimension

    # Applying the resize
    return size_mult
