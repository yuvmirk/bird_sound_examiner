# Bird Sound Examiner

## Description

Bird Sound Examiner is a user-friendly desktop application designed for ornithologists and birding enthusiasts. It simplifies the process of analyzing and categorizing bird sound recordings, allowing users to efficiently sort audio files into categories such as valid species calls, false positives, and noise.

## For Windows Users

### How to Download and Use the Application

1. Go to the [Releases](https://github.com/yourusername/bird-sound-examiner/releases) page of this repository.
2. Find the latest release and download the `Bird.Sound.Examiner.exe` file.
3. Once downloaded, double-click the `.exe` file to run the application. No installation is required.

### Using the Application

1. When you first open the app, you'll see instructions and control buttons.
2. Click "Select Main Folder" to choose the directory containing your species folders.
3. Select a species from the dropdown menu.
4. Click "Start Examination" to begin analyzing audio files.
5. For each audio file:
   - Listen to the audio and observe the spectrogram.
   - Use the following controls to categorize the sound:
     - Press SPACE or do nothing to mark as OK (valid species call)
     - Left-click or press 'F' to mark as False Positive
     - Right-click or press 'N' to mark as Noise
6. The application will automatically move to the next file after each decision.
7. Continue until all files for the selected species have been examined.

### System Requirements

- Windows 7 or later
- No additional software installation is required

## Features

- Easy-to-use graphical interface
- Audio playback of bird sound recordings
- Spectrogram visualization for detailed sound analysis
- Quick categorization using keyboard shortcuts or mouse clicks
- Automatic file organization based on user decisions
- Support for multiple species within a single session

## For Developers

If you're interested in the source code or contributing to the project:

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/bird-sound-examiner.git
   ```
2. Set up a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```
3. Run the main script:
   ```
   python bird_sound_examiner.py
   ```

## Contributing

Contributions to the Bird Sound Examiner are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions, feedback, or to report issues, please open an issue on this repository or contact [Yuval Mirko] at [yuvmirk@gmail.com].
cc Yizhar Lavner