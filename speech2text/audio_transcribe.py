#!/usr/bin/env python3

import speech_recognition as sr
import argparse
import os
import time
import soundfile as sf
import resampy
import numpy as np
import itertools
import gevent as g
from vad import VadGenerator

with open("./google_key.json") as fin:
    GOOGLE_CLOUD_SPEECH_CREDENTIALS = fin.read()


def write_vad_chunks(audio_path, new_rate=48000):
    path, filename = os.path.dirname(audio_path), os.path.basename(audio_path)
    data, rate = sf.read(audio_path)
    if rate != new_rate:
        data = resampy.resample(data, rate, new_rate, filter="kaiser_fast")
    if len(data.shape) < 2:
        num_channels = 1
        data = data[:, np.newaxis]
    else:
        num_channels = data.shape[1]
    vad_generator = VadGenerator(num_channels)
    chunk_paths = []
    for vad_chunk in itertools.chain(vad_generator.emit(data, new_rate), vad_generator.emit_last()):
        time_section = vad_chunk.time_section
        t_start, t_end = time_section.t_start, time_section.t_end
        frame = vad_chunk.frame
        chunk_fname = str(t_start) + "__" + str(t_end) + "__" + filename
        chunk_path = os.path.join(path, chunk_fname)
        sf.write(chunk_path, frame, new_rate, format="flac")
        chunk_paths.append(chunk_path)
    return chunk_paths


def speech_to_text_short(audio_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
    try:
        text = recognizer.recognize_google_cloud(audio_data, credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS,
                                       language="ru-RU")
    except sr.UnknownValueError:
        print("Google Cloud Speech could not understand audio")
        print(audio_path)
        return None
    except sr.RequestError as e:
        print("Could not request results from Google Cloud Speech service; {0}".format(e))
        print(audio_path)
        raise
    return text, audio_path


def speech_to_text_long(audio_path):
    vad_chunk_paths = write_vad_chunks(audio_path)
    greenlets = [g.spawn(speech_to_text_short, chunk_path) for chunk_path in vad_chunk_paths]
    g.joinall(greenlets)
    phrases = [gl.value[0] for gl in greenlets if gl.value is not None]
    return phrases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio_filename_path", type=str, help="Audio filename path")
    ARGS = parser.parse_args()
    text = speech_to_text_long(ARGS.audio_filename_path)
    print(text)
    return text

if __name__ == "__main__":
    from gevent import monkey
    monkey.patch_all()
    main()
