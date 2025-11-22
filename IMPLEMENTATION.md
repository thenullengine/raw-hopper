# RAW_HOPPER Implementation Summary

## Overview
RAW_HOPPER is a Python Tkinter GUI application designed for photographers to ingest RAW photos into a Capture One file structure. The application provides a user-friendly interface with configurable settings for folder organization and file management.

## Architecture

### Core Components

#### 1. HopperLogic Class
**Purpose:** Handles all business logic for file ingestion, path management, and configuration.

**Key Features:**
- Configuration persistence using JSON
- Dynamic drive detection with volume label resolution (Windows-specific via win32api)
- EXIF date extraction from photos (with fallback to file modification time)
- Path construction based on user-defined strftime patterns
- Capture One session folder management
- File filtering by extension

**Methods:**
- `load_config()` / `save_config()`: Configuration persistence
- `get_drives()`: Enumerates drives with volume labels
- `resolve_volume_label_to_drive()`: Resolves saved labels to current drive letters
- `get_exif_date()`: Extracts date from photo EXIF data
- `construct_path()`: Builds folder structure based on patterns
- `find_or_create_session()`: Manages Capture One session folders
- `ingest_files()`: Main ingestion pipeline

#### 2. HopperUI Class
**Purpose:** Provides the Tkinter-based user interface.

**Structure:**
- Two-tab notebook interface using ttk.Notebook
- Tab 1 (INGEST): File drop zone, progress bar, scrolling log, run button
- Tab 2 (CONFIG): All settings and configuration options

**UI Elements:**
- Source folder browser
- Destination drive selector (by volume label)
- Template folder browser
- Naming pattern inputs (year, month, session)
- File extension filter
- Real-time log output with progress tracking

## Key Features

### 1. Dynamic Volume Detection ("The Windows Fix")
**Problem:** Drive letters change between systems/sessions
**Solution:** Store volume labels (e.g., "Samsung_T7") instead of drive letters

**Implementation:**
```python
def get_drives(self) -> List[Tuple[str, str]]:
    # Returns [(drive_path, volume_label), ...]
    # Uses win32api.GetVolumeInformation() on Windows
```

**Runtime:** At ingestion, resolve label to current drive letter

### 2. User-Configurable Patterns
Users can define folder hierarchy using Python strftime tokens:
- Year Format: `%Y` → "2024"
- Month Format: `%Y-%m_%B` → "2024-03_March"
- Session Format: `Session_{month_name}` → "Session_March"

Special token `{month_name}` is replaced with the full month name.

### 3. Capture One Session Management
**Workflow:**
1. Check if session folder exists (by .cosessiondb file)
2. If missing:
   - Copy user's template folder (if provided)
   - Find and rename .cosessiondb file to match session name
   - Create basic structure if no template available
3. Ensure Capture subfolder exists
4. Move files into Capture folder

### 4. Configuration Persistence
All settings stored in `raw_hopper_config.json`:
```json
{
    "source_path": "/path/to/source",
    "destination_volume_label": "Samsung_T7",
    "template_path": "/path/to/template",
    "year_format": "%Y",
    "month_format": "%Y-%m_%B",
    "session_format": "Session_{month_name}",
    "file_extensions": ".RAF, .JPG"
}
```

## File Organization

Created folder structure:
```
[Destination Drive]/
├── 2024/                    (Year: user-defined format)
│   └── 2024-03_March/       (Month: user-defined format)
│       └── Session_March/   (Session: user-defined format)
│           ├── Capture/     (RAW files moved here)
│           │   ├── photo1.RAF
│           │   └── photo2.JPG
│           └── Session_March.cosessiondb
```

## Error Handling

### Implemented Safeguards:
1. **Null Checks:** Validates paths before operations
2. **Duplicate Handling:** Adds counter suffix (`file_1.RAF`, `file_2.RAF`, etc.)
3. **Max Attempts:** Limits duplicate counter to 10,000 to prevent infinite loops
4. **Exception Handling:** Catches and logs errors per file, continues processing
5. **Fallback Logic:** Creates basic session structure if template copy fails

### Thread Safety:
- Uses daemon threads for non-blocking GUI
- File operations (shutil.move) are atomic
- Progress callbacks update UI safely via update_idletasks()

## Testing

### test_logic.py
Unit tests for core logic without GUI dependencies:
- Configuration persistence
- Path construction
- File extension filtering

**Mock Strategy:**
- Mocks tkinter module when unavailable
- Uses TemporaryDirectory for clean test isolation
- All tests passing (3/3)

## Code Quality

### Standards Compliance:
- ✅ PEP8 compliant (verified with flake8, 100-char line limit)
- ✅ Type hints for method signatures
- ✅ Docstrings for all classes and methods
- ✅ Clean separation of concerns (Logic/UI)
- ✅ No security vulnerabilities (CodeQL scan: 0 alerts)

### Code Reviews:
- 2 rounds of automated code review
- All feedback addressed:
  - Added null checks
  - Fixed potential infinite loops
  - Improved thread handling
  - Better type annotations
  - Enhanced test mocking

## Dependencies

### Required:
- Python 3.7+
- tkinter (standard library)

### Optional:
- **exifread**: For EXIF date extraction (graceful fallback to file mtime)
- **pywin32**: For Windows drive detection (Linux/macOS: uses fallback)

## Usage

### Installation:
```bash
pip install -r requirements.txt
```

### Running:
```bash
python raw_hopper.py
```

### Workflow:
1. Open CONFIG tab
2. Click "Refresh Drives" to populate drive list
3. Select destination drive by volume label
4. (Optional) Set template folder path
5. Configure naming patterns
6. Set file extensions to process
7. Click "Save Configuration"
8. Switch to INGEST tab
9. Browse to source folder
10. Click "RUN HOPPER"
11. Monitor progress in log window

## Future Enhancements (Not Implemented)

Possible improvements:
- Drag-and-drop support for source folder
- File preview before ingestion
- Batch operations with multiple sources
- Integration with Capture One API
- Custom session metadata
- Network drive support improvements
- Undo/rollback functionality

## Performance Characteristics

- **File Processing:** Sequential (one file at a time)
- **UI Responsiveness:** Maintained via threading
- **Memory Usage:** Minimal (processes one file at a time)
- **Disk I/O:** Uses shutil.move (atomic, efficient)

## Platform Support

- **Windows:** Full support (drive detection via pywin32)
- **Linux/macOS:** Basic support (limited drive detection)
- **GUI:** Requires desktop environment with tkinter

## Window Title
As specified: **"RAW_HOPPER v1.0"**

---

**Implementation Date:** November 22, 2025  
**Status:** Complete and Reviewed  
**Test Status:** All Passing  
**Security:** No Vulnerabilities
