> **Note:** The code in this repository and its documentation were created with the assistance of AI.

# AvianTag: BirdNET Analyzer for REAPER

This repository provides a Python-based toolset to analyze audio recordings for bird species using the **BirdNET** machine learning model. It is highly optimized for **REAPER** and offers two distinct workflows depending on your needs:

1. **Reaper Action (Lua + CLI):** A fully automated, one-click integration that runs directly inside REAPER, analyzes the selected item(s), and automatically draws the detected regions onto your timeline.
2. **Standalone Application (GUI):** A desktop application with a graphical interface for batch-processing files outside of REAPER, optionally generating visual spectrograms.

Example Sonogram Output

## Features

- **Dual Workflow:** Choose between seamless in-DAW automation or an external batch-processing GUI.
- **Batch Processing in REAPER:** Select multiple items on your timeline to analyze them sequentially with a single click.
- **Multichannel Audio Support:** Accepts mono, stereo, and multichannel (Ambisonics) audio files, isolating channel 1 (W-channel) for analysis.
- **Merge Gap Control:** Intelligently groups detections by species and merges consecutive detections of the same bird into a single, continuous region if the time between them is smaller than the defined gap.
- **Auto-Alignment (Lua):** Automatically compensates for the item's position on the REAPER timeline.
- **Optional Spectrogram Generation (GUI only):** Generates exact, borderless 60-second spectrogram images (PNG) with cyan lines highlighting detections.

## Prerequisites and Installation

You need Python installed on your system. When installing Python on Windows, ensure the option **"Add Python to PATH"** is checked.

Open your terminal or command prompt and install the required libraries:

```
pip install birdnetlib librosa matplotlib soundfile scipy resampy tensorflow geopy
```

*Note: `tensorflow` is explicitly required as the runtime environment for the BirdNET machine learning model. The model file will be downloaded automatically upon the first execution.*

## Repository Structure

- `/Reaper_Action`: Contains the Lua script (`Analyze_BirdNET.lua`) and the headless Python CLI (`AvianTag_CLI.py`).
- `/Standalone`: Contains the desktop GUI application (`AvianTag_GUI.py`).

---

## Workflow 1: The REAPER Action (Automated In-DAW)

This is the recommended workflow for analyzing specific audio items while actively editing in REAPER.

### Setup

1. Open `Reaper_Action/Analyze_BirdNET.lua` in a text editor.
2. Adjust the `SCRIPT_PATH` variable at the top of the file to point to the exact location of `AvianTag_CLI.py` on your computer.
3. In REAPER, go to **Actions > Show action list > New action > Load ReaScript** and load the Lua script. Assign a keyboard shortcut to it for maximum efficiency.

### Usage

1. Select **one or multiple** audio items in your REAPER project. *(Note: Your project must be saved so the script can create the output directory!)*
2. **Metadata Preparation (Optional but recommended):** Open the Item Properties (`F2`) of the **first** selected item. In the **Notes** field at the bottom, enter your location and time data exactly like this:
  `LAT:45.5 LON:-73.6 KW:23`
   *(Note: When processing a batch of multiple items, the script will read the metadata only from the first selected item and apply it to the rest).*
3. Run the Lua script.
  - If you filled out the Item Notes for the first item, the analysis will start silently in the background.
  - If the Item Notes are empty, a native REAPER pop-up will ask you for the Latitude, Longitude, and Calendar Week **once**, and apply these values to the entire batch.
4. Wait for the analysis to finish. REAPER will be unresponsive during the background processing.
5. The detected birds will instantly appear as REAPER regions directly over your items, perfectly synced. The raw CSV data and summaries are automatically saved in a new `BirdNet Analysis` folder within your project directory.

---

## Workflow 2: The Standalone Application (External Batch Processing)

This workflow is ideal for processing multiple files simultaneously or generating spectrogram visualisations.

### Usage

1. Run the script via your terminal or IDE:
  python Standalone/AvianTag_GUI.py
2. Select your input audio files and the desired output directory.
3. Enter the location metadata (City search or manual Lat/Lon) and the Calendar Week.
4. Set the detection **Threshold** (0.1 to 1.0) and the **Merge Gap** in seconds.
5. *(Optional)* Check the box to generate spectrogram images.
6. Click **Start Analysis**.

### Importing Results into REAPER

**Method A: Region/Marker Manager**

1. Import your audio file into REAPER, ensuring the item starts exactly at `0:00.000`.
2. Go to **View > Region/Marker Manager**.
3. Right-click > **Import regions/markers...** and select the generated `_BIRDNET_Reaper_Regions.csv` file.

**Method B: Spectrogram Images**

1. Create a new track below your audio.
2. Drag the generated images (`_min_001.png`, `_min_002.png`, etc.) onto the track in order.
3. Stretch the right edge of each image item until its length is exactly **60s**. Snap them back-to-back. The cyan lines on the images will now sync perfectly with the audio waveform above.

---

## Citation & Acknowledgments

This tool utilizes the BirdNET algorithm for avian detection and refers to the original BirdNET publication:

```
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