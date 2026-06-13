import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import argparse
import librosa
import soundfile as sf
import numpy as np
import tempfile
import csv
from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

def main():
    # Setup command line argument parsing
    parser = argparse.ArgumentParser(description="Headless BirdNET Analyzer for Reaper")
    parser.add_argument("filepath", help="Absolute path to the audio file")
    parser.add_argument("outdir", help="Absolute path to the output directory")
    parser.add_argument("--offset", type=float, default=0.0, help="Item start offset in seconds")
    parser.add_argument("--lat", type=float, default=45.5, help="Latitude")
    parser.add_argument("--lon", type=float, default=-73.6, help="Longitude")
    parser.add_argument("--kw", type=int, default=23, help="Calendar Week (1-52)")
    parser.add_argument("--thresh", type=float, default=0.5, help="Detection threshold (0.1 - 1.0)")
    parser.add_argument("--gap", type=float, default=3.0, help="Merge gap in seconds")
    
    args = parser.parse_args()
    
    base_name = os.path.splitext(os.path.basename(args.filepath))[0]
    print(f"Analyzing {base_name}...")

    # Load the audio file and extract the first channel
    y, sr = librosa.load(args.filepath, sr=48000, mono=False)
    if y.ndim > 1:
        y = y[0] 
        
    temp_wav = os.path.join(tempfile.gettempdir(), "temp_mono_birdnet_cli.wav")
    sf.write(temp_wav, y, sr)
    
    # Run BirdNET analysis
    analyzer = Analyzer()
    recording = Recording(
        analyzer,
        temp_wav,
        lat=args.lat,
        lon=args.lon,
        week_48=max(1, min(48, int(args.kw * 48 / 52))),
        min_conf=args.thresh
    )
    recording.analyze()
    raw_detections = recording.detections
    
    # Merge Logic
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
            
            if time_gap <= args.gap:
                previous_det['end_time'] = max(previous_det['end_time'], current_det['end_time'])
                previous_det['confidence'] = max(previous_det['confidence'], current_det['confidence'])
            else:
                current_merged.append(current_det.copy())
                
        merged_detections.extend(current_merged)
        
    merged_detections = sorted(merged_detections, key=lambda x: x['start_time'])
    
    # Export Summary CSV
    csv_path = os.path.join(args.outdir, f"{base_name}_BIRDNET_Summary.csv")
    bird_counts = {}
    for det in merged_detections:
        key = (det['common_name'], det['scientific_name'])
        bird_counts[key] = bird_counts.get(key, 0) + 1
        
    with open(csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file, delimiter=';')
        writer.writerow([base_name, f"{args.lat}, {args.lon}", f"Week {args.kw}"])
        writer.writerow([f"Threshold: {args.thresh}", f"Merge Gap: {args.gap}s", f"Offset: {args.offset}s"])
        writer.writerow([]) 
        writer.writerow(['Common Name (EN)', 'Scientific Name', 'Detection Count'])
        sorted_birds = sorted(bird_counts.items(), key=lambda item: item[1], reverse=True)
        for (name_en, name_sci), count in sorted_birds:
            writer.writerow([name_en, name_sci, count])
            
    # Export Reaper Region CSV (with offset applied)
    reaper_path = os.path.join(args.outdir, f"{base_name}_BIRDNET_Reaper_Regions.csv")
    with open(reaper_path, mode='w', newline='', encoding='utf-8') as reaper_file:
        writer = csv.writer(reaper_file, delimiter=',')
        writer.writerow(['#', 'Name', 'Start', 'End', 'Length', 'Color'])
        
        for det_idx, det in enumerate(merged_detections):
            region_id = f"R{det_idx+1}"
            name = f"{det['common_name']} ({det['confidence']:.2f})"
            length = det['end_time'] - det['start_time']
            offset_start = det['start_time'] + args.offset
            offset_end = det['end_time'] + args.offset
            writer.writerow([region_id, name, offset_start, offset_end, length, ""])
            
    os.remove(temp_wav)
    print("Analysis complete.")

if __name__ == "__main__":
    main()