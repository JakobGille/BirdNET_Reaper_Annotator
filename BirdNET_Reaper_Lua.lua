-- ==========================================
-- USER CONFIGURATION
-- ==========================================
-- Set the correct path for your system. 
local PYTHON_EXE = "python" 
local SCRIPT_PATH = [[C:\Projekte\Coding\BirdNET_Reaper_Annotator\AvianTag_CLI.py]] 

-- Fallback Metadata (used if Item Notes are empty)
local DEFAULT_LAT = "45.5"
local DEFAULT_LON = "-73.6"
local DEFAULT_KW = "23"

-- Algorithm Parameters
local THRESHOLD = "0.5"
local MERGE_GAP = "3.0"
-- ==========================================

function main()
    -- 1. Check if any items are selected
    local num_selected = reaper.CountSelectedMediaItems(0)
    if num_selected == 0 then
        reaper.ShowMessageBox("Please select at least one audio item.", "Error", 0)
        return
    end

    -- 2. Dynamically determine the current Reaper project directory
    local proj_dir = reaper.GetProjectPath("")
    if proj_dir == "" then
        reaper.ShowMessageBox("Please save your Reaper project before running the analysis.", "Project Not Saved", 0)
        return
    end

    -- 3. Create the "BirdNet Analysis" subfolder
    local separator = package.config:sub(1,1)
    local OUT_DIR = proj_dir .. separator .. "BirdNet Analysis"
    reaper.RecursiveCreateDirectory(OUT_DIR, 0)

    -- 4. METADATA LOGIC: Check the FIRST selected item or prompt GUI ONCE
    local first_item = reaper.GetSelectedMediaItem(0, 0)
    local retval, notes = reaper.GetSetMediaItemInfo_String(first_item, "P_NOTES", "", false)
    local lat = notes:match("LAT:([%d%.%-]+)")
    local lon = notes:match("LON:([%d%.%-]+)")
    local kw = notes:match("KW:(%d+)")

    if not (lat and lon and kw) then
        local default_csv = (lat or DEFAULT_LAT) .. "," .. (lon or DEFAULT_LON) .. "," .. (kw or DEFAULT_KW)
        local dialog_ret, user_inputs_csv = reaper.GetUserInputs("BirdNET Batch Metadata", 3, "Latitude:,Longitude:,Calendar Week (1-52):", default_csv)
        
        if not dialog_ret then return end
        lat, lon, kw = user_inputs_csv:match("([^,]+),([^,]+),([^,]+)")
    end

    -- Prepare UI for batch processing
    reaper.Undo_BeginBlock()
    reaper.ShowConsoleMsg("--- BirdNET Batch Analysis Started ---\n")
    reaper.ShowConsoleMsg("Processing " .. num_selected .. " item(s). Reaper will be unresponsive.\n\n")

    local total_regions_added = 0

    -- 5. BATCH PROCESSING LOOP
    for i = 0, num_selected - 1 do
        local item = reaper.GetSelectedMediaItem(0, i)
        local item_pos = reaper.GetMediaItemInfo_Value(item, "D_POSITION")

        local take = reaper.GetActiveTake(item)
        if take then
            local source = reaper.GetMediaItemTake_Source(take)
            local filepath = reaper.GetMediaSourceFileName(source, "")
            
            if filepath ~= "" then
                local base_name = filepath:match("^.+[/\\](.-)%.[^%.]+$")
                local csv_path = OUT_DIR .. separator .. base_name .. "_BIRDNET_Reaper_Regions.csv"

                -- Construct the Python CLI command
                local cmd = string.format('"%s" "%s" "%s" "%s" --offset %f --lat %s --lon %s --kw %s --thresh %s --gap %s', 
                                          PYTHON_EXE, SCRIPT_PATH, filepath, OUT_DIR, item_pos, lat, lon, kw, THRESHOLD, MERGE_GAP)

                reaper.ShowConsoleMsg("Analyzing [" .. (i+1) .. "/" .. num_selected .. "]: " .. base_name .. "\n")
                
                -- Execute Python synchronously
                local py_output = reaper.ExecProcess(cmd, 0)
                if py_output then
                    reaper.ShowConsoleMsg(py_output .. "\n")
                end

                -- Read CSV and draw regions
                local file = io.open(csv_path, "r")
                if file then
                    file:read() -- Skip header
                    
                    for line in file:lines() do
                        local id, name, start_pos, end_pos, length, color = line:match("([^,]+),([^,]+),([^,]+),([^,]+),([^,]+),(.*)")
                        if name and start_pos and end_pos then
                            reaper.AddProjectMarker2(0, true, tonumber(start_pos), tonumber(end_pos), name, -1, 0)
                            total_regions_added = total_regions_added + 1
                        end
                    end
                    file:close()
                else
                    reaper.ShowConsoleMsg("Error: Could not read CSV file for " .. base_name .. "\n")
                end
            end
        end
    end

    -- Finalize Batch
    reaper.Undo_EndBlock("Import BirdNET Regions (Batch)", -1)
    reaper.UpdateTimeline()
    reaper.ShowConsoleMsg("\n--- Analysis Complete ---\n")
    reaper.ShowConsoleMsg("Successfully added " .. total_regions_added .. " regions total.\n")
end

main()