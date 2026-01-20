# Would You Rather? Video Generator

A web application that generates "Would You Rather?" style short-form videos with animated images and text.

## Features

- Simple web interface for video generation
- **Direct image upload** - no external API dependencies
- Image preview before generating
- Animated image entrance/exit effects
- Red/blue themed UI matching the video style
- Local video output with download

## Installation

### Using Conda (Recommended)

```bash
# Create and activate the conda environment
conda env create -f environment.yml
conda activate wouldyourather

# Initialize the Reflex app
reflex init

# Run the application
reflex run
```

### Using pip

```bash
# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize the Reflex app
reflex init

# Run the application
reflex run
```

## Usage

1. Start the application with `reflex run`
2. Open your browser to `http://localhost:3000`
3. Fill in the form:
   - **Option 1 Text**: The first "Would you rather" option text
   - **Option 1 Image**: Upload an image for the first option
   - **Option 2 Text**: The second option text
   - **Option 2 Image**: Upload an image for the second option
4. Click "Generate Video"
5. Wait for processing, then click "Download Video" to save directly to your browser's downloads

## Supported Image Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- GIF (.gif)
- WebP (.webp)
- BMP (.bmp)

## Project Structure

```
WouldYouRatherBot/
├── would_you_rather_bot/       # Main Reflex application
│   ├── __init__.py
│   ├── would_you_rather_bot.py # Main app and state
│   ├── components/             # UI components
│   │   └── __init__.py
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── video_generator.py  # Video generation logic
│   │   └── image_retrieval.py  # Image processing
│   └── assets/                 # Static assets
│       ├── background.jpg      # Video background template
│       └── DejaVuSans-Bold.ttf # Bundled font for text rendering
├── rxconfig.py                 # Reflex configuration
├── environment.yml             # Conda environment specification
├── requirements.txt            # pip dependencies
└── README.md
```

## Configuration

The video settings can be adjusted in `would_you_rather_bot/services/video_generator.py`:

- `DURATION`: Total video length in seconds (default: 10)
- `ANIMATION_DURATION`: Length of entrance/exit animations (default: 0.3s)
- `MAX_DIMENSION`: Maximum image dimension in pixels (default: 500)
- `FPS`: Frames per second (default: 30)

## Requirements

- Python 3.9+
- FFmpeg (for video encoding)

## License

MIT License
