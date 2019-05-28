# coding: utf-8
import os
import platform
import re

import requests
from Crypto.Cipher import AES

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36"
}

request = requests.Session()
request.headers.update(headers)

playlist = "https://gw-yvpub.c.yimg.jp/v1/hls/VYvjHzaO2WyNuJc1/video.m3u8?min_bw=250&https=1"


# 获取 HOST
def get_host(url, only_host=False):
    if only_host:
        playlist = url.split("/")[1:3]
    else:
        playlist = url.split("/")[1:-1]
    uri = [_ for _ in playlist if _]
    host = "https://" + "/".join(uri) + "/"
    return host


# 获取最佳分辨率
def get_best_url(playlist):
    res = request.get(playlist, headers=headers)
    data = res.text
    # 提取 m3u8 所有的 URL
    rule_m3u8_url = r"^[\w\-\.\/\:\?\&\=\%\,\+]+"
    m3u8urls = re.findall(rule_m3u8_url, data, re.S | re.M)

    # 提取全部码率
    rule_bandwidth = r"BANDWIDTH=([\w]+)"
    bandwidth = re.findall(rule_bandwidth, data, re.S | re.M)
    bandwidth = [int(b) for b in bandwidth]

    # 提取最高码率的 m3u8 的 URL
    group = zip(m3u8urls, bandwidth)
    maxband = max(group, key=lambda x: x[1])
    m3u8_max_url = get_host(playlist) + maxband[0]
    return m3u8_max_url


# 获取 m3u8 的信息
def get_video_info(m3u8_url):
    res = request.get(m3u8_url, headers=headers)
    data = res.text
    # 提取 KEY 的 URL
    rule_key = r'URI=\"(.*?)\"'
    search_key = re.findall(rule_key, data)
    key_url = get_host(playlist, only_host=True) + "".join(search_key)

    # 提取 IV 的16进制字符串
    rule_iv = r'IV=0x([\w]+)'
    search_iv = re.findall(rule_iv, data)
    iv = "".join(search_iv)

    # 提取所有视频分片的 URL
    rule_video = r'[^#\S+][\w\/\-\.\:\?\&\=\,\+\%]+'
    search_video = re.findall(rule_video, data, re.S | re.M)
    videourls = [_.strip() for _ in search_video]

    download_info = {
        "keyurl": key_url,
        "iv": iv,
        "videos": videourls
    }
    return download_info


# AES-128-CBC 解密
def aes_decode(data, key, iv):
    cryptor = AES.new(key, AES.MODE_CBC, iv)
    data_dec = cryptor.decrypt(data)
    return data_dec


# 下载视频并解密合并
def download(info):
    keyurl = info["keyurl"]
    # 获取 KEY 的二进制
    key = request.get(keyurl).content
    # 转换 IV 为二进制
    iv = bytes.fromhex(info["iv"])
    vidoes = info["videos"]
    video_list = []
    print("Total {}".format(str(len(vidoes))))
    for index, vurl in enumerate(vidoes):
        print("Downloading video {}".format(index + 1))
        files = vurl.split("/")[-1]
        video_list.append(files)
        res = request.get(vurl)
        # 保存视频并解密
        with open(files, "wb") as code:
            data_dec = aes_decode(res.content, key, iv)
            code.write(data_dec)

    # 合并分片
    if 'Windows' in platform.system():
        videoin = "+".join(video_list)
        os.system("copy /B " + videoin + " " + "all_win.ts" + " >nul 2>nul")
    else:
        videoin = " ".join(video_list)
        os.system("cat " + videoin + " > all.ts")


if __name__ == "__main__":
    m3u8_best_url = get_best_url(playlist)
    m3u8_info = get_video_info(m3u8_best_url)
    download(m3u8_info)
