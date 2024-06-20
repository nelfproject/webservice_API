#!/usr/bin/env python3

"""
NeLF Transcription Webservice Python API
Author: Jakob Poncelet
Version: v0.3
Date: 20/06/2024
Contact: jakob.poncelet(at)kuleuven.be
"""

import clam.common.client
import clam.common.status
import sys
import os
import time
from datetime import datetime

## SETTINGS ############
# NeLF webservice account
username = "XXX"
password = "XXX"

# Specify a file, a list of files or a directory with files to process
input_path = "./files"

# Set output location
output_dir = "./result"
########################

# Project ID
project = "project_%s" % datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
print("Creating project with ID: %s" % project)

# Check if inputs are valid
if isinstance(input_path, str):
    if os.path.isdir(input_path):
        input_files = [os.path.join(input_path, item) for item in os.listdir(input_path)]
    elif os.path.isfile(input_path):
        input_files = [input_path]
elif isinstance(input_path, list):
    input_files = input_path
else:
    raise ValueError('input_path should be a filepath, a list of filepaths, or a directory path which contains files')

for input_file in input_files:
    assert os.path.isfile(input_file), 'Input file %s does not exist' % input_file
    fileid, file_ext = os.path.splitext(os.path.basename(input_file))
    assert file_ext in ['.wav', '.mp3', '.mp4'], "File has to be WAV / MP3 / MP4 format"

print('Processing %i files' % len(input_files))

# Output for the project
output_dir = os.path.join(output_dir, project)
assert not os.path.isdir(output_dir), "output_dir for this project already exists"
os.makedirs(output_dir, exist_ok=True)
print("Storing output at: %s" % output_dir)


# Create client, connect to server.
clamclient = clam.common.client.CLAMClient("https://ws.nelfproject.be/nelf_transcribe", username, password, basicauth=True)

# Now we call the webservice and create the project (in this and subsequent methods of clamclient, exceptions will be raised on errors).
clamclient.create(project)

# Get project status and specification
data = clamclient.get(project)
print("Status: https://ws.nelfproject.be/nelf_transcribe/%s" % project)

# Add one or more input files according to a specific input template
input_templates = {".wav": "InputWavFile", ".mp3": "InputMP3File", ".mp4": "InputMP4File"}
for input_file in input_files:
    print("Uploading input: %s" % input_file)
    fileid, file_ext = os.path.splitext(os.path.basename(input_file))
    clamclient.addinputfile(project, data.inputtemplate(input_templates[file_ext]), input_file)

# Example with Default parameters
# If you want different parameters, check out 'parameters.txt' for all valid parameters and their functions
data = clamclient.start(project, version="v2", vad="ECAPA2", diarization="speaker_diarization", wordleveltiming="segment_timings", langid="skip_language_detection", annot="both", formatting="clean", vadtiming="timestamps", speakerannot="combine", device="GPU")

# Check for parameter errors
if data.errors:
    print("An error occured: " + data.errormsg, file=sys.stderr)
    for parametergroup, paramlist in data.parameters:
        for parameter in paramlist:
            if parameter.error:
                print("Error in parameter " + parameter.id + ": " + parameter.error, file=sys.stderr)
    clamclient.delete(project) #delete project
    sys.exit(1)

# If everything went well, the system is now running, we simply wait until it is done and retrieve the status in the meantime
prev_status = None
while data.status != clam.common.status.DONE:
    data = clamclient.get(project)  # get status
    if data.statusmessage != prev_status:
        print(data.statusmessage, file=sys.stderr)
        prev_status = data.statusmessage
    else:
        time.sleep(5) #wait 5 seconds before polling status
print('Done processing all files.')

# Iterate over output files
for outputfile in data.output:
    outputfile.copy(os.path.join(output_dir, outputfile.filename))

# Delete the project (otherwise it would remain on server and clients would leave a mess)
#clamclient.delete(project)
