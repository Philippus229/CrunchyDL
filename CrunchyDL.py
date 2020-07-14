import os, math, json, time, shutil, requests, subprocess
from urllib.parse import quote
from urllib import request
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

localizeToUS = True
log_in = False #False recommended for mpeg-dash and even then it's extremely slow (will (hopefully) soon be fixed)
dlmode = True #True=download, False=watch in browser

textmode = False
file_dest = "test"#input("Output directory: ")
if not os.path.isdir("tmp"): os.mkdir("tmp")

options = Options()
#options.add_argument("--headless")
options.add_experimental_option("prefs", {
    "download.default_directory": os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "tmp")).replace("/","\\"),
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})
driver = webdriver.Chrome(options=options)

session = requests.Session()
session.headers.update({"User-Agent": driver.execute_script("return navigator.userAgent")})

username, password = open("credentials.cfg", "r").read().split("\n") if os.path.isfile("credentials.cfg") else (input("Username: "), input("Password: "))
if not os.path.isfile("credentials.cfg"):
    if input("Remember me? (y/n): ").lower() == "y":
        open("credentials.cfg", "w").write(f"{username}\n{password}")

servers = ["https://cr-unblocker.us.to/start_session?version=1.1"]

def login():
    if localizeToUS:
        for server in servers:
            try: sessionData = session.get(server).json()["data"]
            except: sessionData = None
            if sessionData and sessionData["country_code"] == "US":
                session.cookies.set("session_id", sessionData["session_id"])
                session.cookies.set("c_locale", "enUS")
                data = session.post(f"https://api.crunchyroll.com/login.0.json?session_id={sessionData['session_id']}&locale=enUS&account={quote(username)}&password={quote(password)}").json()["data"]
                print(data)
                if data:
                    print("Logged in (US)!")
                    driver.get("https://crunchyroll.com")
                    for name, value in session.cookies.items():           #somehow this actually works pretty well
                        driver.add_cookie({"name": name, "value": value}) #didn't think setting cookies would be enough
                else:
                    print("Login failed!")
    else:
        '''driver.get("https://crunchyroll.com/login")
        driver.find_element_by_id("login_form_name").send_keys(username)
        driver.find_element_by_id("login_form_password").send_keys(username)
        driver.find_element_by_id("login_form_password").submit()'''
        driver.get("https://www.crunchyroll.com")
        for cookie in driver.get_cookies():
            session.cookies.set(cookie["name"], cookie["value"])
        data = session.post(f"https://api.crunchyroll.com/login.0.json?session_id={session.cookies['session_id']}&account={quote(username)}&password={quote(password)}").json()["data"]
        for name, value in session.cookies.items():
            driver.add_cookie({"name": name, "value": value})
        print("Probably logged in!")

if log_in or localizeToUS: login()

def cut(string, cut0, cut1, rev=0):
    return string.split(cut0)[1-rev].split(cut1)[rev]

def segToDict(seg):
    tmp_dict = {s.split('="')[0]:int(cut(s,'="','"')) for s in seg.split(" ") if "=" in s}
    tmp_dict["n"] = tmp_dict["r"]+1 if "r" in tmp_dict else 1
    return tmp_dict

def retrieveURL0(url, mode="r", fp=None): #TODO: find a way to disable the video player in chrome
    for f in os.listdir("tmp"): os.remove(os.path.join("tmp", f))
    driver.get(url)
    while len(os.listdir("tmp")) in [0,2]: time.sleep(0.5) #wait for download to finish
    time.sleep(1)
    filename = os.listdir("tmp")[-1]
    content = open(os.path.join("tmp", filename), mode).read()
    if fp: shutil.copyfile(os.path.join("tmp", filename), fp)
    return content

def retrieveURL1(url, mode="r", fp=None, headers={}):
    for cookie in driver.get_cookies():
        session.cookies.set(cookie["name"], cookie["value"])
    res = session.get(url, headers=headers)
    if fp: open(fp, "wb").write(res.content)
    content = res.text if mode == "r" else res.content if mode == "rb" else res.text
    return content

def retrieveURL(url, mode="r", fp=None, thing=log_in):
    return retrieveURL0(url, mode, fp) if thing else \
           retrieveURL1(url, mode, fp,
                        headers={"Accept": "*/*",
                                 "Accept-Encoding": "gzip, deflate, br",
                                 "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
                                 "Connection": "keep-alive",
                                 "Host": cut(url,"//","/"),
                                 "Origin": "https://static.crunchyroll.com",
                                 "Referer": "https://static.crunchyroll.com/vilos-v2/web/vilos/player.html?control=1&advancedsettings=1",
                                 "Sec-Fetch-Dest": "empty",
                                 "Sec-Fetch-Mode": "cors",
                                 "Sec-Fetch-Site": "cross-site"})

def downloadHLS(url, filepath, sameResForAll):
    test3 = retrieveURL(url, fp="test.m3u8", thing=True).split("\n")
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

def downloadDash(url, fp):
    data = retrieveURL(url, fp="test.mpd")
    base_url0 = cut(data,"<BaseURL>","</BaseURL>") if "<BaseURL>" in data \
                else url.split("manifest.mpd")[0].replace("&amp;","&").replace("dl.","") #temporary, probably gonna make a dictionary (or try to figure out a way to read response headers with selenium (maybe switch to selenium-requests?))
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
        retrieveURL(base_url+init.replace("$RepresentationID$", rep_id),
                    fp=os.path.join(f"{av}_tmp", f"{av}0000.m4{av[0]}"))
        seg_tl = cut(seg_tmp,"<SegmentTimeline>","</SegmentTimeline>")
        segs = [segToDict(s) for s in seg_tl.split("<S")[1:]]
        sn = 1
        num_segs = int(math.fsum([s["n"] for s in segs]))
        print(f"Downloading {av} segments...")
        for si in range(len(segs)):
            for i in range(segs[si]["n"]):
                retrieveURL(base_url+media.replace("$RepresentationID$",rep_id).replace("$Number$",str(start_num+sn-1)),
                            fp=os.path.join(f"{av}_tmp", f"{av}{sn:04}.m4{av[0]}"))
                print(f"{sn} of {num_segs} done...")
                sn += 1
    merge_clean(fp)

def downloadEpisodes(episodes, sameLangForAll, sameResForAll):
    for episode in episodes:
        if episode != driver.current_url:
            driver.get(episode)
        videodata = json.loads(driver.page_source.split("vilos.config.media = ")[1].split(";\n")[0])
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
                sameLangForAll = subtitleList[i][0] if input("Use same subtitle language for all? (y/n): ").lower() == "y" else False
        subdata = subtitleList[i]
        if subdata[0].endswith("(hls)"):
            sameResForAll = downloadHLS(subdata[1], os.path.join(file_dest, f"{currTitle}.ts"), sameResForAll)
        else:
            downloadDash(subdata[1], os.path.join(file_dest, f"{currTitle}.mp4"))

running = lambda: driver.get_log("driver")[-1]["message"] != "Unable to evaluate script: disconnected: not connected to DevTools\n"

if not os.path.isdir(file_dest):
    os.mkdir(file_dest)
driver.get("https://www.crunchyroll.com/videos/anime/alpha?group=all")
if dlmode and not textmode:
    print("Navigate to an episode and the download will automatically start")
while running:
    if dlmode:
        if textmode:
            animeList = driver.find_elements_by_xpath("//a[@class='text-link ellipsis']")
            for a in range(len(animeList)):
                print(f"{a}: {animeList[a].text}")
            driver.get(animeList[int(input("Anime > "))].get_attribute("href"))
            seasonList = driver.find_elements_by_class_name("season")
            episodeList = []
            if len(seasonList) == 1:
                episodeList = seasonList[0].find_elements_by_class_name("episode")
            elif len(seasonList) > 1:
                for s in range(len(seasonList)):
                    print(f"{s}: {seasonList[s].find_element_by_class_name('season-dropdown').get_attribute('title')}")
                episodeList = seasonList[int(input("Season > "))].find_elements_by_class_name("episode")
            episodesToDownload = []
            while True:
                print("-1: Start Download")
                for e in range(len(episodeList)):
                    print(f"{e}: {episodeList[len(episodeList)-e-1].find_element_by_tag_name('img').get_attribute('alt')}")
                i = int(input("Episode > "))
                if i == -1: break
                elif not episodeList[len(episodeList)-i-1].get_attribute("href") in episodesToDownload:
                    episodesToDownload.append(episodeList[len(episodeList)-i-1].get_attribute("href"))
            downloadEpisodes(episodesToDownload, None, None)
        else:
            if "/episode-" in driver.current_url and "vilos.config.media = " in driver.page_source:
                downloadEpisodes([driver.current_url], False, False)
    else:
        time.sleep(1)
