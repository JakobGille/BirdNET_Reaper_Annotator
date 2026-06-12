import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import tkinter as tk
from tkinter import filedialog, messagebox
import librosa
import soundfile as sf
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import math
import csv
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer
from geopy.geocoders import Nominatim

def fetch_coordinates():
    """Fetches latitude and longitude for a given city name using OpenStreetMap."""
    city_name = entry_city.get().strip()
    if not city_name:
        messagebox.showwarning("Missing Input", "Please enter a city name.")
        return
        
    try:
        geolocator = Nominatim(user_agent="birdnet_reaper_analyzer_tool")
        location = geolocator.geocode(city_name)
        
        if location:
            entry_lat.delete(0, tk.END)
            entry_lat.insert(0, str(round(location.latitude, 4)))
            
            entry_lon.delete(0, tk.END)
            entry_lon.insert(0, str(round(location.longitude, 4)))
        else:
            messagebox.showwarning("Not Found", f"Could not find coordinates for '{city_name}'.")
    except Exception as e:
        messagebox.showerror("Network Error", f"Failed to retrieve coordinates.\n\nDetails: {e}")

def run_analysis():
    file_paths_string = entry_file.get()
    out_dir = entry_out.get()
    
    if not file_paths_string or not out_dir:
        messagebox.showwarning("Missing Paths", "Please select at least one audio file and an output directory.")
        return

    file_paths = file_paths_string.split("; ")

    # Parse numerical inputs, including the new time_offset
    try:
        lat = float(entry_lat.get())
        lon = float(entry_lon.get())
        kw = int(entry_kw.get())
        threshold = float(entry_thresh.get())
        merge_gap = float(entry_gap.get())
        time_offset = float(entry_offset.get())
    except ValueError:
        messagebox.showwarning("Invalid Input", "Please check your numerical inputs (Coordinates, Week, Threshold, Merge Gap, Offset).")
        return

    week_48 = max(1, min(48, int(kw * 48 / 52)))
    do_images = var_images.get()

    btn_start.config(state=tk.DISABLED)
    root.update()

    try:
        print("Initializing BirdNET analyzer...")
        analyzer = Analyzer()

        for idx, file_path in enumerate(file_paths):
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            btn_start.config(text=f"Analyzing {idx + 1}/{len(file_paths)}... Please wait.")
            root.update()
            print(f"--- Processing File {idx + 1} of {len(file_paths)}: {base_name} ---")

            y, sr = librosa.load(file_path, sr=48000, mono=False)
            if y.ndim > 1:
                y = y[0] 
            
            temp_wav = os.path.join(tempfile.gettempdir(), f"temp_mono_birdnet_{idx}.wav")
            sf.write(temp_wav, y, sr)
            
            recording = Recording(
                analyzer,
                temp_wav,
                lat=lat,
                lon=lon,
                week_48=week_48,
                min_conf=threshold
            )
            recording.analyze()
            raw_detections = recording.detections
            
            # --- Merge Logic ---
            grouped_detections = {}
            for det in raw_detections:
                key = (det['common_name'], det['scientific_name'])
                if key not in grouped_detections:
                    grouped_detections[key] = []
                grouped_detections[key].append(det)
                
            merged_detections = []
            for key, det_list in grouped_detections.items():
                det_list = sorted(det_list, key=lambda x: x['start_time'])
                current_merged = [det_list[0].copy()]
                
                for i in range(1, len(det_list)):
                    current_det = det_list[i]
                    previous_det = current_merged[-1]
                    
                    time_gap = current_det['start_time'] - previous_det['end_time']
                    
                    if time_gap <= merge_gap:
                        previous_det['end_time'] = max(previous_det['end_time'], current_det['end_time'])
                        previous_det['confidence'] = max(previous_det['confidence'], current_det['confidence'])
                    else:
                        current_merged.append(current_det.copy())
                        
                merged_detections.extend(current_merged)
                
            merged_detections = sorted(merged_detections, key=lambda x: x['start_time'])
            
            # Export Summary CSV (Offset does not apply here as it contains no timestamps)
            csv_path = os.path.join(out_dir, f"{base_name}_BIRDNET_Summary.csv")
            
            bird_counts = {}
            for det in merged_detections:
                key = (det['common_name'], det['scientific_name'])
                bird_counts[key] = bird_counts.get(key, 0) + 1
                
            with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
                writer = csv.writer(csv_file, delimiter=';')
                writer.writerow([base_name, f"{lat}, {lon}", f"Week {kw}"])
                writer.writerow([f"Threshold: {threshold}", f"Merge Gap: {merge_gap}s", f"Offset: {time_offset}s"])
                writer.writerow([]) 
                writer.writerow(['Common Name (EN)', 'Scientific Name', 'Detection Count'])
                
                sorted_birds = sorted(bird_counts.items(), key=lambda item: item[1], reverse=True)
                for (name_en, name_sci), count in sorted_birds:
                    writer.writerow([name_en, name_sci, count])
                    
            print(f"Summary CSV created: {csv_path}")
            
            # Export Reaper Region CSV (Offset is applied to absolute timestamps)
            reaper_path = os.path.join(out_dir, f"{base_name}_BIRDNET_Reaper_Regions.csv")
            with open(reaper_path, mode='w', newline='', encoding='utf-8') as reaper_file:
                writer = csv.writer(reaper_file, delimiter=',')
                writer.writerow(['#', 'Name', 'Start', 'End', 'Length', 'Color'])
                
                for det_idx, det in enumerate(merged_detections):
                    region_id = f"R{det_idx+1}"
                    name = f"{det['common_name']} ({det['confidence']:.2f})"
                    length = det['end_time'] - det['start_time']
                    
                    # Apply the user-defined time offset to shift the region on the timeline
                    offset_start = det['start_time'] + time_offset
                    offset_end = det['end_time'] + time_offset
                    
                    writer.writerow([region_id, name, offset_start, offset_end, length, ""])
                    
            print(f"Reaper Region file created: {reaper_path}")

            # Generate Spectrogram Images (Offset does not apply to audio analysis bounds)
            if do_images:
                segment_length_s = 60
                segment_samples = segment_length_s * sr
                total_duration_s = len(y) / sr
                total_segments = math.ceil(total_duration_s / segment_length_s)
                
                print(f"Creating {total_segments} borderless spectrogram images for {base_name}...")
                for i in range(total_segments):
                    start_sample = i * segment_samples
                    end_sample = min((i + 1) * segment_samples, len(y))
                    y_segment = y[start_sample:end_sample]
                    
                    start_time_s = i * segment_length_s
                    end_time_s = start_time_s + (len(y_segment) / sr)
                    
                    D = librosa.amplitude_to_db(np.abs(librosa.stft(y_segment)), ref=np.max)
                    
                    plt.figure(figsize=(20, 6))
                    ax = plt.axes([0, 0, 1, 1])
                    
                    librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='linear', cmap='magma', ax=ax)
                    ax.axis('off')
                    
                    for det in merged_detections:
                        det_start = det['start_time']
                        det_end = det['end_time']
                        
                        if det_end >= start_time_s and det_start <= end_time_s:
                            rel_start = max(0, det_start - start_time_s)
                            rel_end = min(segment_length_s, det_end - start_time_s)
                            
                            label = f"{det['common_name']} ({det['confidence']:.2f})"
                            
                            ax.axvline(x=rel_start, color='cyan', linestyle='-', linewidth=2)
                            ax.axvline(x=rel_end, color='cyan', linestyle='-', linewidth=2)
                            ax.text(rel_start, sr/5, label, color='white', rotation=90, 
                                     verticalalignment='bottom', backgroundcolor='black', fontsize=12)
                    
                    out_path = os.path.join(out_dir, f"{base_name}_min_{i+1:03d}.png")
                    plt.savefig(out_path, dpi=150, bbox_inches='tight', pad_inches=0)
                    plt.close()
                    
            os.remove(temp_wav)
            
        messagebox.showinfo("Success", f"Analysis complete. {len(file_paths)} file(s) exported successfully!")
        
    except Exception as e:
        messagebox.showerror("Error", str(e))
    finally:
        btn_start.config(state=tk.NORMAL, text="Start Analysis")

# --- GUI Setup ---
root = tk.Tk()
root.title("AvianTag - Audio Analyzer")
root.geometry("500x550") # Height increased for new parameter

def select_file():
    paths = filedialog.askopenfilenames(filetypes=[("Audio Files", "*.wav *.flac *.mp3")])
    if paths:
        entry_file.delete(0, tk.END)
        entry_file.insert(0, "; ".join(paths))

def select_dir():
    path = filedialog.askdirectory()
    if path: 
        entry_out.delete(0, tk.END)
        entry_out.insert(0, path)

tk.Label(root, text="Audio Files (Multiple selection allowed):").pack(pady=(10,0))
entry_file = tk.Entry(root, width=65); entry_file.pack()
tk.Button(root, text="Browse", command=select_file).pack()

tk.Label(root, text="Output Directory:").pack(pady=(10,0))
entry_out = tk.Entry(root, width=65); entry_out.pack()
tk.Button(root, text="Browse", command=select_dir).pack()

# --- Location & Parameters Frame ---
frame_params = tk.Frame(root)
frame_params.pack(pady=15)

tk.Label(frame_params, text="City (optional):").grid(row=0, column=0, sticky="e", padx=5, pady=(0,10))
entry_city = tk.Entry(frame_params, width=15)
entry_city.grid(row=0, column=1, pady=(0,10))
btn_search_city = tk.Button(frame_params, text="Search City", command=fetch_coordinates, bg="#e0e0e0")
btn_search_city.grid(row=0, column=2, padx=5, pady=(0,10))

tk.Label(frame_params, text="Latitude:").grid(row=1, column=0, sticky="e", padx=5)
entry_lat = tk.Entry(frame_params, width=15); entry_lat.grid(row=1, column=1)
entry_lat.insert(0, "45.5")

tk.Label(frame_params, text="Longitude:").grid(row=2, column=0, sticky="e", padx=5)
entry_lon = tk.Entry(frame_params, width=15); entry_lon.grid(row=2, column=1)
entry_lon.insert(0, "-73.6")

tk.Label(frame_params, text="Calendar Week (1-52):").grid(row=3, column=0, sticky="e", padx=5, pady=(10,0))
entry_kw = tk.Entry(frame_params, width=15); entry_kw.grid(row=3, column=1, pady=(10,0))
entry_kw.insert(0, "23")

tk.Label(frame_params, text="Threshold (0.1 - 1.0):").grid(row=4, column=0, sticky="e", padx=5)
entry_thresh = tk.Entry(frame_params, width=15); entry_thresh.grid(row=4, column=1)
entry_thresh.insert(0, "0.7")

tk.Label(frame_params, text="Merge Gap (s):").grid(row=5, column=0, sticky="e", padx=5, pady=(10,0))
entry_gap = tk.Entry(frame_params, width=15); entry_gap.grid(row=5, column=1, pady=(10,0))
entry_gap.insert(0, "3.0") 

# New Offset Parameter
tk.Label(frame_params, text="Item Start Offset (s):").grid(row=6, column=0, sticky="e", padx=5, pady=(10,0))
entry_offset = tk.Entry(frame_params, width=15); entry_offset.grid(row=6, column=1, pady=(10,0))
entry_offset.insert(0, "0.0") 

# --- Options & Execution ---
var_images = tk.BooleanVar(value=False)
tk.Checkbutton(root, text="Generate Spectrogram Images (takes longer)", variable=var_images).pack(pady=5)

btn_start = tk.Button(root, text="Start Analysis", command=run_analysis, bg="green", fg="white", font=("Arial", 12))
btn_start.pack(pady=10)

root.mainloop()