# RAW_HOPPER

A configurable Tkinter-based GUI application for ingesting RAW photos into a Capture One file structure.

## Features

- **Dynamic Volume Detection**: Detects all connected drives by volume label, resolving drive letters at runtime (Windows-friendly)
- **User-Configurable Patterns**: Define folder hierarchy using Python strftime tokens
- **EXIF Date Parsing**: Automatically organizes photos by capture date
- **Capture One Integration**: Copies template sessions and manages .cosessiondb files
- **Persistent Configuration**: All settings saved to JSON file
- **Two-Tab Interface**:
  - **INGEST**: Drop zone, progress tracking, and log viewer
  - **CONFIG**: Drive selection, naming patterns, and file extension filters

## Installation

1. Clone the repository:
```bash
git clone https://github.com/thenullengine/raw-hopper.git
cd raw-hopper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: On Windows, `pywin32` is required for volume label detection. On other platforms, it will gracefully fall back to basic functionality.

## Usage

Run the application:
```bash
python raw_hopper.py
```

### Configuration Tab

1. **Refresh Drives**: Click to populate the dropdown with connected drives by volume label
2. **Select Destination Drive**: Choose the destination volume (e.g., "Samsung_T7")
3. **Template Folder**: (Optional) Browse to a Capture One session template folder
4. **Folder Naming Patterns**:
   - Year Folder Format: Default `%Y` (e.g., 2024)
   - Month Folder Format: Default `%Y-%m_%B` (e.g., 2024-01_January)
   - Session Name Format: Default `Session_{month_name}` (use `{month_name}` placeholder)
5. **File Extensions**: Comma-separated list (e.g., `.RAF, .JPG`)
6. Click **Save Configuration**

### Ingest Tab

1. Click **Browse Source Folder** to select the folder containing RAW files
2. Click **RUN HOPPER** to start the ingestion process
3. Monitor progress in the log window

## File Structure

The application creates the following structure:

```
[Destination Drive]/
├── [Year]/              (e.g., 2024)
│   └── [Month]/         (e.g., 2024-01_January)
│       └── [Session]/   (e.g., Session_January)
│           ├── Capture/ (RAW files moved here)
│           └── Session_January.cosessiondb
```

## Configuration File

All settings are saved to `raw_hopper_config.json` in the application directory.

## Dependencies

- `tkinter` (included with Python)
- `exifread` - EXIF data extraction
- `pywin32` - Windows drive detection (Windows only)

## Requirements

- Python 3.7+
- Windows (for full drive detection features) or Linux/macOS (basic functionality)

## License

See LICENSE.md for details.
