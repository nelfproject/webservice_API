#!/usr/bin/env python3

"""
NeLF Transcription Webservice Python API
Author: Jakob Poncelet
Version: v0.1
Date: 24/05/2024
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


#create client, connect to server.
clamclient = clam.common.client.CLAMClient("https://ws.nelfproject.be/nelf_transcribe", username, password, basicauth=True)

#Now we call the webservice and create the project (in this and subsequent methods of clamclient, exceptions will be raised on errors).
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

## PARAMETERS ###########################################################################
# Set Parameters (the first option is the default and recommended setting)
#   - version
#       Model Version: Select which version you want to use
#       Options: v2 (=latest), v1
#   - vad
#       Voice Activity Detection: Model to use for Voice Activity Detection
#       Options: ECAPA2, rVAD, CRDNN
#   - type
#       Model Type: Transcribe the input recordings with an ASR model (best transcriptions) or generate word-level timings (still experimental!) with a transcription+timing model
#       Options: best (=transcribe), wordtimings
#   - annot
#       Transcription type: Generate a verbatim transcription, a subtitle transcription, or both
#       Options: both, verbatim, subtitle
#   - formatting
#       Formatting: The transcription should contain all tags (e.g. <*d>, <.>) or should be cleaned up text
#       Options: clean, tags
#   - vadtimings
#       Timestamps: Include start/end timestamps for speech sentences or generate one large body of text without timestamps
#       Options: timestamps, notimestamps
#   - device
#       Compute device -  Decode on GPU (fast) or CPU (slow). GPU jobs might need to queue for a short while. Processing time on GPU is estimated at around 0.25-0.50 RTF depending on the chosen configuration
#       Options: GPU, CPU
#######################################################################################
# Example with Default parameters
data = clamclient.start(project, version="v2", vad="ECAPA2", type="best", annot="both", formatting="clean", vadtiming="timestamps", device="GPU")

# check for parameter errors
if data.errors:
    print("An error occured: " + data.errormsg, file=sys.stderr)
    for parametergroup, paramlist in data.parameters:
        for parameter in paramlist:
            if parameter.error:
                print("Error in parameter " + parameter.id + ": " + parameter.error, file=sys.stderr)
    clamclient.delete(project) #delete project
    sys.exit(1)

#If everything went well, the system is now running, we simply wait until it is done and retrieve the status in the meantime
prev_status = None
while data.status != clam.common.status.DONE:
    data = clamclient.get(project)  # get status
    if data.statusmessage != prev_status:
        print(data.statusmessage, file=sys.stderr)
        prev_status = data.statusmessage
    else:
        time.sleep(5) #wait 5 seconds before polling status
print('Done processing all files.')

#Iterate over output files
for outputfile in data.output:
    outputfile.copy(os.path.join(output_dir, outputfile.filename))

#delete the project (otherwise it would remain on server and clients would leave a mess)
clamclient.delete(project)
