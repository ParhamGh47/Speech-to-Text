import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import pyaudio
import wave
import threading
import datetime
from vosk import Model, KaldiRecognizer
import speech_recognition as sr
import json
import os


vosk_english = "models/vosk-model-small-en-us-0.15"
vosk_persian = "models/vosk-model-small-fa-0.42"


class VoiceToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Speech to Text Converter")
        self.root.geometry("400x450")
        self.root.config(bg="#282c34")
        self.root.resizable(False, False)
        icon = tk.PhotoImage(file="icons/text-to-speech.png")
        root.iconphoto(False, icon)

        self.recording = False
        self.audio_file = "recorded_audio.wav"
        self.selected_language = "English"
        self.mode_var = tk.StringVar(value="online")

        self.title_label = tk.Label(self.root, text="Speech to Text",
                                    bg="#282c34", fg="#61afef", font=("Helvetica", 16, "bold"))
        self.title_label.pack(pady=20)

        self.mode_frame = tk.Frame(self.root, bg="#282c34")
        self.mode_frame.pack(pady=(0, 15))

        self.online_radio = tk.Radiobutton(self.mode_frame, text="Online Mode", variable=self.mode_var,
                                           value="online", bg="#282c34", fg="#abb2bf",
                                           selectcolor="#282c34", font=("Arial", 14), anchor="w")
        self.online_radio.pack(side=tk.LEFT, padx=10)

        self.offline_radio = tk.Radiobutton(self.mode_frame, text="Offline Mode", variable=self.mode_var,
                                            value="offline", bg="#282c34", fg="#abb2bf",
                                            selectcolor="#282c34", font=("Arial", 14), anchor="w")
        self.offline_radio.pack(side=tk.LEFT, padx=10)

        self.language_label = tk.Label(self.root, text="Select Language:",
                                       bg="#282c34", fg="#abb2bf", font=("Arial", 9))
        self.language_label.pack(pady=(5, 5))

        self.language_combobox = ttk.Combobox(self.root, state="readonly",
                                              values=["English", "Persian (Farsi)"])
        self.language_combobox.current(0)
        self.language_combobox.pack(pady=5)
        self.language_combobox.bind("<<ComboboxSelected>>", self.update_language)

        self.start_button = tk.Button(self.root, text="Start Recording", command=self.start_recording,
                                      bg="#98c379", fg="#282c34", font=("Arial", 14), width=20)
        self.start_button.pack(pady=(30, 15))

        self.stop_button = tk.Button(self.root, text="Stop Recording", command=self.stop_recording,
                                     bg="#e06c75", fg="#282c34", font=("Arial", 14), width=20, state=tk.DISABLED)
        self.stop_button.pack(pady=(0, 20))

        self.browse_button = tk.Button(self.root, text="Browse Audio File", command=self.browse_audio,
                                       bg="#61afef", fg="#282c34", font=("Arial", 14), width=20)
        self.browse_button.pack(pady=10)

        self.loading_label = tk.Label(self.root, text="Processing...",
                                      bg="#282c34", fg="#61afef", font=("Arial", 12), anchor="center")
        self.loading_label.pack(pady=10)
        self.loading_label.pack_forget()

    def update_language(self, event):
        self.selected_language = self.language_combobox.get()

    def start_recording(self):
        self.recording = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        
        recorded_folder = os.path.join(os.getcwd(), "recorded")
        if not os.path.exists(recorded_folder):
            os.makedirs(recorded_folder)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.audio_file = os.path.join(recorded_folder, f"recorded_audio_{timestamp}.wav")
        
        threading.Thread(target=self.record_audio).start()

    def stop_recording(self):
        self.recording = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        messagebox.showinfo("Recording Stopped", "Processing the audio...")
        self.process_audio(self.audio_file)

    def record_audio(self):
        chunk = 1024
        format = pyaudio.paInt16
        channels = 1
        rate = 16000

        audio = pyaudio.PyAudio()
        stream = audio.open(format=format, channels=channels, rate=rate,
                            input=True, frames_per_buffer=chunk)

        frames = []
        while self.recording:
            data = stream.read(chunk)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        audio.terminate()

        with wave.open(self.audio_file, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(audio.get_sample_size(format))
            wf.setframerate(rate)
            wf.writeframes(b"".join(frames))

    def process_audio(self, audio_path):
        self.processing_indicator = tk.Label(self.root, text="Processing...", bg="#282c34", fg="#abb2bf", font=("Arial", 12))
        self.processing_indicator.pack(pady=(5, 10))
        self.root.update()

        if self.mode_var.get() == "online":
            self.process_audio_online(audio_path)
        elif self.mode_var.get() == "offline":
            self.process_audio_offline(audio_path)

        self.processing_indicator.destroy()

    def process_audio_online(self, audio_path):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(audio_path) as source:
                audio = recognizer.record(source)
                language_code = "en-US" if self.selected_language == "English" else "fa-IR"
                text = recognizer.recognize_google(audio, language=language_code)
                self.show_text_window(text, audio_path)
        except sr.UnknownValueError:
            messagebox.showerror("Error", "Speech Recognition could not understand audio")
        except sr.RequestError as e:
            messagebox.showerror("Error", f"Could not request results from Speech Recognition service; check your internet connection.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def process_audio_offline(self, audio_path):
        model_path = ""
        if self.selected_language == "English":
            model_path = vosk_english
        elif self.selected_language == "Persian (Farsi)":
            model_path = vosk_persian

        if not os.path.exists(model_path):
            messagebox.showerror("Error", f"Model not found!")
            return

        try:
            model = Model(model_path)
            recognizer = KaldiRecognizer(model, 16000)

            with wave.open(audio_path, "rb") as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                    messagebox.showerror("Error", "Audio file must be mono PCM at 16kHz.")
                    return

                text = ""
                while True:
                    data = wf.readframes(4000)
                    if len(data) == 0:
                        break
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text += result.get("text", "") + " "

                final_result = json.loads(recognizer.FinalResult())
                text += final_result.get("text", "")

            self.show_text_window(text.strip(), audio_path)
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")

    def browse_audio(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav")])
        if file_path:
            self.process_audio(file_path)

    def show_text_window(self, text, audio_path):
        audio_name = audio_path.split("/")[-1]
        text_window = tk.Toplevel(self.root)
        text_window.title(f"Recognized Text - {audio_name}")
        text_window.geometry("500x450")
        icon = tk.PhotoImage(file="icons/text.png")
        text_window.iconphoto(False, icon)
        text_window.config(bg="#282c34")
        text_window.resizable(False, False)

        label = tk.Label(text_window, text="Recognized Text:", bg="#282c34", fg="#61afef", font=("Helvetica", 14))
        label.pack(pady=(10, 5))

        text_frame = tk.Frame(text_window, bg="#282c34")
        text_frame.pack(expand=True, fill="both", padx=10, pady=(7, 7))

        text_alignment = "right" if self.selected_language == "Persian (Farsi)" else "left"
        text_direction = "rtl" if self.selected_language == "Persian (Farsi)" else "ltr"

        text_area = tk.Text(text_frame, wrap=tk.WORD, font=("Arial", 12), bg="#21252b", fg="#abb2bf",
                            height=18, padx=10, pady=10)
        text_area.pack(side=tk.LEFT, expand=True, fill="both")
        text_area.tag_configure("align", justify=text_alignment)
        if text_direction == "rtl":
            text_area.tag_configure("rtl")
        text_area.insert(tk.END, text, ("align", "rtl") if text_direction == "rtl" else "align")
        text_area.config(state=tk.DISABLED)

        scrollbar = tk.Scrollbar(text_frame, command=text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y", padx=5)
        text_area.config(yscrollcommand=scrollbar.set)

        copy_button_frame = tk.Frame(text_window, bg="#282c34")
        copy_button_frame.pack(pady=(5, 10))

        copy_button = tk.Button(copy_button_frame, text="Copy to Clipboard",
                                command=lambda: self.copy_to_clipboard(copy_button, text),
                                bg="#74c4c3", fg="#282c34", font=("Arial", 12), width=15)
        copy_button.pack()


    def copy_to_clipboard(self, button, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update()
        button.config(text="Copied!", bg="#6fa688")
        button.config(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = VoiceToTextApp(root)
    root.mainloop()
