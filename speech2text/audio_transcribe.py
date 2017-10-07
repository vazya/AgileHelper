#!/usr/bin/env python3

import speech_recognition as sr
import argparse
import os
import subprocess


with open("./google_key.json") as fin:
    GOOGLE_CLOUD_SPEECH_CREDENTIALS = fin.read()


def speech_to_text(audio_path):
    recognizer = sr.Recognizer()
    filename, extension = os.path.splitext(audio_path)
    tmp_path = None
    if extension != ".flac":
        tmp_path = filename + ".flac"
        with open(os.devnull, 'w') as FNULL:
            subprocess.run(["ffmpeg", "-i", audio_path, tmp_path], stdout=FNULL, stderr=FNULL)
        audio_path = tmp_path
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google_cloud(audio_data, credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS,
                                       language="ru-RU")
        recognizer.recjj
    except sr.UnknownValueError:
        print("Google Cloud Speech could not understand audio")
        raise
    except sr.RequestError as e:
        print("Could not request results from Google Cloud Speech service; {0}".format(e))
        raise
    finally:
        if tmp_path is not None:
            os.remove(tmp_path)
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_filename", type=str, help="Audio filename")
    ARGS = parser.parse_args()
    text = speech_to_text(ARGS.audio_filename)
    print(text)
    return text

if __name__ == "__main__":
    main()
