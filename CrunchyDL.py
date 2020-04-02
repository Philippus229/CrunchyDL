from urllib.parse import quote
from urllib import request
import requests, random, json, os, subprocess, math
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from bs4 import BeautifulSoup

username, password = open("credentials.cfg", "r").read().split("\n") if os.path.isfile("credentials.cfg") else (input("Username: "), input("Password: "))
if not os.path.isfile("credentials.cfg"):
    if input("Remember me? (y/n): ").lower() == "y":
        open("credentials.cfg", "w").write(f"{username}\n{password}")

session = requests.Session()
session.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4093.3 Safari/537.36"}

def localizeToUs():
    print("Fetching session id...")
    res = session.get("https://api1.cr-unblocker.com/getsession.php?version=1.1")
    if res:
        sessionData = res.json()["data"]
        if sessionData["country_code"] == "US":
            print(f"Got session id, setting cookie {sessionData['session_id']}.")
            session.cookies.set(**{"name": "session_id",
                                   "value": sessionData["session_id"],
                                   "domain": f"crunchyroll.com/videos/anime/alpha?group=all",})
            session.cookies.set(**{"name": "c_locale",
                                   "value": "enUS",
                                   "domain": f"crunchyroll.com/videos/anime/alpha?group=all",})
            if not "header_profile_dropdown" in session.get("https://crunchyroll.com").text:
                data = session.post(f"https://api.crunchyroll.com/login.0.json?session_id={sessionData['session_id']}&locale=enUS&account={quote(username)}&password={quote(password)}").json()["data"]
                if data != None:
                    print(f"User logged in until {data['expires']}")
                else:
                    return False
            return True

def downloadHLS(url, filepath, sameResForAll):
    test3 = session.get(url).text.split("\n")
    availResolutions = [(test3[l].split(",RESOLUTION=")[1].split(",")[0], test3[l+1]) for l in range(len(test3)) if "#EXT-X-STREAM-INF" in test3[l]]
    selected = ""
    if len(availResolutions) > 0:
        i = 0
        if type(sameResForAll) == str:
            i = [r[0] for r in availResolutions].index(sameResForAll)
        else:
            for r in range(len(availResolutions)):
                print(f"{r}: {availResolutions[r][0]}")
            i = int(input("Resolution > "))
            if sameResForAll == None:
                sameResForAll = [False, availResolutions[i][0]][input("Use same resolution for all? (y/n): ").lower() == "y"]
        selected = availResolutions[i][1]
    print("Downloading chunk list...")
    tmpcl = [str(l) for l in request.urlopen(selected).readlines()] if len(availResolutions) > 0 else [f"  {l}\\n " for l in test3]
    keyurl = [l.split("URI=\"")[1].split("\"\\n")[0] for l in tmpcl if "#EXT-X-KEY:METHOD=AES-128" in l][0]
    key = request.urlopen(keyurl).read()
    print(key)
    chunklist = [tmpcl[l+1].replace("\\n", "") for l in range(len(tmpcl)) if "#EXTINF" in tmpcl[l]]
    print("Done, downloading chunks...")
    if not os.path.isdir("temp"):
        os.mkdir("temp")
    for c in range(len(chunklist)):
        request.urlretrieve(chunklist[c][2:][:-1], os.path.join("temp", f"{c}.ts"))
        print(f"{c+1} of {len(chunklist)} done...")
    print("Done, decoding and combining chunks...")
    with open(filepath, "wb") as f0:
        tmpdirlen = len(os.listdir("temp"))
        for f1 in range(tmpdirlen):
            f2 = open(os.path.join("temp", f"{f1}.ts"), "rb")
            f0.write(unpad(AES.new(key, AES.MODE_CBC, iv=f2.read(16)).decrypt(f2.read()), AES.block_size))
            f2.close()
            os.remove(os.path.join("temp", f"{f1}.ts"))
            print(f"{f1+1} of {tmpdirlen} done...")
        f0.close()
    os.rmdir("temp")
    print("Done, converting file to mp4...")
    done = subprocess.Popen(f'ffmpeg.exe -i "{filepath}" -c:v libx264 -c:a aac "{filepath[:-2]}mp4"', stdout=subprocess.PIPE, shell=True).wait()
    os.remove(filepath)
    print("Done!")
    return sameResForAll

def merge_clean(filepath):
    for t in range(2):
        av = ["audio","video"][t]
        print(f"Merging {av} segments...")
        with open(f"{av}.m4{av[0]}", "wb") as out:
            for sfn in os.listdir(f"{av}_tmp"):
                sfp = os.path.join(f"{av}_tmp", sfn)
                out.write(open(sfp, "rb").read())
                os.remove(sfp)
            out.close()
    print("Merging audio and video...")
    if not os.path.isdir(os.path.dirname(filepath)):
        os.mkdir(os.path.dirname(filepath))
    done = subprocess.Popen(f'ffmpeg -i video.m4v -i audio.m4a -c:v copy -c:a copy "{filepath}"', stdout=subprocess.PIPE, shell=True).wait()
    os.remove("audio.m4a")
    os.remove("video.m4v")
    print("Done!")

def cut(string, cut0, cut1, rev=0):
    return string.split(cut0)[not rev].split(cut1)[rev]

def segToDict(seg):
    tmp_dict = {s.split('="')[0]:int(cut(s,'="','"')) for s in seg.split(" ") if "=" in s}
    tmp_dict["n"] = tmp_dict["r"]+1 if "r" in tmp_dict else 1
    return tmp_dict

def downloadDash(url, fp):
    add_headers = {"Accept": "*/*",
                   "Accept-Encoding": "gzip, deflate, br",
                   "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                   "Connection": "keep-alive",
                   "Host": cut(url,"//","/"),
                   "Origin": "https://static.crunchyroll.com",
                   "Referer": "https://static.crunchyroll.com/",
                   "Sec-Fetch-Dest": "empty",
                   "Sec-Fetch-Mode": "cors",
                   "Sec-Fetch-Site": "cross-site"}
    data = session.get(url, headers=add_headers).text
    open("test.mpd", "w").write(data)
    base_url0 = cut(data,"<BaseURL>","</BaseURL>")
    for t in range(2):
        av = ["video","audio"][t]
        if not os.path.isdir(f"{av}_tmp"):
            os.mkdir(av+"_tmp")
        a_set = [set_split.split("</AdaptationSet>")[0] for set_split in data.split("<AdaptationSet") if f'mimeType="{av}/mp4"' in set_split][0]
        seg_tmp = cut(a_set, "<SegmentTemplate", "</SegmentTemplate>")
        init = cut(seg_tmp,'initialization="','"')
        media = cut(seg_tmp,'media="','"')
        start_num =  int(cut(seg_tmp,'startNumber="','"'))
        print("Quality options not implemented yet, defaulting to highest...") ###TODO
        try: rep_id, base_url = sorted([(cut(r,'id="','"'), cut(r,"<BaseURL>","</BaseURL>"), int(cut(r,'bandwidth="','"'))) for r in a_set.split("<Representation")[1:]], key=lambda x: x[-1])[-1][:-1]
        except: rep_id, base_url = sorted([(cut(r,'id="','"'), base_url0, int(cut(r,'bandwidth="','"'))) for r in a_set.split("<Representation")[1:]], key=lambda x: x[-1])[-1][:-1]
        print(base_url+init.replace("$RepresentationID$", rep_id))
        open(os.path.join(f"{av}_tmp", f"{av}0000.m4{av[0]}"), "wb").write(session.get(base_url+init.replace("$RepresentationID$", rep_id)).content)
        seg_tl = cut(seg_tmp,"<SegmentTimeline>","</SegmentTimeline>")
        segs = [segToDict(s) for s in seg_tl.split("<S")[1:]]
        sn = 1
        num_segs = int(math.fsum([s["n"] for s in segs]))
        print(f"Downloading {av} segments...")
        for si in range(len(segs)):
            for i in range(segs[si]["n"]):
                open(os.path.join(f"{av}_tmp", f"{av}{sn:04}.m4{av[0]}"), "wb").write(session.get(base_url+media.replace("$RepresentationID$",rep_id).replace("$Number$",str(start_num+sn-1))).content)
                print(f"{sn} of {num_segs} done...")
                sn += 1
    merge_clean(fp)

if localizeToUs():
    animeString = session.get("https://crunchyroll.com/videos/anime/alpha?group=all").text
    soup = BeautifulSoup(animeString, "html.parser")
    animeList = [(a["title"], a["href"]) for a in soup.find_all("a", {"class": "text-link ellipsis"})]
    while True:
        sameLangForAll = None
        sameResForAll = None
        for a in range(len(animeList)):
            print(f"{a}: {animeList[a][0]}")
        seasonString = session.get(f"https://crunchyroll.com{animeList[int(input('Anime > '))][1]}").text
        soup = BeautifulSoup(seasonString, "html.parser")
        seasonList = []
        episodeList = []
        if soup.find("ul", {"class": "list-of-seasons cf"}).find("li")["class"] == ["season"]:
            episodeList = [(e.find("img")["alt"], e["href"]) for e in soup.find("li", {"class": "season"}).find_all("a")]
        else:
            seasonList = [(s.find("a")["title"], [(e.find("img")["alt"], e["href"]) for e in s.find_all("a")[1:]]) for s in soup.find_all("li", {"class": "season small-margin-bottom"})]
        if len(seasonList) > 0:
            for s in range(len(seasonList)):
                print(f"{s}: {seasonList[s][0]}")
            episodeList = seasonList[int(input("Season > "))][1]
        episodesToDownload = []
        while True:
            print("-1: Start Download")
            for e in range(len(episodeList)):
                print(f"{e}: {episodeList[len(episodeList)-e-1][0]}")
            i = int(input("Episode > "))
            if i == -1:
                break
            elif not episodeList[len(episodeList)-i-1] in episodesToDownload:
                episodesToDownload.append(episodeList[len(episodeList)-i-1])
        file_dest = input("Download destination: ")
        for e in episodesToDownload:
            videodata = json.loads(session.get(f"https://crunchyroll.com{e[1]}").text.split("vilos.config.media = ")[1].split(";\n")[0])
            #with open("videodata.json", "w", encoding="utf-8") as f:
            #    json.dump(videodata, f, ensure_ascii=False, indent=4)
            streams = videodata["streams"]
            currTitle = f"Episode {videodata['metadata']['display_episode_number']} - {videodata['metadata']['title']}"
            print(f"--------{currTitle}--------")
            subtitleList = []
            for s in [s0 for s0 in streams if s0["format"] in ["adaptive_hls", "adaptive_dash"]]:
                subtitleList.append((f"{s['hardsub_lang']} ({s['format'].replace('adaptive_','')})", s["url"]))
            i = 0
            if type(sameLangForAll) == str:
                i = [sl[0] for sl in subtitleList].index(sameLangForAll)
            else:
                for sl in range(len(subtitleList)):
                    print(f"{sl}: {subtitleList[sl][0]}")
                i = int(input("Subtitle Language > "))
                if sameLangForAll == None:
                    sameLangForAll = [False, subtitleList[i][0]][input("Use same subtitle language for all? (y/n): ").lower() == "y"]
            subdata = subtitleList[i]
            if subdata[0].endswith("(hls)"):
                sameResForAll = downloadHLS(subdata[1], os.path.join(file_dest, f"{currTitle}.ts"), sameResForAll)
            else:
                downloadDash(subdata[1], os.path.join(file_dest, f"{currTitle}.mp4"))
print("Initialization failed!")
