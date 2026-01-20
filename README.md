# Would You Rather? Video Generator

A web application that generates "Would You Rather?" style short-form videos with animated images and text.

## Features

- Simple web interface for video generation
- Automatic image retrieval based on search terms
- Animated image entrance/exit effects
- Red/blue themed UI matching the video style
- Local video output

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
   - **Upper Text**: The first "Would you rather" option text
   - **Lower Text**: The second option text
   - **Upper Image Search**: Search term for the top image
   - **Lower Image Search**: Search term for the bottom image
4. Click "Generate Video"
5. Wait for processing, then download your video

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
│   │   └── image_retrieval.py  # Image search functionality
│   └── assets/                 # Static assets
│       └── background.jpg      # Video background template
├── output/                     # Generated videos directory
├── rxconfig.py                 # Reflex configuration
├── environment.yml             # Conda environment specification
├── requirements.txt            # pip dependencies
└── README.md
```

## Configuration

The video settings can be adjusted in `would_you_rather_bot/services/video_generator.py`:

- `duration`: Total video length in seconds
- `animation_duration`: Length of entrance/exit animations
- `max_dimension`: Maximum image dimension in pixels

## Requirements

- Python 3.9+
- FFmpeg (for video encoding)

## License

MIT License
