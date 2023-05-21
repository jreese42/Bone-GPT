# Building Bone-GPT

## Requirements

Bone-GPT requires piper for TTS.  You will need to build and provide this before building Bone-GPT.
Check it out from https://github.com/rhasspy/piper and build it or download a release package. Follow the piper README to build it.

If building Piper from source, Piper depends on a patched version of espeak-ng, which you can find in the /lib directory of piper. 
Follow the [Build Guide|https://github.com/espeak-ng/espeak-ng/blob/master/docs/building.md] for espeak-ng to build and install it.

Piper also depends on ONNX runtime, which can be downloaded from https://github.com/microsoft/onnxruntime.
Place ONNX runtime into Piper's `lib/$(uname -s)-$(uname -m:)`.