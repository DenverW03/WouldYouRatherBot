from generate_video import video_builder

# Main function is used to drive the steps of building a video
if __name__ == '__main__':
    vid_builder = video_builder("Be a chef", "Be a doctor", "resources/upper.jpg", "resources/lower.jpg")
    vid_builder.build()
