#!/usr/bin/env python3

import os
import sys
import argparse
import configparser
import openai

parser = argparse.ArgumentParser(
                    prog='Bone-GPT', 
                    description='AI Voice Assistant Pipeline for Halloween Decorations')
parser.add_argument('-c', default='.config', dest='configFilePath',
                    help='path to .config file')
parser.add_argument('--openai-key', dest='openaiApiKey',
                    help='An API Key for OpenAI. May alternatively be provided in the .config file or in the environment as OPENAI_APIKEY')
parser.add_argument('--openai-organization', dest='openaiOrganization',
                    help='An Organization for the OpenAI API. If omitted, the default Organization for your OpenAI account will be used. May alternatively be provided in the .config file or in the environment as OPENAI_ORGANIZATION')

args = parser.parse_args()

config = configparser.ConfigParser()
config.read(args.configFilePath)

# Resolve OpenAI Arguments from config or env if not provided as args
if not args.openaiApiKey:
    args.openaiApiKey = config['OpenAI']['OpenAIApiKey']
if not args.openaiOrganization:
    args.openaiOrganization = config['OpenAI']['OpenAIOrganization']

if not args.openaiApiKey:
    args.openaiApiKey = os.getenv('OPENAI_APIKEY')
if not args.openaiOrganization:
    args.openaiOrganization = os.getenv('OPENAI_ORGANIZATION')

if not args.openaiApiKey:
    print('\n\nError: Unable to Resolve OpenAI API Key\n\n', file=sys.stderr)
    parser.print_help()
    exit(-1)

openai.api_key = args.openaiApiKey
openai.organization = args.openaiOrganization

completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Who are you?"}])
print(completion.choices[0].message.content)

#For now, dump to the TTS pipeline as a system call
voice_cmd = "echo '{}' | ./piper --model en-us-ryan-medium.onnx --output_raw | ffplay -autoexit -nodisp -f s16le -ar 22050 -i -"
os.system(voice_cmd.format(completion.choices[0].message.content))
