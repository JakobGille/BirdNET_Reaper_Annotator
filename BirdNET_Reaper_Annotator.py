import tkinter as tk
from tkinter import filedialog, messagebox
import librosa
import soundfile as sf
import matplotlib.pyplot as plt
import numpy as np
import os
import tempfile
import math
import csv
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

def run_analysis():
    # Get user inputs from the GUI
    file_path = entry_file.get()
    out_dir = entry_out.get()
    
    # Check if both paths are provided
    if not file_path or not out_dir:
        messagebox.showwarning("Missing Paths", "Please select an audio file and an output directory.")
        return

    # Parse and validate numerical inputs
    try:
        lat = float(entry_lat.get())
        lon = float(entry_lon.get())
        kw = int(entry_kw.get())
        threshold = float(entry_thresh.get())
    except ValueError:
        messagebox.showwarning("Invalid Input", "Please check your inputs for coordinates, week, and threshold.")
        return

    # Convert the standard 52-week calendar format into BirdNET's required 48-week format
    week_48 = max(1, min(48, int(kw * 48 / 52)))
    do_images = var_images.get()

    # Disable the start button while the background processing is running
    btn_start.config(state=tk.DISABLED, text="Analyzing... Please wait.")
    root.update()

    try:
        # 1. Load the audio file and extract the first channel (e.g., W-channel for Ambisonics)
        print(f"Loading {file_path}...")
        y, sr = librosa.load(file_path, sr=48000, mono=False)
        if y.ndim > 1:
            y = y[0] # Keep only the first channel
        
        # 2. Save a temporary mono WAV file required by the BirdNET analyzer
        temp_wav = os.path.join(tempfile.gettempdir(), "temp_mono_birdnet.wav")
        sf.write(temp_wav, y, sr)
        
        # 3. Initialize and run the BirdNET analysis
        print("Starting BirdNET analysis...")
        analyzer = Analyzer()
        recording = Recording(
            analyzer,
            temp_wav,
            lat=lat,
            lon=lon,
            week_48=week_48,
            min_conf=threshold
        )
        recording.analyze()
        detections = recording.detections
        
        # Extract the base name of the audio file without extension
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 4. Write the summary CSV file (Grouped and counted species)
        csv_path = os.path.join(out_dir, f"{base_name}_bird_summary.csv")
        
        # Count the occurrences of each bird species
        bird_counts = {}
        for det in detections:
            # birdnetlib returns common_name in English by default
            key = (det['common_name'], det['scientific_name'])
            bird_counts[key] = bird_counts.get(key, 0) + 1
            
        with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file, delimiter=';')
            
            # Write the metadata header row
            # Column A: File Title | Column B: Lat, Lon | Column C: Calendar Week
            writer.writerow([base_name, f"{lat}, {lon}", f"Week {kw}"])
            writer.writerow([]) # Empty row for visual separation
            
            # Write the table headers in English
            writer.writerow(['Common Name (EN)', 'Scientific Name', 'Detection Count'])
            
            # Sort the birds by detection count in descending order and write to CSV
            sorted_birds = sorted(bird_counts.items(), key=lambda item: item[1], reverse=True)
            for (name_en, name_sci), count in sorted_birds:
                writer.writerow([name_en, name_sci, count])
                
        print(f"Summary CSV created: {csv_path}")
        
        # 5. Write the Reaper Region CSV file (for DAW import)
        reaper_path = os.path.join(out_dir, f"{base_name}_reaper_regions.csv")
        with open(reaper_path, mode='w', newline='', encoding='utf-8') as reaper_file:
            # Reaper requires a comma delimiter for markers/regions
            writer = csv.writer(reaper_file, delimiter=',')
            writer.writerow(['#', 'Name', 'Start', 'End', 'Length', 'Color'])
            
            for idx, det in enumerate(detections):
                region_id = f"R{idx+1}"
                name = f"{det['common_name']} ({det['confidence']:.2f})"
                start = det['start_time']
                end = det['end_time']
                length = end - start
                # Leave color empty so Reaper assigns its default color automatically
                writer.writerow([region_id, name, start, end, length, ""])
                
        print(f"Reaper Region file created: {reaper_path}")

        # 6. Generate Spectrogram Images (if the checkbox is checked)
        if do_images:
            segment_length_s = 60 # Length of each image in seconds
            segment_samples = segment_length_s * sr
            total_duration_s = len(y) / sr
            total_segments = math.ceil(total_duration_s / segment_length_s)
            
            print(f"Creating {total_segments} borderless spectrogram images...")
            for i in range(total_segments):
                # Calculate start and end samples for the current 60-second segment
                start_sample = i * segment_samples
                end_sample = min((i + 1) * segment_samples, len(y))
                y_segment = y[start_sample:end_sample]
                
                start_time_s = i * segment_length_s
                end_time_s = start_time_s + (len(y_segment) / sr)
                
                # Compute the spectrogram (Decibel scale)
                D = librosa.amplitude_to_db(np.abs(librosa.stft(y_segment)), ref=np.max)
                
                # Create a figure that takes up 100% of the canvas (no borders)
                plt.figure(figsize=(20, 6))
                ax = plt.axes([0, 0, 1, 1])
                
                librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='linear', cmap='magma', ax=ax)
                ax.axis('off') # Hide axes and borders entirely
                
                # Draw vertical lines for detected birds within this time segment
                for det in detections:
                    det_start = det['start_time']
                    det_end = det['end_time']
                    
                    # Check if the bird detection overlaps with the current 60-second window
                    if det_end >= start_time_s and det_start <= end_time_s:
                        # Calculate relative positions for the image x-axis
                        rel_start = max(0, det_start - start_time_s)
                        rel_end = min(segment_length_s, det_end - start_time_s)
                        
                        label = f"{det['common_name']} ({det['confidence']:.2f})"
                        
                        # Draw cyan lines to mark the start and end of the detection
                        ax.axvline(x=rel_start, color='cyan', linestyle='-', linewidth=2)
                        ax.axvline(x=rel_end, color='cyan', linestyle='-', linewidth=2)
                        
                        # Add text label for the bird
                        ax.text(rel_start, sr/5, label, color='white', rotation=90, 
                                 verticalalignment='bottom', backgroundcolor='black', fontsize=12)
                
                # Save the image without padding (pad_inches=0 ensures no white borders)
                out_path = os.path.join(out_dir, f"{base_name}_min_{i+1:03d}.png")
                plt.savefig(out_path, dpi=150, bbox_inches='tight', pad_inches=0)
                plt.close()
                
        # Clean up the temporary mono audio file
        os.remove(temp_wav)
        messagebox.showinfo("Success", "Analysis complete. Files exported successfully!")
        
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        # Re-enable the start button after processing finishes or crashes
        btn_start.config(state=tk.NORMAL, text="Start Analysis")

# --- GUI Setup ---
root = tk.Tk()
root.title("BirdNET Analyzer for Reaper")
root.geometry("480x400")

def select_file():
    path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.flac *.mp3")])
    if path: entry_file.delete(0, tk.END); entry_file.insert(0, path)

def select_dir():
    path = filedialog.askdirectory()
    if path: entry_out.delete(0, tk.END); entry_out.insert(0, path)

tk.Label(root, text="Audio File:").pack(pady=(10,0))
entry_file = tk.Entry(root, width=60); entry_file.pack()
tk.Button(root, text="Browse", command=select_file).pack()

tk.Label(root, text="Output Directory:").pack(pady=(10,0))
entry_out = tk.Entry(root, width=60); entry_out.pack()
tk.Button(root, text="Browse", command=select_dir).pack()

frame_params = tk.Frame(root)
frame_params.pack(pady=10)

tk.Label(frame_params, text="Latitude:").grid(row=0, column=0, sticky="e", padx=5)
entry_lat = tk.Entry(frame_params, width=15); entry_lat.grid(row=0, column=1)
entry_lat.insert(0, "45.5")

tk.Label(frame_params, text="Longitude:").grid(row=1, column=0, sticky="e", padx=5)
entry_lon = tk.Entry(frame_params, width=15); entry_lon.grid(row=1, column=1)
entry_lon.insert(0, "-73.6")

tk.Label(frame_params, text="Calendar Week (1-52):").grid(row=2, column=0, sticky="e", padx=5)
entry_kw = tk.Entry(frame_params, width=15); entry_kw.grid(row=2, column=1)
entry_kw.insert(0, "23")

tk.Label(frame_params, text="Threshold (0.1 - 1.0):").grid(row=3, column=0, sticky="e", padx=5)
entry_thresh = tk.Entry(frame_params, width=15); entry_thresh.grid(row=3, column=1)
entry_thresh.insert(0, "0.7")

var_images = tk.BooleanVar(value=False)
tk.Checkbutton(root, text="Generate Spectrogram Images (takes longer)", variable=var_images).pack(pady=5)

btn_start = tk.Button(root, text="Start Analysis", command=run_analysis, bg="green", fg="white", font=("Arial", 12))
btn_start.pack(pady=10)

root.mainloop()