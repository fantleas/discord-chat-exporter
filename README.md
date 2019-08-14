# discord-chat-exporter
A simple, easy-of-use Discord chat exporter written in Python.

DISCLAIMER: Use at your own risk.

## Installation
Before to start use, Python 3.6+ and dependencies should have been installed on your computer.

We assume that you have installed Python 3.6+ successfully.

```
# Install dependencies.
$ pip3 install -r requirements.txt
```

That's all what we should do.

## Usage
To see help, execute `python3 ./discord-chat-exporter.py --help`.

Example:
```
# This will export entire chat messages until message ID 123412341234 in channel ID 12345678.
python3 ./discord-chat-exporter.py --token-type User --channel-id 12345678 --newest-message-id 123412341234 --oldest-message-id 0 --path ./output.json
Token: (not shown)
...
```

You should notice that this script does *not* check validity of `--newest-message-id` and `--oldest-message-id` due to lack of Discord official API functionalities. If you used some non-existent IDs, it may go wrong.

## Specification
Token is a Discord account token. It can be user and bot tokens. If you are wondering how to get my token, search for it :)

Format of the JSON file is just an array of [message object](https://discordapp.com/developers/docs/resources/channel#message-object).
There are no metadata.

## Performance
For an instance, exporting 1.3M messages from Feb 2018 to Aug 2019 takes 70 minutes and makes a 640MB JSON file on my computer.

## License
Original author is Deneb (https://github.com/denebu)

MIT License
