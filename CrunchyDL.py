from urllib.parse import quote
from urllib import request
import requests, random, json, os
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

username = input("Username: ")
password = input("Password: ")

session = requests.Session()

def generateDeviceId():
    return "".join(["ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"[random.randint(0, 61)] for x in range(32)])

def getSessionData(server, auth, user):
    uri = server["url"] + auth
    if server["sendUserId"] and user != None and user["userId"] != None and auth != "":
        uri += f"&user_id={quote(user['userId'])}"
    if server["generateDeviceId"]:
        uri += f"&device_id={generateDeviceId()}"
    res = session.get(uri)
    if res:
        json0 = res.json()
        if json0["data"]["country_code"] != "US":
            print(f"country_code is {json0['data']['country_code']}")
            return None
        else:
            return json0["data"]
    else:
        return None

def loginUser(sessionId, loginData):
    res = session.get(f"https://api.crunchyroll.com/login.0.json?session_id={sessionId}&locale=enUS&account={quote(loginData['username'])}&password={quote(loginData['password'])}")
    try:
        res = res.json()
        return res["data"]
    except:
        return None

def doLogin(sessionData):
    if not "header_profile_dropdown" in session.get("https://crunchyroll.com").text:
        data = loginUser(sessionData["session_id"], {"username": username, "password": password})
        if data == None:
            print("Login failed!")
        else:
            print(f"User logged in until {data['expires']}")

def updateCookies(extension, sessionData):
    print(f"got session id. Setting cookie {sessionData['session_id']}.")
    session.cookies.set(**{"name": "session_id",
                           "value": sessionData["session_id"],
                           "domain": f"crunchyroll{extension}",})
    session.cookies.set(**{"name": "sess_id",
                           "value": sessionData["session_id"],
                           "domain": f"crunchyroll{extension}",})
    session.cookies.set(**{"name": "c_locale",
                           "value": "enUS",
                           "domain": f"crunchyroll{extension}",})
    doLogin(sessionData)

def sequentialFetch(server, extension, auth, user):
    print(f"Fetching server {server['url']}")
    sessionData = getSessionData(server, auth, user)
    if sessionData != None:
        return updateCookies(extension, sessionData)
    else:
        return None

def localizeToUs(extension):
    print("Fetching session id...")
    return sequentialFetch({"url": "https://api1.cr-unblocker.com/getsession.php?version=1.1", "sendUserId": True, "generateDeviceId": None}, extension, "", None)

ext = input("Enter URL of the episode you wanna download: ").split("crunchyroll")[-1]
test = localizeToUs(ext)
test2 = session.get(f"https://crunchyroll{ext}").text
videodata = json.loads(test2.split("vilos.config.media = ")[1].split(";\n")[0])
streams = videodata["streams"]
currTitle = videodata["metadata"]["title"]
print(f"--------{currTitle}--------")
categorizedStreams = []
audioLangList = []
for s in [s0 for s0 in streams if s0["format"] == "adaptive_hls"]:
    al = s["audio_lang"]
    if not al in audioLangList:
        print(f"{len(audioLangList)}: {al}")
        audioLangList.append(al)
        categorizedStreams.append((al, []))
    categorizedStreams[audioLangList.index(al)][1].append((s["hardsub_lang"], s["url"]))
audioSelected = categorizedStreams[int(input("Audio Language > "))][1]
for sl in range(len(audioSelected)):
    print(f"{sl}: {audioSelected[sl][0]}")
currURL = audioSelected[int(input("Subtitle Language > "))][1]
test3 = [str(l) for l in request.urlopen(currURL).readlines()]
availResolutions = [(test3[l].split(",RESOLUTION=")[1].split(",")[0], test3[l+1]) for l in range(len(test3)) if "#EXT-X-STREAM-INF" in test3[l]]
for r in range(len(availResolutions)):
    print(f"{r}: {availResolutions[r][0]}")
selected = availResolutions[int(input("Resolution > "))][1]
print("Downloading chunk list...")
tmpcl = [str(l) for l in request.urlopen(selected[2:][:-1]).readlines()]
keyurl = [l.split("URI=\"")[1].split("\"\\n")[0] for l in tmpcl if "#EXT-X-KEY:METHOD=AES-128" in l][0]
key = request.urlopen(keyurl).read()
print(key)
chunklist = [tmpcl[l+1].replace("\\n", "") for l in range(len(tmpcl)) if "#EXTINF" in tmpcl[l]]
print("Done, downloading chunks...")
if not os.path.isdir("temp"):
    os.mkdir("temp")
for c in range(len(chunklist)):
    request.urlretrieve(chunklist[c][2:][:-1], f"temp/{c}.ts")
    print(f"{c+1} of {len(chunklist)} done...")
print("Done, decoding and combining chunks...")
with open(f"{currTitle}.ts", "wb") as f0:
    tmpdirlen = len(os.listdir("temp"))
    for f1 in range(tmpdirlen):
        f2 = open(os.path.join("temp", f"{f1}.ts"), "rb")
        f0.write(unpad(AES.new(key, AES.MODE_CBC, iv=f2.read(16)).decrypt(f2.read()), AES.block_size))
        f2.close()
        os.remove(os.path.join("temp", f"{f1}.ts"))
        print(f"{f1+1} of {tmpdirlen} done...")
    f0.close()
os.rmdir("temp")
print("Done!")
