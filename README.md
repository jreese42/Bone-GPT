# Bone-GPT
The goal of this project is to build an AI voice pipeline for a halloween decoration as a demonstration of conversation voice assistant pipelines in public or semi-public settings.

## Building
See the [Build guide](doc/Building.md) for information about requirements and how to build this project.

## Running
First, activate the venv with `source build/.venv/bin/activate`.
Execute `build/boneGPT.sh`. Arguments are processed from the commandline first, then the config file, and finally the environment.

|Argument|Description|Default|Config Parameter|Environment Variable|
|--------|-----------|-------|----------------|--------------------|
|`-c`,`--config`|path to .config file|`.config`|||
|`--openai-key`|OpenAI API Key||`OpenAIApiKey`|`OPENAI_APIKEY`|
|`--openai-organization`|OpenAI Organization||`OpenAIOrganization`|`OPENAI_ORGANIZATION`|

I'll clean this up later, this is just how it works for now.