import os
import threading

from flask import Flask, request, redirect, flash, jsonify
from werkzeug.utils import secure_filename
from audio_transcribe import speech_to_text

UPLOAD_FOLDER = '/home/vlad/abby_hack/AgileHelper/speech2text/data'

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def long_running_task(audio_file_path):
    text = speech_to_text(audio_file_path)
    return text


@app.route('/', methods=['POST', 'GET'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            saved_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(saved_file_path)
            task = threading.Thread(target=long_running_task, args=(saved_file_path, ))
            task.start()
            return jsonify({"success": True})

    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''


if __name__ == "__main__":
    app.debug = True
    app.run()
