# Bone-GPT
The goal of this project is to build an AI voice pipeline for a halloween decoration as a demonstration of conversational voice assistant pipelines in public or semi-public settings. It is also a test of local vs. remote AI-based SR, LLM, and TTS models.

## Building
See the [Build Guide](doc/Building.md) for information about requirements and how to build this project.

## Running
Execute `build/boneGPT.sh`. Arguments are processed from the commandline first, then the config file, and finally the environment.

|Argument|Description|Default|Config Parameter|Environment Variable|
|--------|-----------|-------|----------------|--------------------|
|`-c`,`--config`|path to config file|`.config`|||
|`-pf`,`--promptfile`|path to prompt file|`openai_prompt.txt`|`OpenAIPromptFile`||
|`--openai-key`|OpenAI API Key||`OpenAI.OpenAIApiKey`|`OPENAI_APIKEY`|
|`--openai-organization`|OpenAI Organization||`OpenAI.OpenAIOrganization`|`OPENAI_ORGANIZATION`|
|`--stt-provider`|Speech-to-Text Provider. `google`, `openai`, or `sphinx`|`google`|`General.STTProvider`||

I'll clean this up later, this is just how it works for now.
