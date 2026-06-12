-- ==========================================
-- USER CONFIGURATION
-- ==========================================
-- Set the correct path for your system. 
-- If Python is in your system PATH, "python" is sufficient.
local PYTHON_EXE = "python" 
local SCRIPT_PATH = [[C:\Projekte\Coding\BirdNET_Reaper_Annotator\BirdNET_Reaper_Standalone.py]] 

-- Fallback Metadata (used if Item Notes are empty)
local DEFAULT_LAT = "45.5"
local DEFAULT_LON = "-73.6"
local DEFAULT_KW = "24"

-- Algorithm Parameters
local THRESHOLD = "0.3"
local MERGE_GAP = "6.0"
-- ==========================================

function main()
    -- 1. Check if an audio item is selected in Reaper
    local item = reaper.GetSelectedMediaItem(0, 0)
    if not item then
        reaper.ShowMessageBox("Please select an audio item first.", "Error", 0)
        return
    end

    -- 2. Dynamically determine the current Reaper project directory
    local proj_dir = reaper.GetProjectPath("")
    if proj_dir == "" then
        reaper.ShowMessageBox("Please save your Reaper project before running the analysis.\nThe script needs a project folder to store the results.", "Project Not Saved", 0)
        return
    end

    -- 3. Create the "BirdNet Analysis" subfolder inside the project directory
    local separator = package.config:sub(1,1)
    local OUT_DIR = proj_dir .. separator .. "BirdNet Analysis" .. separator
    reaper.RecursiveCreateDirectory(OUT_DIR, 0)

    -- 4. Extract item position on the timeline to use as the time offset
    local item_pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION")

    -- 5. Extract the active take and its source file path
    local take = reaper.GetActiveTake(item)
    if not take then return end
    local source = reaper.GetMediaItemTake_Source(take)
    local filepath = reaper.GetMediaSourceFileName(source, "")
    
    if filepath == "" then
        reaper.ShowMessageBox("Selected item does not have a valid source file.", "Error", 0)
        return
    end

    -- 6. Extract base filename to construct the path for the upcoming CSV file
    local base_name = filepath:match("^.+[/\\](.-)%.[^%.]+$")
    local csv_path = OUT_DIR .. base_name .. "_BIRDNET_Reaper_Regions.csv"

    -- 7. READ ITEM NOTES (The Hybrid Logic)
    local retval, notes = reaper.GetSetMediaItemInfo_String(item, "P_NOTES", "", false)
    local lat = notes:match("LAT:([%d%.%-]+)")
    local lon = notes:match("LON:([%d%.%-]+)")
    local kw = notes:match("KW:(%d+)")

    -- If any metadata is missing, fallback to the native Reaper GUI dialog
    if not (lat and lon and kw) then
        local current_lat = lat or DEFAULT_LAT
        local current_lon = lon or DEFAULT_LON
        local current_kw = kw or DEFAULT_KW
        local default_csv = current_lat .. "," .. current_lon .. "," .. current_kw
        
        local dialog_ret, user_inputs_csv = reaper.GetUserInputs("BirdNET Metadata", 3, "Latitude:,Longitude:,Calendar Week (1-52):", default_csv)
        
        if not dialog_ret then 
            return 
        end
        
        lat, lon, kw = user_inputs_csv:match("([^,]+),([^,]+),([^,]+)")
    end

    -- 8. Construct the command line string to execute the Python CLI script
    local cmd = string.format('"%s" "%s" "%s" "%s" --offset %f --lat %s --lon %s --kw %s --thresh %s --gap %s', 
                              PYTHON_EXE, SCRIPT_PATH, filepath, OUT_DIR, item_pos, lat, lon, kw, THRESHOLD, MERGE_GAP)

    -- 9. Execute the Python script synchronously
    reaper.ShowConsoleMsg("--- BirdNET Analysis ---\n")
    reaper.ShowConsoleMsg("File: " .. base_name .. "\n")
    reaper.ShowConsoleMsg("Output Directory: " .. OUT_DIR .. "\n")
    reaper.ShowConsoleMsg("Position: " .. tostring(item_pos) .. "s | Lat: " .. lat .. " | Lon: " .. lon .. " | Week: " .. kw .. "\n")
    reaper.ShowConsoleMsg("Analyzing... Please wait. Reaper will be unresponsive during this process.\n")
    
    -- ExecProcess returns only one value containing the output string
    local py_output = reaper.ExecProcess(cmd, 0)
    if py_output then
        reaper.ShowConsoleMsg(py_output .. "\n")
    end

    -- 10. Parse the generated CSV file and draw regions onto the timeline
    local file = io.open(csv_path, "r")
    if file then
        file:read() -- Skip the CSV header line
        
        local region_count = 0
        reaper.Undo_BeginBlock()
        
        for line in file:lines() do
            local id, name, start_pos, end_pos, length, color = line:match("([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),(.*)")
            
            if name and start_pos and end_pos then
                reaper.AddProjectMarker2(0, true, tonumber(start_pos), tonumber(end_pos), name, -1, 0)
                region_count = region_count + 1
            end
        end
        
        file:close()
        reaper.Undo_EndBlock("Import BirdNET Regions", -1)
        reaper.UpdateTimeline()
        reaper.ShowConsoleMsg("Successfully added " .. tostring(region_count) .. " regions to the timeline.\n")
    else
        reaper.ShowConsoleMsg("Error: Could not read CSV file at " .. csv_path .. "\n")
        reaper.ShowMessageBox("Analysis failed or CSV not found. Check console for Python errors.", "Error", 0)
    end
end

main()
