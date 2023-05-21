#!/usr/bin/env python3

import configparser
import openai

config = configparser.ConfigParser()
config.read('build/.config') #TODO: Take as input


#TODO: Validate key exists
openai.api_key = config['OpenAI']['OpenAIApiKey']; #TODO: Or from params, or from env
openai.organization = config['OpenAI']['OpenAIOrganization'];

completion = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Who are you?"}])
print(completion.choices[0].message.content)
