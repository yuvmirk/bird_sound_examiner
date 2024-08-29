import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import sys

if getattr(sys, 'frozen', False):
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

import shutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import librosa
import numpy as np
import traceback
import soundfile as sf
import sounddevice as sd

class LoggingPrint:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "a")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

class BirdSoundApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Bird Sound Examiner")
        self.master.geometry("1000x800")
        self.master.configure(bg="#2C3E50")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()

        self.main_folder = ""
        self.current_species = tk.StringVar()
        self.current_file = ""
        self.files_to_examine = []

        self.filtered_species_folder = "filtered_species_files"
        self.noise_folder = "noise"
        self.false_positive_folder = "false_positive"
        self.progress_file = "filtered species - updated list.txt"
        self.max_seg_num = 500
        # logging
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.log_file = os.path.join(desktop_path, f'bird_sound_examiner_log_.txt')
        self.log_message("Application started")

        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Bird Sound Examiner", font=('Helvetica', 20, 'bold'), foreground="#ECF0F1", background="#2C3E50")
        title_label.pack(pady=(0, 20))

        # Guidance Panel
        guidance_frame = ttk.LabelFrame(main_frame, text="Instructions", padding="10 10 10 10")
        guidance_frame.pack(pady=10, fill=tk.X)

        guidance_text = (
            "1. Choose the main folder containing all species folders.\n"
            "2. Select the species you wish to work on from the dropdown.\n"
            "3. Click 'Start Examination' to begin.\n"
            "4. For each audio file:\n"
            "   - Press SPACE or Left-click to approve\n"
            "   - Press RIGHT ARROW or Right-click for noise\n"
            "   - Press LEFT ARROW or Middle-click for false positive\n"
            "5. You can select a new folder at any time using the 'Select Folder' button."
        )
        guidance_label = ttk.Label(guidance_frame, text=guidance_text, justify=tk.LEFT, wraplength=900, font=('Helvetica', 12))
        guidance_label.pack(pady=5)

        # Folder selection
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(pady=20, fill=tk.X)

        self.folder_button = ttk.Button(folder_frame, text="Select Folder", command=self.select_folder, style="RoundedButton.TButton")
        self.folder_button.pack(side=tk.LEFT)

        self.folder_label = ttk.Label(folder_frame, text="No folder selected", font=('Helvetica', 10, 'italic'))
        self.folder_label.pack(side=tk.LEFT, padx=10)

        # Species selection
        species_frame = ttk.Frame(main_frame)
        species_frame.pack(pady=10, fill=tk.X)

        ttk.Label(species_frame, text="Select Species:", font=('Helvetica', 11)).pack(side=tk.LEFT)
        self.species_dropdown = ttk.Combobox(species_frame, textvariable=self.current_species, state="readonly", font=('Helvetica', 10))
        self.species_dropdown.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        self.species_dropdown.bind("<<ComboboxSelected>>", self.on_species_selected)

        # Start button
        self.start_button = ttk.Button(main_frame, text="Start Examination", command=self.start_examination, style="RoundedAccent.TButton")
        self.start_button.pack(pady=20)

        # Spectrogram
        spec_frame = ttk.Frame(main_frame)
        spec_frame.pack(pady=10, expand=True, fill=tk.BOTH)

        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.fig.patch.set_facecolor('#2C3E50')
        self.ax.set_facecolor('#34495E')
        self.ax.tick_params(colors='#ECF0F1')
        for spine in self.ax.spines.values():
            spine.set_edgecolor('#ECF0F1')
        self.canvas = FigureCanvasTkAgg(self.fig, master=spec_frame)
        self.canvas.draw()
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(expand=True, fill=tk.BOTH)

        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=20, fill=tk.X)

        button_width = 25
        self.ok_button = ttk.Button(control_frame, text="Approve (Space)", command=self.approve_decision, style="RoundedApprove.TButton", width=button_width)
        self.ok_button.pack(side=tk.LEFT, padx=5, expand=True)

        self.noise_button = ttk.Button(control_frame, text="Noise (Right Arrow)", command=self.noise_decision, style="RoundedNoise.TButton", width=button_width)
        self.noise_button.pack(side=tk.LEFT, padx=5, expand=True)

        self.fp_button = ttk.Button(control_frame, text="False Positive (Left Arrow)", command=self.false_positive_decision, style="RoundedFalsePositive.TButton", width=button_width)
        self.fp_button.pack(side=tk.LEFT, padx=5, expand=True)

        # Bind keyboard shortcuts
        self.master.bind('<space>', self.approve_decision)
        self.master.bind('<Left>', self.false_positive_decision)
        self.master.bind('<Right>', self.noise_decision)
        self.canvas_widget.bind("<Button-1>", self.approve_decision)
        self.canvas_widget.bind("<Button-2>", self.false_positive_decision)
        self.canvas_widget.bind("<Button-3>", self.noise_decision)

    def approve_decision(self, event=None):
        self.process_decision("approve")

    def false_positive_decision(self, event=None):
        self.process_decision("false_positive")

    def noise_decision(self, event=None):
        self.process_decision("noise")

    def configure_styles(self):
        self.style.configure("TFrame", background="#2C3E50")
        self.style.configure("TLabel", background="#2C3E50", foreground="#ECF0F1", font=('Helvetica', 10))
        self.style.configure("TLabelframe", background="#2C3E50", foreground="#ECF0F1")
        self.style.configure("TLabelframe.Label", background="#2C3E50", foreground="#ECF0F1", font=('Helvetica', 12, 'bold'))

        # Custom button styles with rounded corners
        self.style.layout("RoundedButton.TButton", 
                         [('Button.padding', {'children': 
                             [('Button.label', {'side': 'left', 'expand': 1})],
                           'sticky': 'nswe'})])
        self.style.configure("RoundedButton.TButton", 
                             font=('Helvetica', 10),
                             background="#3498DB",
                             foreground="#ECF0F1",
                             padding=(10, 5),
                             borderwidth=0,
                             relief="flat")
        self.style.map("RoundedButton.TButton",
                       background=[('active', '#2980B9')],
                       relief=[('pressed', 'sunken')])

        self.style.configure("RoundedAccent.TButton", 
                             font=('Helvetica', 11, 'bold'),
                             background="#E74C3C",
                             foreground="#ECF0F1",
                             padding=(15, 10),
                             borderwidth=0,
                             relief="flat")
        self.style.map("RoundedAccent.TButton",
                       background=[('active', '#C0392B')],
                       relief=[('pressed', 'sunken')])

        # Decision button styles
        self.style.configure("RoundedApprove.TButton", 
                             background="#2ECC71",
                             foreground="#ECF0F1",
                             font=('Helvetica', 10, 'bold'),
                             relief="flat")
        self.style.map("RoundedApprove.TButton",
                       background=[('active', '#27AE60')])

        self.style.configure("RoundedNoise.TButton", 
                             background="#E74C3C",
                             foreground="#ECF0F1",
                             font=('Helvetica', 10, 'bold'),
                             relief="flat")
        self.style.map("RoundedNoise.TButton",
                       background=[('active', '#C0392B')])

        self.style.configure("RoundedFalsePositive.TButton", 
                             background="#F39C12",
                             foreground="#ECF0F1",
                             font=('Helvetica', 10, 'bold'),
                             relief="flat")
        self.style.map("RoundedFalsePositive.TButton",
                       background=[('active', '#D35400')])

        # Combobox style
        self.style.map('TCombobox', fieldbackground=[('readonly', '#34495E')])
        self.style.map('TCombobox', selectbackground=[('readonly', '#2C3E50')])
        self.style.map('TCombobox', selectforeground=[('readonly', '#ECF0F1')])
        self.style.map('TCombobox', foreground=[('readonly', '#ECF0F1')])
    
    def select_folder(self):
        new_folder = filedialog.askdirectory()
        if new_folder:
            self.main_folder = new_folder
            self.folder_label.config(text=self.main_folder)
            self.update_species_dropdown()
            self.reset_examination()

    def reset_examination(self):
        self.current_file = ""
        self.files_to_examine = []
        self.start_button.config(state=tk.NORMAL)
        self.ax.clear()
        self.canvas.draw()

    def update_species_dropdown(self):
        species = [f for f in os.listdir(self.main_folder) if os.path.isdir(os.path.join(self.main_folder, f))]
        self.species_dropdown['values'] = species
        if species:
            self.species_dropdown.set(species[0])

    def on_species_selected(self, event):
        self.start_button.config(state=tk.NORMAL)

    def start_examination(self):
        species_folder = os.path.normpath(os.path.join(self.main_folder, self.current_species.get()))
        self.log_message(f"Starting examination for species folder: {species_folder}")
        try:
            all_files = [f for f in os.listdir(species_folder) if f.lower().endswith(('.wav', '.mp3'))]
            self.log_message(f"All files found: {all_files}")
            self.files_to_examine = np.random.permutation(all_files).tolist()
            self.log_message(f"Files to examine (randomized): {self.files_to_examine}")
            if self.files_to_examine:
                self.start_button.config(state=tk.DISABLED)
                self.examine_next_file()
            else:
                self.log_message(f"No WAV or MP3 files found in the folder: {species_folder}")
                messagebox.showinfo("No Files", f"No WAV or MP3 files found in the folder:\n{species_folder}")
        except Exception as e:
            error_msg = f"Error accessing species folder:\n{species_folder}\n\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.log_message(error_msg)
            self.log_error(error_msg)

    def examine_next_file(self):
        self.log_message(f"Entering examine_next_file. Files to examine: {len(self.files_to_examine)}")
        if self.files_to_examine:
            self.current_file = os.path.normpath(os.path.join(self.main_folder, self.current_species.get(), self.files_to_examine.pop(0)))
            self.log_message(f"Examining file: {self.current_file}")
            try:
                if not os.path.exists(self.current_file):
                    raise FileNotFoundError(f"File not found: {self.current_file}")
                self.log_message(f"Attempting to load file: {self.current_file}")
                self.log_message(f"File exists: {os.path.exists(self.current_file)}")
                self.log_message(f"File size: {os.path.getsize(self.current_file)} bytes")
                with sf.SoundFile(self.current_file) as sound_file:
                    y = sound_file.read(dtype="float32")
                    sr = sound_file.samplerate

                duration = len(y) / sr
                if len(y) == 0:
                    self.log_message(f"Warning: Empty audio file: {self.current_file}")
                    self.examine_next_file()
                    return

                if duration != 3.0:
                    self.log_message(f"Skipping file {self.current_file} as it is not exactly 3 seconds long (actual duration: {duration:.2f} seconds)")
                    self.examine_next_file()
                    return

                self.load_and_play_audio(y, sr)
                self.display_spectrogram(y, sr)
            except Exception as e:
                error_msg = f"Error processing file {self.current_file}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                self.log_message(error_msg)
                self.log_error(error_msg)
                self.examine_next_file()
        else:
            self.log_message("No more files to examine. Entering completion block.")
            # Gather detailed information
            species_folder = os.path.join(self.main_folder, self.current_species.get())
            all_files = [f for f in os.listdir(species_folder) if f.lower().endswith(('.wav', '.mp3'))]
            subfolders = [f.name for f in os.scandir(species_folder) if f.is_dir()]

            detail_msg = f"""
            All files have been examined.

            Main folder: {self.main_folder}
            Current species folder: {species_folder}
            Number of subfolders: {len(subfolders)}
            Subfolders: {', '.join(subfolders)}
            Total audio files found: {len(all_files)}
            Files processed: {len(all_files) - len(self.files_to_examine)}

            Folder permissions:
            Read: {os.access(species_folder, os.R_OK)}
            Write: {os.access(species_folder, os.W_OK)}
            Execute: {os.access(species_folder, os.X_OK)}

            Path exists: {os.path.exists(species_folder)}
            Path is absolute: {os.path.isabs(species_folder)}
            """
            self.log_message(detail_msg)
            messagebox.showinfo("Examination Complete", detail_msg)
            self.update_progress_file()
            self.reset_examination()

    def load_and_play_audio(self, y, sr):
        try:
            sd.play(y, sr)
        except Exception as e:
            self.log_message(f"Error playing audio: {e}")
            messagebox.showwarning("Audio Playback Error", "Unable to play audio. The spectrogram will still be displayed.")

    def display_spectrogram(self, y, sr):
        self.ax.clear()
        S = np.abs(librosa.stft(y))
        librosa.display.specshow(librosa.amplitude_to_db(S, ref=np.max), y_axis='hz', x_axis='time', ax=self.ax, sr=sr, cmap='viridis')
        self.ax.set_title(os.path.basename(self.current_file), color='#ECF0F1')
        self.ax.set_xlabel('Time', color='#ECF0F1')
        self.ax.set_ylabel('Frequency', color='#ECF0F1')
        self.ax.tick_params(colors='#ECF0F1')
        self.canvas.draw()
    
    def process_decision(self, decision):
        self.log_message(f"Processing decision: {decision}")
        if not self.current_file:
            self.log_message("No current file to process")
            return
        try:
            if decision == "approve":
                target_folder = os.path.normpath(os.path.join(self.main_folder, self.filtered_species_folder, self.current_species.get()))
            elif decision == "noise":
                target_folder = os.path.normpath(os.path.join(self.main_folder, self.noise_folder))
            elif decision == "false_positive":
                target_folder = os.path.normpath(os.path.join(self.main_folder, self.false_positive_folder))
            else:
                self.log_message(f"Unknown decision: {decision}")
                return

            self.log_message(f"Target folder: {target_folder}")
            os.makedirs(target_folder, exist_ok=True)
            target_file = os.path.normpath(os.path.join(target_folder, os.path.basename(self.current_file)))
            self.log_message(f"Moving file from {self.current_file} to {target_file}")
            
            # Check if source file exists
            if not os.path.exists(self.current_file):
                raise FileNotFoundError(f"Source file not found: {self.current_file}")
            
            # Check if we have write permissions in the target folder
            if not os.access(os.path.dirname(target_file), os.W_OK):
                raise PermissionError(f"No write permission for target folder: {os.path.dirname(target_file)}")
            
            shutil.move(self.current_file, target_file)
            self.log_message(f"File successfully moved to: {target_file}")
            
            if decision == "approve":
                approved_files = len([f for f in os.listdir(target_folder) if f.lower().endswith(('.wav', '.mp3'))])
                if approved_files >= self.max_seg_num:
                    messagebox.showinfo("Process Complete", f"Reached {self.max_seg_num} approved files. Stopping examination.")
                    self.reset_examination()
                    return
            self.examine_next_file()
        except Exception as e:
            error_msg = f"Error processing decision for file:\n{self.current_file}\n\nError: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
            self.examine_next_file()

    def update_progress_file(self):
        progress_file_path = os.path.normpath(os.path.join(self.main_folder, self.progress_file))
        try:
            with open(progress_file_path, 'a') as f:
                f.write(f"{self.current_species.get()}\n")
        except Exception as e:
            self.log_message(f"Error updating progress file: {e}")
            messagebox.showerror("Error", f"Error updating progress file:\n{progress_file_path}\n\nError: {str(e)}")
    
    def log_error(self, error_msg):
        log_file_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'bird_sound_examiner_error_log.txt')
        with open(log_file_path, "a") as log_file:
            log_file.write(f"{error_msg}\n")
        self.log_message(f"Error logged to {log_file_path}")
        messagebox.showerror("Error", f"An error occurred. Error details:\n\n{error_msg}\n\nThis error has been logged to:\n{log_file_path}")
    def log_message(self, message):
        log_entry = f"{message}\n"
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)


root = tk.Tk()
app = BirdSoundApp(root)
root.mainloop()