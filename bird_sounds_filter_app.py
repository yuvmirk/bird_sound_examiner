import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import shutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import librosa
import sounddevice as sd
import numpy as np
import threading

class BirdSoundApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Bird Sound Examiner")
        self.master.geometry("900x800")
        self.master.configure(bg="#f0f0f0")  # Light gray background
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.main_folder = ""
        self.current_species = tk.StringVar()
        self.current_file = ""
        self.files_to_examine = []
        
        self.create_widgets()
        
    def create_widgets(self):
        self.configure_styles()
        
        main_frame = ttk.Frame(self.master, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Guidance Panel with larger font
        guidance_frame = ttk.LabelFrame(main_frame, text="Instructions", padding="10 10 10 10", style="Large.TLabelframe")
        guidance_frame.pack(pady=10, fill=tk.X)
        
        guidance_text = (
            "1. Choose the main folder containing all species folders.\n"
            "2. Select the species you wish to work on from the dropdown.\n"
            "3. Click 'Start Examination' to begin.\n"
            "4. For each audio file:\n"
            "   - Press SPACE or do nothing to mark as OK\n"
            "   - Left-click or press 'F' to mark as False Positive\n"
            "   - Right-click or press 'N' to mark as Noise\n"
            "5. Try to finish all files of one species before moving to the next."
        )
        
        guidance_label = ttk.Label(guidance_frame, text=guidance_text, justify=tk.LEFT, wraplength=780, style="Large.TLabel")
        guidance_label.pack(pady=5)

        # Folder selection
        folder_frame = ttk.Frame(main_frame)
        folder_frame.pack(pady=10, fill=tk.X)
        
        self.folder_button = ttk.Button(folder_frame, text="Select Main Folder", command=self.select_folder)
        self.folder_button.pack(side=tk.LEFT)
        
        self.folder_label = ttk.Label(folder_frame, text="No folder selected")
        self.folder_label.pack(side=tk.LEFT, padx=10)
        
        # Species selection
        species_frame = ttk.Frame(main_frame)
        species_frame.pack(pady=10, fill=tk.X)
        
        ttk.Label(species_frame, text="Select Species:").pack(side=tk.LEFT)
        self.species_dropdown = ttk.Combobox(species_frame, textvariable=self.current_species, state="readonly")
        self.species_dropdown.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        self.species_dropdown.bind("<<ComboboxSelected>>", self.on_species_selected)
        
        # Start button
        self.start_button = ttk.Button(main_frame, text="Start Examination", command=self.start_examination, style="Accent.TButton")
        self.start_button.pack(pady=10)
        
        # Spectrogram (slightly smaller)
        spec_frame = ttk.Frame(main_frame)
        spec_frame.pack(pady=10, expand=True, fill=tk.BOTH)
        
        self.fig, self.ax = plt.subplots(figsize=(7, 3))  # Reduced size
        self.canvas = FigureCanvasTkAgg(self.fig, master=spec_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)
        
        # Control buttons
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(pady=10, fill=tk.X)
        
        self.ok_button = ttk.Button(control_frame, text="OK (Space)", command=lambda: self.process_decision("ok"))
        self.ok_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.fp_button = ttk.Button(control_frame, text="False Positive (F/Left-click)", command=lambda: self.process_decision("false_positive"))
        self.fp_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.noise_button = ttk.Button(control_frame, text="Noise (N/Right-click)", command=lambda: self.process_decision("noise"))
        self.noise_button.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Bind keyboard shortcuts
        self.master.bind('<space>', lambda event: self.process_decision("ok"))
        self.master.bind('f', lambda event: self.process_decision("false_positive"))
        self.master.bind('n', lambda event: self.process_decision("noise"))
        
        # Bind mouse clicks to the canvas widget
        self.canvas.get_tk_widget().bind("<Button-1>", lambda event: self.process_decision("false_positive"))
        self.canvas.get_tk_widget().bind("<Button-3>", lambda event: self.process_decision("noise"))

        # Remove focus from the Start button to prevent accidental activation
        self.start_button.config(takefocus=0)
            
    def configure_styles(self):
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=('Helvetica', 10))
        self.style.configure("Large.TLabel", background="#f0f0f0", font=('Helvetica', 12))
        self.style.configure("TButton", font=('Helvetica', 10))
        self.style.configure("Accent.TButton", font=('Helvetica', 10, 'bold'))
        self.style.configure("TLabelframe", background="#f0f0f0")
        self.style.configure("TLabelframe.Label", font=('Helvetica', 11, 'bold'))
        self.style.configure("Large.TLabelframe.Label", font=('Helvetica', 13, 'bold'))
    
    def select_folder(self):
        self.main_folder = filedialog.askdirectory()
        if self.main_folder:
            self.folder_label.config(text=self.main_folder)
            self.update_species_dropdown()
        
    def update_species_dropdown(self):
        species = [f for f in os.listdir(self.main_folder) if os.path.isdir(os.path.join(self.main_folder, f))]
        self.species_dropdown['values'] = species
        if species:
            self.species_dropdown.set(species[0])
            
    def on_species_selected(self, event):
        self.start_button.config(state=tk.NORMAL)
        
    def start_examination(self):
        species_folder = os.path.join(self.main_folder, self.current_species.get())
        try:
            self.files_to_examine = [f for f in os.listdir(species_folder) if (f.endswith('.wav') or f.endswith('.mp3'))]
            if self.files_to_examine:
                self.folder_button.config(state=tk.DISABLED)  # Disable the button
                self.start_button.config(state=tk.DISABLED)  # Disable the button
                self.examine_next_file()
            else:
                tk.messagebox.showinfo("No Files", "No WAV or MP3 files found in the selected species folder.")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Error accessing species folder: {e}")
    
    def examine_next_file(self):
        if self.files_to_examine:
            self.current_file = os.path.join(self.main_folder, self.current_species.get(), self.files_to_examine.pop(0))
            try:
                y, sr = librosa.load(self.current_file)
                if len(y) == 0:
                    print(f"Warning: Empty audio file: {self.current_file}")
                    self.examine_next_file()  # Skip this file and move to the next
                    return
                self.load_and_play_audio(y, sr)
                self.display_spectrogram(y, sr)
            except Exception as e:
                print(f"Error processing file {self.current_file}: {e}")
                self.examine_next_file()  # Skip this file and move to the next
        else:
            tk.messagebox.showinfo("Finished", "All files have been examined.")

    def load_and_play_audio(self, y, sr):
        try:
            sd.play(y, sr)
        except sd.PortAudioError as e:
            print(f"PortAudio error: {e}")
            tk.messagebox.showwarning("Audio Playback Error", "Unable to play audio. The spectrogram will still be displayed.")
        except Exception as e:
            print(f"Unexpected error during audio playback: {e}")
            tk.messagebox.showwarning("Audio Playback Error", "An unexpected error occurred during audio playback. The spectrogram will still be displayed.")

    def display_spectrogram(self, y, sr):
        self.ax.clear()
        S = np.abs(librosa.stft(y))  # Get magnitude of STFT
        librosa.display.specshow(librosa.amplitude_to_db(S, ref=np.max), 
                                y_axis='hz', x_axis='time', ax=self.ax)
        self.ax.set_title(os.path.basename(self.current_file))
        self.canvas.draw()
    
    def process_decision(self, decision):
        if not self.current_file:
            return
        
        try:
            if decision == "noise":
                target_folder = os.path.join(os.path.dirname(self.current_file), 'noise')
            elif decision == "false_positive":
                target_folder = os.path.join(os.path.dirname(self.current_file), 'false_positive')
            else:  # "ok"
                self.examine_next_file()
                return
            
            os.makedirs(target_folder, exist_ok=True)
            shutil.move(self.current_file, os.path.join(target_folder, os.path.basename(self.current_file)))
            self.examine_next_file()
        except Exception as e:
            tk.messagebox.showerror("Error", f"Error processing decision: {e}")
            self.examine_next_file()  # Move to next file even if there's an error
            
root = tk.Tk()
app = BirdSoundApp(root)
root.mainloop()