# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='screensaver.video')
__addonid__ = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (__addon__.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join(dir, file):
    # Check if it ends in a slash
    if dir.endswith("/") or dir.endswith("\\"):
        # Remove the slash character
        dir = dir[:-1]

    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)


# Checks if a directory exists (Do not use for files)
def dir_exists(dirpath):
    directoryPath = dirpath
    # The xbmcvfs exists interface require that directories end in a slash
    # It used to be OK not to have the slash in Gotham, but it is now required
    if (not directoryPath.endswith("/")) and (not directoryPath.endswith("\\")):
        dirSep = "/"
        if "\\" in directoryPath:
            dirSep = "\\"
        directoryPath = "%s%s" % (directoryPath, dirSep)
    return xbmcvfs.exists(directoryPath)


##############################
# Stores Various Settings
##############################
class Settings():
    # ["Aquarium 3  - [6.6GB] - 1080p", "Aquarium003-1080p.mkv", ""]
    # ["Aquarium 4  - [10GB]  - 1080p", "Aquarium003-1080p.mkv", ""]
    PRESET_VIDEOS = (
        ["Aquarium 1  - [846MB] - 400p", "Aquarium001.mkv", "https://onedrive.live.com/download?resid=80BD16963F5C21B5!127&authkey=!ALex8PkcwV8LVJg"],
        ["Aquarium 2  - [2.7GB] - 720p", "Aquarium002-720p.mkv", "https://onedrive.live.com/download?resid=80BD16963F5C21B5!128&authkey=!APnNfC8YAC20UmE"],
        ["Fireplace 1 - [965MB] - 720p", "Fireplace001-720p.mkv", "https://onedrive.live.com/download?resid=80BD16963F5C21B5!129&authkey=!AGEezA6TTGU_urM"],
        ["Fireplace 2 - [827MB] - 480p", "Fireplace002.mkv", "https://onedrive.live.com/download?resid=80BD16963F5C21B5!130&authkey=!AOf_ClWmjzqkouQ"],
        ["Fireplace 3 - [2.1GB] - 1080p", "Fireplace03-1080p.mkv", "https://onedrive.live.com/download?resid=80BD16963F5C21B5!131&authkey=!ACZmSAeDTUxdz20"]
    )

    @staticmethod
    def getScreensaverVideo():
        return __addon__.getSetting("screensaverFile").decode("utf-8")

    @staticmethod
    def setScreensaverVideo(screensaverFile):
        __addon__.setSetting("screensaverFile", screensaverFile)

    @staticmethod
    def setPresetVideoSelected(id):
        if (id is not None) and (id != -1):
            __addon__.setSetting("displaySelected", Settings.PRESET_VIDEOS[id][0])
