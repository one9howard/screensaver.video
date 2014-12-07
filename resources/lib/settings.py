# -*- coding: utf-8 -*-
import xbmc
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='screensaver.video')
__addonid__ = __addon__.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (__addon__.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (__addonid__, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


##############################
# Stores Various Settings
##############################
class Settings():
    @staticmethod
    def getScreensaverVideo():
        return __addon__.getSetting("screensaverFile").decode("utf-8")
