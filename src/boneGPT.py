#!/usr/bin/env python3

import os
import sys
import argparse
import configparser
import openai
import speech_recognition as sr

def main():
    parser = argparse.ArgumentParser(
                        prog='Bone-GPT', 
                        description='AI Voice Assistant Pipeline for Halloween Decorations')
    parser.add_argument('-c', '--config', default='.config', dest='configFilePath',
                        help='path to .config file')
    parser.add_argument('-pf', '--promptfile', default='', dest='promptFilePath',
                        help='path to file containing prompt for OpenAI')
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

    if not args.promptFilePath:
        args.promptFilePath = config['OpenAI']['OpenAIPromptFile']

    controller = OpenAIController(args.openaiApiKey, args.openaiOrganization)
    prompt_conversation = Conversation()
    with open(args.promptFilePath) as f:
        prompt_conversation.add_user_message(f.read())
    controller.set_prompt(prompt_conversation)

    voice_pipeline = VoicePipeline(config['Paths']['PiperPath'],"en-us-ryan-high.onnx")
    voice_pipeline.adjust_input_ambient_level()

    repl(controller, voice_pipeline)

def repl(controller, voice_pipeline):
    consecutive_idles = 0

    try:
        while True:
            # user_input = input('>>> ')
            voice_pipeline.adjust_input_ambient_level()
            user_input = voice_pipeline.take_input()
            if user_input == None:
                if consecutive_idles >=  5: #5 * 3 seconds = 15 second clear timer
                    print("Conversation Timeout.")
                    controller.reset()
                    consecutive_idles = 0
                else:
                    consecutive_idles = consecutive_idles+1
                continue

            if user_input == "clear":
                controller.reset()
                print("Cleared conversation.")
                continue

            if user_input in ('quit', 'exit'):
                print("\n>>> Goodbye!")
                break

            controller.conversation.add_user_message(user_input)
            controller.fetch_completion()
            print(controller.conversation.last_message())
            voice_pipeline.vocalize(controller.conversation.last_message())
            print()
            
    except KeyboardInterrupt:
        print('\n>>> Goodbye!')

class Conversation:
    def __init__(self):
        self.messages = []
    def __repr__(self):
        return 'Conversation()'
    def __str__(self):
        return str(self.messages)
    def clear(self):
        self.messages = []
    def add_system_message(self, message):
        self.messages.append({"role": "system", "content": message})
    def add_user_message(self, message):
        self.messages.append({"role": "user", "content": message})
    def add_assistant_message(self, message):
        self.messages.append({"role": "assistant", "content": message})
    def last_message(self):
        return self.messages[-1]["content"]

class OpenAIController:
    def __init__(self, apiKey, organization):
        self.prompt_conversation = Conversation()
        self.conversation = Conversation()
        self.model = "gpt-3.5-turbo"
        openai.api_key = apiKey
        openai.organization = organization
    
    def set_prompt(self, prompt_conversation):
        self.prompt_conversation = prompt_conversation
        self.reset()
    
    def reset(self):
        self.conversation = self.prompt_conversation
    
    def fetch_completion(self):
        completion = openai.ChatCompletion.create(model=self.model, messages=self.conversation.messages)
        #TODO check errors
        self.conversation.add_assistant_message(completion.choices[0].message.content)
        
class VoicePipeline:
    def __init__(self, piper_path, model_path):
        self.piper_path = piper_path
        self.model_path = model_path
        self.voice_cmd = "echo '{line}' | {piper} --model {model} --output_raw | ffmpeg -hide_banner -loglevel error -nostats -f s16le -ar 22050 -i - -filter_complex 'asplit [out1][out2];[out1]afreqshift=shift=-450[shifted];[shifted]aecho=0.8:0.88:80:0.5[echo];[echo]asubboost[sub];[sub]aphaser[final1];[out2]afreqshift=shift=-350[s2];[s2]asubboost[final2];[final1] [final2] amix[mixed];[mixed]volume=volume=10dB[vol];[vol]atempo=0.85' -f s16le pipe:1 | ffplay -hide_banner -loglevel error -nostats -autoexit -nodisp -f s16le -ar 22050 -i -".format(line='{line}',piper=self.piper_path, model=self.model_path)
        self.speech_recognizer = sr.Recognizer()
        self.speech_recognizer.energy_threshold = 4000
        self.speech_recognizer.dynamic_energy_threshold = True

    def vocalize(self, line):
        #For now, dump to the TTS pipeline as a system call
        line = line.replace('\n', '. ') #Some characters the TTS model pronounces but we don't want
        line = line.replace(':', '. ') #Some characters the TTS model pronounces but we don't want
        line = line.replace('\'', '\'\\\'\'') #Because we're dumping to shell currently
        os.system(self.voice_cmd.format(line=line))

    def adjust_input_ambient_level(self):
        with sr.Microphone() as source:
            self.speech_recognizer.adjust_for_ambient_noise(source, 0.5)

    def take_input(self):
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            r.pause_threshold = 0.6
            try:
                audio = r.listen(source, 3, 5)
            except sr.WaitTimeoutError as e:
                return None

            try:
                print("Recognizing...")   
                #TODO Try Sphinx vs Google vs OpenAI Whisper
                query = r.recognize_google(audio, language ='en-us')
                print(f"User said: {query}\n")
            except Exception as e:
                print(e)   
                print("Unable to Recognize your voice.") 
                return None
        
        return query

if __name__ == "__main__":
    main()