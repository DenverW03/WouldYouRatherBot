import moviepy.editor
from moviepy.video.VideoClip import ImageClip
from moviepy.editor import CompositeVideoClip

class video_builder:
    image_path = "background.png"
    duration = 10
    clip = ImageClip(image_path, duration=duration)

    def output_video(self, clip):
        clip.write_videofile("test.mp4", fps=30)

    def add_upper_image(self):
        upper_image = ImageClip("upper.jpg", duration=self.duration)
        # Compositing the clips together
        composite_clip = CompositeVideoClip([self.clip, upper_image]).set_fps(30)
        
        # Outputting the composite clip
        self.output_video(composite_clip)
