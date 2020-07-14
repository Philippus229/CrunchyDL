<b>DISCLAIMER</b>: For educational purposes only!

# CrunchyDL
Crunchyroll Downloader heavily inspired by CR-Unblocker for Google Chrome (also uses the same server).
New version fixes problem with Crunchyroll apparently using captchas now (currently only supports HLS).
### TODO:
- find a way to download fragments for mpeg-dash video (maybe use different library like selenium-requests?)

## Requirements
- Python 3.x with pycryptodome, selenium (Chrome) and requests
- ffmpeg.exe in the same folder as the Python script

## Variables
- <b>localizeToUS</b>: use american session id to get access to more content
- <b>log_in</b>: log in or not (ignored in case of localization to US)
- <b>dlmode</b>: set this to False if you just want to watch anime in the browser (f.e. in combination with localizeToUS)
- <b>textmode</b>: set this to True for the console interface from the old version
