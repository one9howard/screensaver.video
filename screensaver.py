# -*- coding: utf-8 -*-
import sys
import os
import random
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs


__addon__ = xbmcaddon.Addon(id='screensaver.video')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings


class ScreensaverWindow(xbmcgui.WindowXMLDialog):
    TIME_CONTROL = 3002

    # Static method to create the Window class
    @staticmethod
    def createScreensaverWindow():
        return ScreensaverWindow("screensaver-video-main.xml", __cwd__)

    # Called when setting up the window
    def onInit(self):
        xbmcgui.WindowXML.onInit(self)

        # Get the videos to use as a screensaver
        playlist = self._getPlaylist()
        # If there is nothing to play, then exit now
        if playlist is None:
            self.close()
            return

        # Now play the video
        xbmc.Player().play(playlist)

        # Set the video to loop, as we want it running as long as the screensaver
        xbmc.executebuiltin("PlayerControl(RepeatAll)")
        log("Started playing")

        # Now check to see if we are overlaying the time on the screen
        # Default is hidden
        timeControl = self.getControl(ScreensaverWindow.TIME_CONTROL)
        timeControl.setVisible(Settings.isShowTime())

        # Check if we need to start at a random location
        if Settings.isRandomStart() and xbmc.Player().isPlaying():
            duration = int(xbmc.Player().getTotalTime())
            log("Screensaver video has a duration of %d" % duration)

            if duration > 10:
                randomStart = random.randint(0, int(duration * 0.75))
                log("Setting random start to %d" % randomStart)
#                xbmc.Player().seekTime(randomStart)
                xbmc.Player().seekTime(randomStart)

    # Handle any activity on the screen, this will result in a call
    # to close the screensaver window
    def onAction(self, action):
        log("Action received: %s" % str(action.getId()))
        # For any action we want to close, as that means activity
        self.close()

    # The user clicked on a control
    def onClick(self, control):
        log("OnClick received")
        self.close()

    # A request to close the window has been made, tidy up the screensaver window
    def close(self):
        log("Ending Screensaver")
        # Exiting, so stop the video
        if xbmc.Player().isPlayingVideo():
            log("Stopping screensaver video")
            # There is a problem with using the normal "xbmc.Player().stop()" to stop
            # the video playing if another addon is selected - it will just continue
            # playing the video because the call to "xbmc.Player().stop()" will hang
            # instead we use the built in option
            xbmc.executebuiltin("PlayerControl(Stop)")

        log("Closing Window")
        xbmcgui.WindowXML.close(self)

    # Generates the playlist to use for the screensaver
    def _getPlaylist(self):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()
        videoFile = Settings.getScreensaverVideo()

        if (videoFile is None):
            videoFile == ""

        # Check to make sure the screensaver video file exists
        if (videoFile == "") or (not xbmcvfs.exists(videoFile)):
            log("No Screensaver file set or not valid %s" % videoFile)
            cmd = 'XBMC.Notification("{0}", "{1}")'.format(__addon__.getLocalizedString(32300), videoFile)
            xbmc.executebuiltin(cmd)
            return None

        log("Screensaver video is: %s" % videoFile)
        playlist.add(videoFile)

        return playlist

##################################
# Main of the Video Screensaver
##################################
if __name__ == '__main__':
    screenWindow = ScreensaverWindow.createScreensaverWindow()
    # Now show the window and block until we exit
    screenWindow.doModal()
    del screenWindow
    log("Leaving Screensaver Script")
