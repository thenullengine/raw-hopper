"""
RAW_HOPPER - Configurable RAW Photo Ingest Tool for Capture One
A Tkinter-based GUI application for ingesting RAW photos into a Capture One file structure.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import shutil
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading

try:
    import exifread
    EXIF_AVAILABLE = True
except ImportError:
    EXIF_AVAILABLE = False

try:
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class HopperLogic:
    """Core logic for RAW photo ingestion."""

    DEFAULT_CONFIG = {
        'source_path': '',
        'destination_volume': '',
        'destination_volume_label': '',
        'template_path': '',
        'year_format': '%Y',
        'month_format': '%Y-%m_%B',
        'session_format': 'Session_{month_name}',
        'file_extensions': '.RAF, .JPG',
    }

    def __init__(self, config_path: str = 'raw_hopper_config.json'):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    config = self.DEFAULT_CONFIG.copy()
                    config.update(loaded)
                    return config
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.DEFAULT_CONFIG.copy()
        return self.DEFAULT_CONFIG.copy()

    def save_config(self) -> None:
        """Save configuration to JSON file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_drives(self) -> List[Tuple[str, str]]:
        """
        Get all available drives with their volume labels.
        Returns list of tuples: (drive_letter, volume_label)
        """
        if not WIN32_AVAILABLE:
            return [('C:\\', 'Local Drive')]

        drives = []
        try:
            for drive_letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                drive_path = f'{drive_letter}:\\'
                try:
                    volume_info = win32api.GetVolumeInformation(drive_path)
                    if volume_info[0]:
                        volume_label = volume_info[0]
                    else:
                        volume_label = f'Drive_{drive_letter}'
                    drives.append((drive_path, volume_label))
                except Exception:
                    continue
        except Exception as e:
            print(f"Error getting drives: {e}")

        return drives

    def resolve_volume_label_to_drive(self, volume_label: str) -> Optional[str]:
        """Resolve a volume label to its current drive letter."""
        drives = self.get_drives()
        for drive_path, label in drives:
            if label == volume_label:
                return drive_path
        return None

    def get_exif_date(self, file_path: str) -> Optional[datetime.datetime]:
        """Extract date from EXIF data."""
        if not EXIF_AVAILABLE:
            # Fallback to file modification time
            return datetime.datetime.fromtimestamp(os.path.getmtime(file_path))

        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, stop_tag='DateTimeOriginal')
                if 'EXIF DateTimeOriginal' in tags:
                    date_str = str(tags['EXIF DateTimeOriginal'])
                    dt = datetime.datetime.strptime(
                        date_str, '%Y:%m:%d %H:%M:%S'
                    )
                    return dt
        except Exception as e:
            print(f"Error reading EXIF from {file_path}: {e}")

        # Fallback to file modification time
        try:
            return datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        except Exception:
            return None

    def construct_path(self, date: datetime.datetime) -> Tuple[str, str, str]:
        """
        Construct year folder, month folder, and session name based on patterns.
        Returns: (year_folder, month_folder, session_name)
        """
        year_folder = date.strftime(self.config['year_format'])
        month_folder = date.strftime(self.config['month_format'])

        # For session format, replace {month_name} with full month name
        session_format = self.config['session_format']
        session_name = session_format.replace(
            '{month_name}', date.strftime('%B')
        )

        return year_folder, month_folder, session_name

    def get_file_extensions(self) -> List[str]:
        """Parse file extensions from config."""
        ext_string = self.config['file_extensions']
        extensions = [ext.strip().upper() for ext in ext_string.split(',')]
        return extensions

    def should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed based on extension."""
        ext = os.path.splitext(file_path)[1].upper()
        return ext in self.get_file_extensions()

    def find_or_create_session(self, destination_root: str, year_folder: str,
                               month_folder: str,
                               session_name: str) -> str:
        """
        Find or create a Capture One session folder.
        Returns the path to the session folder.
        """
        session_path = os.path.join(
            destination_root, year_folder, month_folder, session_name
        )
        capture_path = os.path.join(session_path, 'Capture')
        session_db = os.path.join(session_path, f'{session_name}.cosessiondb')

        # If session already exists, return it
        if os.path.exists(session_db):
            if not os.path.exists(capture_path):
                os.makedirs(capture_path, exist_ok=True)
            return session_path

        # Need to create from template
        template_path = self.config['template_path']
        if not template_path or not os.path.exists(template_path):
            # Create basic structure without template
            os.makedirs(capture_path, exist_ok=True)
            # Create empty session DB (placeholder)
            Path(session_db).touch()
            return session_path

        # Copy template
        try:
            # Create parent directories
            os.makedirs(os.path.dirname(session_path), exist_ok=True)

            # Copy template folder
            shutil.copytree(template_path, session_path)

            # Find and rename .cosessiondb file
            for item in os.listdir(session_path):
                if item.endswith('.cosessiondb'):
                    old_db = os.path.join(session_path, item)
                    new_db = session_db
                    os.rename(old_db, new_db)
                    break

            # Ensure Capture folder exists
            if not os.path.exists(capture_path):
                os.makedirs(capture_path, exist_ok=True)

            return session_path
        except Exception as e:
            print(f"Error creating session from template: {e}")
            # Fallback to basic structure
            os.makedirs(capture_path, exist_ok=True)
            Path(session_db).touch()
            return session_path

    def ingest_files(self, log_callback=None,
                     progress_callback=None) -> Tuple[int, int, List[str]]:
        """
        Main ingestion logic.
        Returns: (success_count, fail_count, error_messages)
        """
        source_path = self.config['source_path']
        volume_label = self.config['destination_volume_label']

        errors = []
        success_count = 0
        fail_count = 0

        # Validate source
        if not source_path or not os.path.exists(source_path):
            errors.append("Source path is invalid or does not exist")
            return success_count, fail_count, errors

        # Resolve destination drive
        destination_drive = self.resolve_volume_label_to_drive(volume_label)
        if not destination_drive:
            msg = f"Could not resolve volume label '{volume_label}' to a drive"
            errors.append(msg)
            return success_count, fail_count, errors

        if log_callback:
            log_callback(f"Source: {source_path}")
            log_callback(
                f"Destination: {destination_drive} (Volume: {volume_label})"
            )

        # Get all files to process
        files_to_process = []
        for root, dirs, files in os.walk(source_path):
            for file in files:
                file_path = os.path.join(root, file)
                if self.should_process_file(file_path):
                    files_to_process.append(file_path)

        total_files = len(files_to_process)
        if log_callback:
            log_callback(f"Found {total_files} files to process")

        # Process each file
        for idx, file_path in enumerate(files_to_process):
            try:
                # Get date from EXIF
                date = self.get_exif_date(file_path)
                if not date:
                    raise Exception("Could not determine file date")

                # Construct destination path
                year_folder, month_folder, session_name = (
                    self.construct_path(date)
                )

                # Find or create session
                session_path = self.find_or_create_session(
                    destination_drive, year_folder, month_folder, session_name
                )

                # Check if session creation was successful
                if not session_path:
                    raise Exception("Failed to create session folder")

                # Move file to Capture folder
                capture_folder = os.path.join(session_path, 'Capture')
                dest_file = os.path.join(
                    capture_folder, os.path.basename(file_path)
                )

                # Handle duplicate filenames
                if os.path.exists(dest_file):
                    base, ext = os.path.splitext(os.path.basename(file_path))
                    counter = 1
                    max_attempts = 10000  # Prevent infinite loop
                    while os.path.exists(dest_file) and counter < max_attempts:
                        dest_file = os.path.join(
                            capture_folder, f'{base}_{counter}{ext}'
                        )
                        counter += 1
                    if counter >= max_attempts:
                        raise Exception("Too many duplicate filenames")

                shutil.move(file_path, dest_file)
                success_count += 1

                if log_callback:
                    basename = os.path.basename(file_path)
                    log_callback(
                        f"✓ Moved: {basename} -> {session_name}/Capture"
                    )

            except Exception as e:
                fail_count += 1
                basename = os.path.basename(file_path)
                error_msg = f"✗ Failed: {basename} - {str(e)}"
                errors.append(error_msg)
                if log_callback:
                    log_callback(error_msg)

            # Update progress
            if progress_callback:
                progress = ((idx + 1) / total_files) * 100
                progress_callback(progress)

        return success_count, fail_count, errors


class HopperUI:
    """Tkinter GUI for RAW_HOPPER."""

    def __init__(self, root: tk.Tk, logic: HopperLogic):
        self.root = root
        self.logic = logic
        self.root.title("RAW_HOPPER v1.0")
        self.root.geometry("800x600")

        # Create notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # Create tabs
        self.ingest_tab = ttk.Frame(self.notebook)
        self.config_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.ingest_tab, text="INGEST")
        self.notebook.add(self.config_tab, text="CONFIG")

        # Build tab contents
        self.build_ingest_tab()
        self.build_config_tab()

        # Load saved config into UI
        self.load_config_to_ui()

    def build_ingest_tab(self):
        """Build the INGEST tab."""
        # Drop zone style area
        drop_frame = ttk.LabelFrame(
            self.ingest_tab, text="Source Folder", padding=20
        )
        drop_frame.pack(fill='both', expand=True, padx=10, pady=10)

        self.source_label = ttk.Label(
            drop_frame, text="No source selected",
            font=('Arial', 12), anchor='center',
            relief='sunken', padding=40
        )
        self.source_label.pack(fill='both', expand=True)

        browse_btn = ttk.Button(
            drop_frame, text="Browse Source Folder",
            command=self.browse_source
        )
        browse_btn.pack(pady=5)

        # Progress bar
        progress_frame = ttk.Frame(self.ingest_tab)
        progress_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(progress_frame, text="Progress:").pack(side='left', padx=5)
        self.progress_bar = ttk.Progressbar(
            progress_frame, mode='determinate', length=400
        )
        self.progress_bar.pack(side='left', fill='x', expand=True, padx=5)

        # Log window
        log_frame = ttk.LabelFrame(self.ingest_tab, text="Log", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # Scrollbar for log
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side='right', fill='y')

        self.log_text = tk.Text(
            log_frame, height=10, yscrollcommand=log_scroll.set,
            wrap='word', state='disabled'
        )
        self.log_text.pack(fill='both', expand=True)
        log_scroll.config(command=self.log_text.yview)

        # Run button
        self.run_btn = ttk.Button(
            self.ingest_tab, text="RUN HOPPER",
            command=self.run_hopper, style='Accent.TButton'
        )
        self.run_btn.pack(pady=10)

    def build_config_tab(self):
        """Build the CONFIG tab."""
        # Scrollable frame for config
        canvas = tk.Canvas(self.config_tab)
        scrollbar = ttk.Scrollbar(
            self.config_tab, orient="vertical", command=canvas.yview
        )
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Drive selection
        drive_frame = ttk.LabelFrame(
            scrollable_frame, text="Destination Drive", padding=10
        )
        drive_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(drive_frame, text="Volume Label:").grid(
            row=0, column=0, sticky='w', pady=5
        )
        self.volume_var = tk.StringVar()
        self.volume_combo = ttk.Combobox(
            drive_frame, textvariable=self.volume_var,
            width=40, state='readonly'
        )
        self.volume_combo.grid(row=0, column=1, padx=5, pady=5)

        refresh_btn = ttk.Button(
            drive_frame, text="Refresh Drives",
            command=self.refresh_drives
        )
        refresh_btn.grid(row=0, column=2, padx=5, pady=5)

        # Template path
        template_frame = ttk.LabelFrame(
            scrollable_frame, text="Capture One Template", padding=10
        )
        template_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(template_frame, text="Template Folder:").grid(
            row=0, column=0, sticky='w', pady=5
        )
        self.template_var = tk.StringVar()
        template_entry = ttk.Entry(
            template_frame, textvariable=self.template_var, width=50
        )
        template_entry.grid(row=0, column=1, padx=5, pady=5)

        template_btn = ttk.Button(
            template_frame, text="Browse",
            command=self.browse_template
        )
        template_btn.grid(row=0, column=2, padx=5, pady=5)

        # Naming patterns
        pattern_frame = ttk.LabelFrame(
            scrollable_frame, text="Folder Naming Patterns", padding=10
        )
        pattern_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(pattern_frame, text="Year Folder Format:").grid(
            row=0, column=0, sticky='w', pady=5
        )
        self.year_format_var = tk.StringVar(value='%Y')
        ttk.Entry(
            pattern_frame, textvariable=self.year_format_var, width=30
        ).grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(pattern_frame, text="(e.g., %Y = 2024)").grid(
            row=0, column=2, sticky='w', pady=5
        )

        ttk.Label(pattern_frame, text="Month Folder Format:").grid(
            row=1, column=0, sticky='w', pady=5
        )
        self.month_format_var = tk.StringVar(value='%Y-%m_%B')
        ttk.Entry(
            pattern_frame, textvariable=self.month_format_var, width=30
        ).grid(row=1, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(pattern_frame, text="(e.g., 2024-01_January)").grid(
            row=1, column=2, sticky='w', pady=5
        )

        ttk.Label(pattern_frame, text="Session Name Format:").grid(
            row=2, column=0, sticky='w', pady=5
        )
        self.session_format_var = tk.StringVar(value='Session_{month_name}')
        ttk.Entry(
            pattern_frame, textvariable=self.session_format_var, width=30
        ).grid(row=2, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(pattern_frame, text="(use {month_name} for month)").grid(
            row=2, column=2, sticky='w', pady=5
        )

        # File extensions
        ext_frame = ttk.LabelFrame(
            scrollable_frame, text="File Extensions", padding=10
        )
        ext_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(ext_frame, text="Extensions (comma-separated):").grid(
            row=0, column=0, sticky='w', pady=5
        )
        self.extensions_var = tk.StringVar(value='.RAF, .JPG')
        ttk.Entry(
            ext_frame, textvariable=self.extensions_var, width=50
        ).grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # Save button
        save_btn = ttk.Button(
            scrollable_frame, text="Save Configuration",
            command=self.save_config_from_ui
        )
        save_btn.pack(pady=10)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Initial drive refresh
        self.refresh_drives()

    def browse_source(self):
        """Browse for source folder."""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.logic.config['source_path'] = folder
            self.source_label.config(text=folder)
            self.logic.save_config()

    def browse_template(self):
        """Browse for template folder."""
        title = "Select Capture One Template Folder"
        folder = filedialog.askdirectory(title=title)
        if folder:
            self.template_var.set(folder)

    def refresh_drives(self):
        """Refresh the list of available drives."""
        drives = self.logic.get_drives()
        volume_labels = [label for _, label in drives]
        self.volume_combo['values'] = volume_labels

        # Set current selection if saved
        saved_label = self.logic.config.get('destination_volume_label', '')
        if saved_label in volume_labels:
            self.volume_var.set(saved_label)
        elif volume_labels:
            self.volume_var.set(volume_labels[0])

    def load_config_to_ui(self):
        """Load saved configuration into UI elements."""
        config = self.logic.config

        # Source path
        if config.get('source_path'):
            self.source_label.config(text=config['source_path'])

        # Template path
        self.template_var.set(config.get('template_path', ''))

        # Patterns
        self.year_format_var.set(config.get('year_format', '%Y'))
        self.month_format_var.set(config.get('month_format', '%Y-%m_%B'))
        session_format = config.get('session_format', 'Session_{month_name}')
        self.session_format_var.set(session_format)

        # Extensions
        self.extensions_var.set(config.get('file_extensions', '.RAF, .JPG'))

    def save_config_from_ui(self):
        """Save configuration from UI to config file."""
        self.logic.config['destination_volume_label'] = self.volume_var.get()
        self.logic.config['template_path'] = self.template_var.get()
        self.logic.config['year_format'] = self.year_format_var.get()
        self.logic.config['month_format'] = self.month_format_var.get()
        self.logic.config['session_format'] = self.session_format_var.get()
        self.logic.config['file_extensions'] = self.extensions_var.get()

        self.logic.save_config()
        messagebox.showinfo("Success", "Configuration saved successfully!")

    def log(self, message: str):
        """Add message to log window."""
        self.log_text.config(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.config(state='disabled')
        self.root.update_idletasks()

    def update_progress(self, value: float):
        """Update progress bar."""
        self.progress_bar['value'] = value
        self.root.update_idletasks()

    def run_hopper(self):
        """Execute the ingestion process."""
        # Save current config
        self.save_config_from_ui()

        # Clear log
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, 'end')
        self.log_text.config(state='disabled')

        # Reset progress
        self.progress_bar['value'] = 0

        # Disable run button
        self.run_btn.config(state='disabled')

        # Run in thread to keep UI responsive
        def run_thread():
            try:
                self.log("Starting ingestion...")
                success, fail, errors = self.logic.ingest_files(
                    log_callback=self.log,
                    progress_callback=self.update_progress
                )

                self.log("\n" + "="*50)
                self.log("Ingestion complete!")
                self.log(f"Success: {success} files")
                self.log(f"Failed: {fail} files")

                if fail == 0:
                    msg = f"Successfully processed {success} files!"
                    messagebox.showinfo("Complete", msg)
                else:
                    msg = (
                        f"Processed {success} files, {fail} failed. "
                        "Check log for details."
                    )
                    messagebox.showwarning("Complete with errors", msg)
            except Exception as e:
                self.log(f"\nERROR: {str(e)}")
                messagebox.showerror("Error", f"Ingestion failed: {str(e)}")
            finally:
                self.run_btn.config(state='normal')

        # Use daemon thread so app can close cleanly
        # File operations (shutil.move) are atomic and won't corrupt
        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()


def main():
    """Main entry point."""
    root = tk.Tk()
    logic = HopperLogic()
    HopperUI(root, logic)
    root.mainloop()


if __name__ == '__main__':
    main()
