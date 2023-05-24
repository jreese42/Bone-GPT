#!/usr/bin/env python3

import os
import sys
import argparse
import configparser
import openai
import speech_recognition as sr
from subprocess import Popen, PIPE, DEVNULL

validSttProviders = ['google', 'openai', 'sphinx']

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
    parser.add_argument('--stt-provider', dest='sttProvider', choices=validSttProviders,
                        help='Select Speech-to-Text provider.')
    
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

    if not args.sttProvider:
        args.sttProvider = config['General']['STTProvider']
        if not args.sttProvider in validSttProviders:
            print('\n\nError: STT Provider is not valid.\n\n', file=sys.stderr)
            parser.print_help()
            exit(-1)
    
    print("Using STT Provider '{}'".format(args.sttProvider))

    controller = OpenAIController(args.openaiApiKey, args.openaiOrganization)
    prompt_conversation = Conversation()
    with open(args.promptFilePath) as f:
        prompt_conversation.add_user_message(f.read())
    controller.set_prompt(prompt_conversation)

    voice_pipeline = VoicePipeline(config['Paths']['PiperPath'],"en-us-ryan-high.onnx", args.sttProvider, args.openaiApiKey)
    voice_pipeline.adjust_input_ambient_level()

    motd()
    intro_line = "Happy Halloween! I'm Bonejangles, the skeleton who loves to give frights and delights. Are you brave enough to talk to me?"
    voice_pipeline.vocalize(intro_line)

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
            controller.stream_completion(voice_pipeline)
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
    def current_role(self):
        try:
            return self.messages[-1]["role"]
        except:
            return "none"
    def add_message(self, role, message):
        self.messages.append({"role": role, "content": message})
    def add_system_message(self, message):
        self.messages.append({"role": "system", "content": message})
    def add_user_message(self, message):
        self.messages.append({"role": "user", "content": message})
    def add_assistant_message(self, message):
        self.messages.append({"role": "assistant", "content": message})
    def last_message(self):
        return self.messages[-1]["content"]
    def append_stream_content(self, content):
        #inserts streaming content into the last message
        self.messages[-1]["content"] += content

class OpenAIController:
    def __init__(self, apiKey, organization):
        self.prompt_conversation = Conversation()
        self.conversation = Conversation()
        self.model = "gpt-3.5-turbo"
        openai.api_key = apiKey
        openai.organization = organization

        self.stream_current_role = "assistant"
        self.stream_current_content = ""
    
    def set_prompt(self, prompt_conversation):
        self.prompt_conversation = prompt_conversation
        self.reset()
    
    def reset(self):
        self.conversation = self.prompt_conversation
    
    def fetch_completion(self):
        completion = openai.ChatCompletion.create(model=self.model, messages=self.conversation.messages)
        #TODO check errors
        self.conversation.add_assistant_message(completion.choices[0].message.content)

    def stream_completion(self, voice_pipeline):
        stream = openai.ChatCompletion.create(model=self.model, messages=self.conversation.messages, stream=True)
        #TODO check errors
        for chunk in stream:
            if 'choices' in chunk and 'delta' in chunk.choices[0]:
                if 'role' in chunk.choices[0].delta:
                    #new role means start a new message in the Conversation
                    self.conversation.add_message(chunk.choices[0].delta.role, "")
                    #if role is assistant and tokens sufficient or stop, open voice pipeline
                if 'content' in chunk.choices[0].delta:
                    #content delta gets appended into the current message, and also the voice pipeline
                    self.conversation.append_stream_content(chunk.choices[0].delta.content)
                    if self.conversation.current_role() == "assistant":
                        voice_pipeline.handle_stream_content(chunk.choices[0].delta.content)
                        print(chunk.choices[0].delta.content, end='')
                if 'finish_reason' in chunk.choices[0]:
                    if chunk.choices[0].finish_reason != None:
                        voice_pipeline.handle_stream_stop()
                        print("")
        
class VoicePipeline:
    def __init__(self, piper_path, model_path, stt_provider, openai_key = None):
        self.piper_path = piper_path
        self.model_path = model_path
        self.stt_provider = stt_provider
        self.openai_key = openai_key
        self.voice_cmd = "echo '{line}' | {piper} --model {model} --output_raw | ffmpeg -hide_banner -loglevel error -nostats -f s16le -ar 22050 -i - -filter_complex 'asplit [out1][out2];[out1]afreqshift=shift=-450[shifted];[shifted]aecho=0.8:0.88:80:0.5[echo];[echo]asubboost[sub];[sub]aphaser[final1];[out2]afreqshift=shift=-350[s2];[s2]asubboost[final2];[final1] [final2] amix[mixed];[mixed]volume=volume=10dB[vol];[vol]atempo=0.85' -f s16le pipe:1 | ffplay -hide_banner -loglevel error -nostats -autoexit -nodisp -f s16le -ar 22050 -i -".format(line='{line}',piper=self.piper_path, model=self.model_path)
        self.speech_recognizer = sr.Recognizer()
        self.speech_recognizer.energy_threshold = 4000
        self.speech_recognizer.dynamic_energy_threshold = True
        self.stream_content_queue = []
        self.stream_content_buffer = []
        self.ffplay_proc = None
        self.ffmpeg_proc = None
        self.piper_proc = None

    def open_pipeline(self):
        '''Open the pipeline for streaming data'''
        piper_args = [self.piper_path, "--model", self.model_path, "--output_raw"]
        ffmpeg_args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostats", "-f", "s16le", "-ar", "22050", "-i", "-", "-filter_complex", "asplit [out1][out2];[out1]afreqshift=shift=-450[shifted];[shifted]aecho=0.8:0.88:80:0.5[echo];[echo]asubboost[sub];[sub]aphaser[final1];[out2]afreqshift=shift=-350[s2];[s2]asubboost[final2];[final1] [final2] amix[mixed];[mixed]volume=volume=10dB[vol];[vol]atempo=0.85", "-f", "s16le", "pipe:1"]
        ffplay_args = ["ffplay", "-hide_banner", "-loglevel", "error", "-nostats", "-autoexit", "-nodisp", "-f", "s16le", "-ar", "22050", "-i", "-"]
        self.piper_proc = Popen(piper_args, text=True, stdin=PIPE, stdout=PIPE, stderr=DEVNULL)
        self.ffmpeg_proc = Popen(ffmpeg_args, stdin=self.piper_proc.stdout, stdout=PIPE)
        self.ffplay_proc = Popen(ffplay_args, stdin=self.ffmpeg_proc.stdout, stdout=None)

    def close_pipeline(self):
        '''Close the pipeline'''
        self.piper_proc.stdin.close()
        self.piper_proc.wait()
        self.ffmpeg_proc.wait()
        self.ffplay_proc.wait()
        self.ffplay_proc = None
        self.ffmpeg_proc = None
        self.piper_proc = None

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
                if self.stt_provider == 'google':
                    query = r.recognize_google(audio, language='en-US')
                elif self.stt_provider == 'openai':
                    query = r.recognize_whisper_api(audio, api_key=self.openai_key)
                elif self.stt_provider == 'sphinx':
                    query = r.recognize_sphinx(audio, language="en-US")
                print(f"User said: {query}\n")
            except Exception as e:
                print(e)   
                print("Unable to Recognize your voice.") 
                return None
        
        return query

    def handle_stream_content(self, stream_content):
        # print("stream content {}".format(stream_content))
        #The TTS model needs complete lines to operate on, so split on punctuation and sent it to the pipeline in chunks.
        #This speeds up the time to first data coming out of the pipeline
        #TODO If initial response takes more than 1s, queue a "Hmm", "Sure", "Okay", etc with a short pause after
        self.stream_content_buffer.insert(0, stream_content)

        #queue data until a terminator
        if any(p in stream_content for p in ".!?"):
            #We found some punctuation. Start the TTS!
            content = ""
            while len(self.stream_content_buffer) > 0:
                content += self.stream_content_buffer.pop()
            self.stream_content_queue.insert(0, self.piper_token_sanitize(content) + '\n')

            if not self.piper_proc:
                self.open_pipeline()

            #provide TTS with all data up until the last punctuation found
            while len(self.stream_content_queue) > 0:
                self.piper_proc.stdin.write(self.stream_content_queue.pop())
            self.piper_proc.stdin.flush()
            

    def handle_stream_stop(self):
        if len(self.stream_content_buffer) > 0:
            content = ""
            while len(self.stream_content_buffer) > 0:
                content += self.stream_content_buffer.pop()
            self.stream_content_queue.insert(0, self.piper_token_sanitize(content) + '\n')

        if len(self.stream_content_queue) > 0:
            self.open_pipeline()
            #provide TTS with all data up until the last punctuation found
            while len(self.stream_content_queue) > 0:
                self.piper_proc.stdin.write(self.stream_content_queue.pop())
        self.close_pipeline()
    
    def piper_token_sanitize(self, input_string):
        '''Strip away or change certain tokens which piper has trouble pronouncing'''
        #TODO This should be stored in a file
        #These tokens get replaced only if the full word is found
        sanitize_tokens_full_word_only = {
            "the": "the", #TBD
            "boo": "boooo",
            "mwahaha": "mu-ha-ha",
        }

        #These tokens get replaced if they appear anywhere in the string
        sanitize_tokens_anywhere = { 
            "!\"": "!",
        }

        words = input_string.lower().split(' ')
        for i in range(len(words)):
            word = words[i]
            punc = ""
            #strip punctuation
            if len(word) > 1 and word[-1] in ".!?":
                punc = word[-1]
                word = word[:-1]
            if word in sanitize_tokens_full_word_only.keys():
                words[i] = sanitize_tokens_full_word_only[word] + punc

        out = ' '.join(words)
        for token, substitution in sanitize_tokens_anywhere.items():
            out = out.replace(token, substitution)
        return out

def motd():
    print("                      :::!~!!!!!:.\n                  .xUHWH!! !!?M88WHX:.\n                .X*#M@$!!  !X!M$$$$$$WWx:.\n               :!!!!!!?H! :!$!$$$$$$$$$$8X:\n              !!~  ~:~!! :~!$!#$$$$$$$$$$8X:\n             :!~::!H!<   ~.U$X!?R$$$$$$$$MM!\n             ~!~!!!!~~ .:XW$$$U!!?$$$$$$RMM!\n               !:~~~ .:!M\"T#$$$$WX??#MRRMMM!\n               ~?WuxiW*`   `\"#$$$$8!!!!??!!!\n             :X- M$$$$       `\"T#$T~!8$WUXU~\n            :%`  ~#$$$m:        ~!~ ?$$$$$$\n          :!`.-   ~T$$$$8xx.  .xWW- ~\"\"##*\"\n.....   -~~:<` !    ~?T#$$@@W@*?$$      /`\nW$@@M!!! .!~~ !!     .:XUW$W!~ `\"~:    :\n#\"~~`.:x%`!!  !H:   !WM$$$$Ti.: .!WUn+!`\n:::~:!!`:X~ .: ?H.!u \"$$$B$$$!W:U!T$$M~\n.~~   :X@!.-~   ?@WTWo(\"*$$$W$TH$! `\nWi.~!X$?!-~    : ?$$$B$Wu(\"**$RM!\n$R@i.~~ !     :   ~$$$$$B$$en:``\n?MXT@Wx.~    :     ~\"##*$$$$M~")

if __name__ == "__main__":
    main()