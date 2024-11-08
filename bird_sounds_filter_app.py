import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
import os
import sys

if getattr(sys, 'frozen', False):
    os.environ['PATH'] = sys._MEIPASS + os.pathsep + os.environ['PATH']

import shutil
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import librosa
import numpy as np
import traceback
import soundfile as sf
import sounddevice as sd
import tempfile


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
        self.approved_count = tk.IntVar(value=0)

        # logging
        temp_dir = tempfile.gettempdir()
        self.log_file = os.path.join(temp_dir, 'bird_sound_examiner_log.txt')
        try:
            with open(self.log_file, 'a') as f:
                f.write("Application started\n")
        except Exception as e:
            print(f"Warning: Unable to create or write to log file. Error: {e}")
            self.log_file = None
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
            "3. Set the maximum files threshold if needed.\n"
            "4. Click 'Start Examination' to begin.\n"
            "5. For each audio file, you have three ways to make a decision:\n"
            "   - True Positive: Press SPACE, Left-click, or 'True Positive' button\n"
            "   - Noise: Press RIGHT ARROW, Right-click, or 'Noise' button\n"
            "   - False Positive: Press LEFT ARROW, Middle-click, or 'False Positive' button\n"
            "   - Use 'Play Again' button to replay the current audio"
        )
        guidance_label = ttk.Label(guidance_frame, text=guidance_text, justify=tk.LEFT, wraplength=900, font=('Helvetica', 12))
        guidance_label.pack(pady=5)

        # Folder selection
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(pady=10, fill=tk.X)

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

        # Set Max Files Threshold button
        threshold_frame = ttk.Frame(main_frame)
        threshold_frame.pack(pady=10, fill=tk.X)

        self.set_threshold_button = ttk.Button(threshold_frame, text="Set Max Files Threshold", command=self.set_max_files_threshold, style="RoundedButton.TButton")
        self.set_threshold_button.pack(side=tk.LEFT)

        self.threshold_label = ttk.Label(threshold_frame, text=f"Max Files: {self.max_seg_num}", font=('Helvetica', 10, 'italic'))
        self.threshold_label.pack(side=tk.LEFT, padx=10)

        # Start button
        self.start_button = ttk.Button(main_frame, text="Start Examination", command=self.start_examination, style="RoundedAccent.TButton")
        self.start_button.pack(pady=20)

        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=10, fill=tk.X)

        button_width = 20
        self.play_again_button = ttk.Button(control_frame, text="Play Again", command=self.play_again, style="RoundedPlayAgain.TButton", width=button_width)
        self.play_again_button.pack(side=tk.LEFT, padx=5)

        self.ok_button = ttk.Button(control_frame, text="True Positive", command=self.approve_decision, style="RoundedApprove.TButton", width=button_width)
        self.ok_button.pack(side=tk.LEFT, padx=5)

        self.noise_button = ttk.Button(control_frame, text="Noise", command=self.noise_decision, style="RoundedNoise.TButton", width=button_width)
        self.noise_button.pack(side=tk.LEFT, padx=5)

        self.fp_button = ttk.Button(control_frame, text="False Positive", command=self.false_positive_decision, style="RoundedFalsePositive.TButton", width=button_width)
        self.fp_button.pack(side=tk.LEFT, padx=5)

        # Approved count
        self.approved_count_label = ttk.Label(control_frame, text="Approved Files: 0", font=('Helvetica', 12, 'bold'))
        self.approved_count_label.pack(side=tk.RIGHT, padx=20)

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

        self.style.configure("RoundedPlayAgain.TButton", 
                             background="#3498DB",
                             foreground="#ECF0F1",
                             font=('Helvetica', 10, 'bold'),
                             relief="flat")
        self.style.map("RoundedPlayAgain.TButton",
                       background=[('active', '#2980B9')])

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
            self.update_approved_count()
    
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
        self.update_approved_count()

    def start_examination(self):
        species_folder = os.path.normpath(os.path.join(self.main_folder, self.current_species.get()))
        self.log_message(f"Starting examination for species folder: {species_folder}")
        try:
            all_files = [f for f in os.listdir(species_folder) if f.lower().endswith(('.wav', '.mp3'))]
            self.log_message(f"All files found: {all_files}")
            self.files_to_examine = all_files.copy()
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
                
                self.display_spectrogram(y, sr)
                self.load_and_play_audio(y, sr)
                
            except Exception as e:
                error_msg = f"Error processing file {self.current_file}: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
                self.log_message(error_msg)
                self.log_error(error_msg)
                self.examine_next_file()
        else:
            self.log_message("No more files to examine. Entering completion block.")
            detail_msg = "All files have been examined."
            self.log_message(detail_msg)
            messagebox.showinfo("Examination Complete", detail_msg)
            self.update_progress_file()
            self.reset_examination()

    def load_and_play_audio(self, y, sr):
        try:
            sd.stop()  # Stop any currently playing audio
            sd.play(y, sr)
        except Exception as e:
            self.log_message(f"Error playing audio: {e}")
            messagebox.showwarning("Audio Playback Error", "Unable to play audio. The spectrogram will still be displayed.")

    def display_spectrogram(self, y, sr):
        self.ax.clear()
        S = np.abs(librosa.stft(y))
        librosa.display.specshow(librosa.amplitude_to_db(S, ref=np.max), y_axis='hz', x_axis='time', ax=self.ax, sr=sr, cmap='viridis')
        plt.ylim(0, 15000)
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
            
            shutil.move(self.current_file, target_file)
            self.log_message(f"File successfully moved to: {target_file}")
            
            if decision == "approve":
                self.approved_count.set(self.approved_count.get() + 1)
                self.update_approved_count_label()
                if self.approved_count.get() >= self.max_seg_num:
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
        log_file_path = os.path.join(tempfile.gettempdir(), 'bird_sound_examiner_error_log.txt')
        with open(log_file_path, "a") as log_file:
            log_file.write(f"{error_msg}\n")
        self.log_message(f"Error logged to {log_file_path}")
        messagebox.showerror("Error", f"An error occurred. Error details:\n\n{error_msg}\n\nThis error has been logged to:\n{log_file_path}")
    
    def log_message(self, message):
        log_entry = f"{message}\n"
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

    def play_again(self):
        if self.current_file:
            try:
                y, sr = sf.read(self.current_file, dtype="float32")
                self.load_and_play_audio(y, sr)
            except Exception as e:
                self.log_message(f"Error playing audio again: {e}")
                messagebox.showwarning("Audio Playback Error", "Unable to play audio again.")

    def update_approved_count(self):
        if self.main_folder and self.current_species.get():
            species_folder = os.path.join(self.main_folder, self.filtered_species_folder, self.current_species.get())
            if os.path.exists(species_folder):
                count = len([f for f in os.listdir(species_folder) if f.lower().endswith(('.wav', '.mp3'))])
                self.approved_count.set(count)
            else:
                self.approved_count.set(0)
        else:
            self.approved_count.set(0)
        self.update_approved_count_label()

    def update_approved_count_label(self):
        self.approved_count_label.config(text=f"Approved Files: {self.approved_count.get()}")

    def set_max_files_threshold(self):
        new_threshold = simpledialog.askinteger("Set Threshold", "Enter new maximum files threshold:", 
                                                initialvalue=self.max_seg_num, minvalue=1, maxvalue=10000)
        if new_threshold:
            self.max_seg_num = new_threshold
            self.threshold_label.config(text=f"Max Files: {self.max_seg_num}")
            messagebox.showinfo("Threshold Updated", f"New maximum files threshold set to {self.max_seg_num}")

# Main execution
if __name__ == "__main__":
    root = tk.Tk()
    app = BirdSoundApp(root)
    root.mainloop()
