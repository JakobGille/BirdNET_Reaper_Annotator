# BirdNET Analyzer for Reaper

*Note: The code in this repository was generated with the assistance of AI.*

This Python tool  analyzes audio recordings for bird species using the **BirdNET** machine learning model.
The script is optimized for a seamless workflow in **Reaper**, offering both marker generation as CSV, visual sonogram export and generates an CSV overview over the detected bird species.

[Example Sonogram Output](Examples/Example_Sonogram_Output.png)

## Features

- **Multichannel Audio Support:** Accepts mono, stereo, and multichannel audio files, isolating channel 1 for analysis.
- **Reaper Region Export:** Generates a CSV file formatted specifically for Reaper's Region/Marker Manager, allowing instant visualization of detected birds directly on the DAW timeline.
- **Summary CSV Export:** Creates a clean summary table listing all detected species, their scientific names, and total detection counts.
- **Optional Spectrogram Generation:** Generates exact, borderless 60-second spectrogram images (PNG). These serve as a visual frequency map with cyan lines highlighting exactly where the AI detected a bird, making it easier to verify calls visually.

## Prerequisites and Installation

The script requires Python. When installing Python on Windows, ensure the option **"Add Python to PATH"** is checked during the installation process.

You must install the required Python libraries before running the script. Open the command prompt (`cmd`) and execute the following command:

```bash
pip install birdnetlib librosa matplotlib soundfile scipy resampy tensorflow geopy

```

*Note: `tensorflow` is explicitly required as the runtime environment for the BirdNET machine learning model.*

## Usage

1. Run the script via the command line or by executing the file:

```bash
python bird_analyzer.py

```

1. Select your input audio file and the desired output directory.
2. Enter the location metadata for the recording:

- **Latitude / Longitude:** Decimal format (e.g., 45.5 and -73.6).
- **Calendar Week:** 1 to 52.

1. Set the detection **Threshold** (0.1 to 1.0). A value of `0.3` is recommended.
2. (Optional) Check the box to generate spectrogram images. *Note: This significantly increases processing time.*
3. Click **Start Analysis**. The model will be downloaded automatically upon the very first execution.

## Reaper Integration Workflow

### Method 1: Using the Region/Marker Manager (Recommended)

This is the fastest way to see the results in your timeline.

1. Import your original audio file into a Reaper track. Ensure the item starts exactly at `0:00.000`.
2. In the top menu, navigate to **View** > **Region/Marker Manager**.
3. Right-click in the empty area of the manager window and select **Import regions/markers...**.
4. Select the generated `[filename]_reaper_regions.csv` file.
5. The detected birds will immediately appear as labeled regions above your audio item, aligned with the audio events.

### Method 2: Using the Spectrogram Images

If you chose to generate the spectrograms, the script splits your audio into 60-second chunks and exports them as borderless PNG images. This is useful if you want to visually verify the bird calls in the frequency spectrum without rendering spectral views natively in Reaper.

To align them:

1. Create a new, empty track directly below your main audio track.
2. Drag and drop the generated images (`_min_001.png`, `_min_002.png`, etc.) onto this new track in sequential order.
3. By default, Reaper assigns a static length to imported images (e.g., 1 measure or 10 seconds). Because the images represent exactly 60 seconds of audio, you must grab the right edge of each image item and stretch it until its length is exactly **60s**.
4. Snap the stretched images back-to-back.
5. Because the images were generated without borders, the cyan vertical markers on the PNGs will now perfectly sync up with the audio waveforms of the track above.

### Citation & Acknowledgments

This tool utilizes the BirdNET algorithm for avian detection and refers to the original BirdNET publication:
```bash
@article{kahl2021birdnet,
  title={BirdNET: A deep learning solution for avian diversity monitoring},
  author={Kahl, Stefan and Wood, Connor M and Eibl, Maximilian and Klinck, Holger},
  journal={Ecological Informatics},
  volume={61},
  pages={101236},
  year={2021},
  publisher={Elsevier}
}
```
