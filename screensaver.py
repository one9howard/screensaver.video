# -*- coding: utf-8 -*-
import sys
import os
import random
import time
import traceback
import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json


__addon__ = xbmcaddon.Addon(id='screensaver.video')
__icon__ = __addon__.getAddonInfo('icon')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__lib__)

# Import the common settings
from settings import log
from settings import Settings
from settings import list_dir
from settings import os_path_join
from settings import dir_exists
from settings import os_path_isfile

from VideoParser import VideoParser


# Video Screensaver Player that can detect when the next item in a playlist starts
class VideoScreensaverPlayer(xbmc.Player):
    def __init__(self, *args):
        self.initialStart = True
        xbmc.Player.__init__(self, *args)

    def onPlayBackStarted(self):
        # The first item in a playlist will have already had it's start time
        # set correctly if it is a clock
        if self.initialStart is True:
            self.initialStart = False
            log("onPlayBackStarted received for initial video")
            return

        if self.isPlayingVideo():
            # Get the currently playing file
            filename = self.getPlayingFile()
            log("onPlayBackStarted received for file %s" % filename)

            duration = self._getVideoDuration(filename)
            log("onPlayBackStarted: Duration is %d for file %s" % (duration, filename))

            startTime = Settings.getTimeForClock(filename, duration)

            # Set the clock start time
            if startTime > 0 and duration > 10:
                self.seekTime(startTime)
        else:
            log("onPlayBackStarted received, but not playing video file")

        xbmc.Player.onPlayBackStarted(self)

    # Returns the duration in seconds
    def _getVideoDuration(self, filename):
        duration = 0
        try:
            # Parse the video file for the duration
            duration = VideoParser().getVideoLength(filename)
        except:
            log("Failed to get duration from %s" % filename, xbmc.LOGERROR)
            log("Error: %s" % traceback.format_exc(), xbmc.LOGERROR)
            duration = 0

        log("Duration retrieved is = %d" % duration)

        return duration


class ScreensaverWindow(xbmcgui.WindowXMLDialog):
    TIME_CONTROL = 3002
    DIM_CONTROL = 3003
    OVERLAY_CONTROL = 3004

    def __init__(self, *args, **kwargs):
        self.isClosed = False
        self.player = VideoScreensaverPlayer()
        # Create the scheduler that will store when each item should be played
        self.scheduler = Scheduler()
        self.currentScheduleItem = -1

    # Static method to create the Window class
    @staticmethod
    def createScreensaverWindow():
        return ScreensaverWindow("screensaver-video-main.xml", __cwd__)

    # Called when setting up the window
    def onInit(self):
        xbmcgui.WindowXML.onInit(self)
        self.volumeCtrl = None

        # Get the videos to use as a screensaver
        playlist = self._getPlaylist()
        # If there is nothing to play, then exit now
        if playlist is None:
            self.close()
            return

        # Update the playlist with any settings such as random start time
        self._updatePlaylistForSettings(playlist)

        # Update the volume if needed
        self.volumeCtrl = VolumeDrop()
        self.volumeCtrl.lowerVolume()

        # Now play the video
        self.player.play(playlist)

        # Set the video to loop, as we want it running as long as the screensaver
        self._setRepeat()
        log("Started playing")

        # Now check to see if we are overlaying the time on the screen
        # Default is hidden
        timeControl = self.getControl(ScreensaverWindow.TIME_CONTROL)
        timeControl.setVisible(Settings.isShowTime())

        # Set the value of the dimming for the video
        dimLevel = Settings.getDimValue()
        if dimLevel is not None:
            log("Setting Dim Level to: %s" % dimLevel)
            dimControl = self.getControl(ScreensaverWindow.DIM_CONTROL)
            dimControl.setColorDiffuse(dimLevel)

        # Set the overlay image
        self._setOverlayImage()

        # Update any settings that need to be done after the video is playing
        self._updatePostPlayingForSettings(playlist)

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

    def isComplete(self):
        return self.isClosed

    # A request to close the window has been made, tidy up the screensaver window
    def close(self):
        log("Ending Screensaver")
        # Exiting, so stop the video
        if self.player.isPlayingVideo():
            log("Stopping screensaver video")
            # There is a problem with using the normal "xbmc.Player().stop()" to stop
            # the video playing if another addon is selected - it will just continue
            # playing the video because the call to "xbmc.Player().stop()" will hang
            # instead we use the built in option
            xbmc.executebuiltin("PlayerControl(Stop)")

        # Reset the Player Repeat
        xbmc.executebuiltin("PlayerControl(RepeatOff)", True)

        if self.volumeCtrl is not None:
            # Restore the volume
            self.volumeCtrl.restoreVolume()
            self.volumeCtrl = None

        log("Closing Window")
        # Record that we are closing
        self.isClosed = True
        xbmcgui.WindowXML.close(self)

    # Generates the playlist to use for the screensaver
    def _getPlaylist(self):
        playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playlist.clear()

        # Check to see if we should be using a video from the schedule
        scheduleEntry = self.scheduler.getScheduleEntry()

        if scheduleEntry != -1:
            # There is an item scheduled, so check to see if the item has actually changed
            if scheduleEntry == self.currentScheduleItem:
                return None
            # Set the entry we are about to play
            self.currentScheduleItem = scheduleEntry
            # Get the actual video file that should be played
            scheduledVideo = self.scheduler.getScheduleVideo(scheduleEntry)
            # Do a quick check to see if the video exists
            if xbmcvfs.exists(scheduledVideo):
                log("Screensaver video for scheduled item %d is: %s" % (scheduleEntry, scheduledVideo))
                playlist.add(scheduledVideo)

        # Check if we are showing all the videos in a given folder
        elif Settings.isFolderSelection():
            videosFolder = Settings.getScreensaverFolder()
            if (videosFolder is None):
                videosFolder == ""

            # Check if we are dealing with a Folder of videos
            if videosFolder != "" and dir_exists(videosFolder):
                self.currentScheduleItem = -1
                dirs, files = list_dir(videosFolder)
                # Now shuffle the playlist to ensure that if there are more
                #  than one video a different one starts each time
                random.shuffle(files)
                for vidFile in files:
                    fullPath = os_path_join(videosFolder, vidFile)
                    log("Screensaver video in directory is: %s" % fullPath)
                    playlist.add(fullPath)
        else:
            # Must be dealing with a single file
            videoFile = Settings.getScreensaverVideo()
            if (videoFile is None):
                videoFile == ""

            # Check to make sure the screensaver video file exists
            if (videoFile != "") and xbmcvfs.exists(videoFile):
                self.currentScheduleItem = -1
                log("Screensaver video is: %s" % videoFile)
                playlist.add(videoFile)

        # If there are no videos in the playlist yet, then display an error
        if playlist.size() < 1:
            errorLocation = Settings.getScreensaverVideo()
            if Settings.isFolderSelection():
                errorLocation = Settings.getScreensaverFolder()

            log("No Screensaver file set or not valid %s" % errorLocation)
            cmd = 'Notification("{0}", "{1}", 3000, "{2}")'.format(__addon__.getLocalizedString(32300).encode('utf-8'), errorLocation, __icon__)
            xbmc.executebuiltin(cmd)
            return None

        return playlist

    # Apply any user setting to the created playlist
    def _updatePlaylistForSettings(self, playlist):
        if playlist.size() < 1:
            return playlist

        filename = playlist[0].getfilename()
        duration = self._getVideoDuration(filename)
        log("Duration is %d for file %s" % (duration, filename))

        startTime = 0

        # Check if we have a random start time
        if Settings.isRandomStart():
            startTime = random.randint(0, int(duration * 0.75))
            startTime = duration - 5

        clockStart = Settings.getTimeForClock(filename, duration)
        if clockStart > 0:
            startTime = clockStart

        # Set the random start
        if (startTime > 0) and (duration > 10):
            listitem = xbmcgui.ListItem()
            # Record if the theme should start playing part-way through
            listitem.setProperty('StartOffset', str(startTime))

            log("Setting start of %d for %s" % (startTime, filename))

            # Remove the old item from the playlist
            playlist.remove(filename)
            # Add the new item at the start of the list
            playlist.add(filename, listitem, 0)

        return playlist

    # Update anything needed once the video is playing
    def _updatePostPlayingForSettings(self, playlist):
        # Check if we need to start at a random location
        if Settings.isRandomStart() and playlist.size() > 0:
            # Need to reset the offset to the start so that if it loops
            # it will play from the start
            playlist[0].setProperty('StartOffset', "0")

    # Returns the duration in seconds
    def _getVideoDuration(self, filename):
        duration = 0
        try:
            # Parse the video file for the duration
            duration = VideoParser().getVideoLength(filename)
        except:
            log("Failed to get duration from %s" % filename, xbmc.LOGERROR)
            log("Error: %s" % traceback.format_exc(), xbmc.LOGERROR)
            duration = 0

        log("Duration retrieved is = %d" % duration)

        return duration

    # Set the overlay image to the correct value
    def _setOverlayImage(self):
        overlayImage = Settings.getOverlayImage()

        # Check if we should set the overlay image based on a schedule
        if self.currentScheduleItem != -1:
            overlayImage = self.scheduler.getScheduleOverlay(self.currentScheduleItem)

        overlayControl = self.getControl(ScreensaverWindow.OVERLAY_CONTROL)

        if overlayImage is not None:
            log("Setting Overlay Image to: %s" % overlayImage)
            overlayControl.setImage(overlayImage)
            overlayControl.setVisible(True)
        else:
            overlayControl.setVisible(False)

    def _setRepeat(self):
        # Set the video to loop, as we want it running as long as the screensaver
        repeatType = Settings.getFolderRepeatType()
        if repeatType is not None:
            log("Setting Repeat Type to %s" % repeatType)
            xbmc.executebuiltin("PlayerControl(%s)" % repeatType)

    def check(self):
        oldScheduleValue = self.currentScheduleItem

        # Check to see if there needs to be a change in what is playing
        # This will also update the schedule item so we know what has been selected
        newPlaylist = self._getPlaylist()

        # Check to see if the scheduled item has changed, if it has not then
        # there is nothing to do
        if oldScheduleValue == self.currentScheduleItem:
            return

        # If we reach here, there is a change of some sort
        if newPlaylist is not None:
            # Update the playlist with any settings such as random start time
            self._updatePlaylistForSettings(newPlaylist)

            # Start playing the new file, just override the existing one that is playing
            self.player.play(newPlaylist)

            # Also update the overlay
            self._setOverlayImage()

            # Now set the repeat option
            self._setRepeat()

            # Update any settings that need to be done after the video is playing
            self._updatePostPlayingForSettings(newPlaylist)


class VolumeDrop(object):
    def __init__(self, *args):
        self.screensaverVolume = Settings.getVolume()
        if self.screensaverVolume > -1:
            # Save the volume from before any alterations
            self.original_volume = self._getVolume()

    # This will return the volume in a range of 0-100
    def _getVolume(self):
        result = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Application.GetProperties", "params": { "properties": [ "volume" ] }, "id": 1}')

        json_query = json.loads(result)
        if ("result" in json_query) and ('volume' in json_query['result']):
            # Get the volume value
            volume = json_query['result']['volume']

        log("VolumeDrop: current volume: %s%%" % str(volume))
        return volume

    # Sets the volume in the range 0-100
    def _setVolume(self, newvolume):
        # Can't use the RPC version as that will display the volume dialog
        # '{"jsonrpc": "2.0", "method": "Application.SetVolume", "params": { "volume": %d }, "id": 1}'
        xbmc.executebuiltin('SetVolume(%d)' % newvolume, True)

    def lowerVolume(self):
        try:
            # If we are after a zero volume then we have the option to suspend
            # the Audio Engine
            if Settings.isUseAudioSuspend():
                xbmc.audioSuspend()
            elif self.screensaverVolume > -1:
                vol = self.screensaverVolume
                # Make sure the volume still has a value, otherwise we see the mute symbol
                if vol < 1:
                    vol = 1
                log("Player: volume goal: %d%%" % vol)
                self._setVolume(vol)
            else:
                log("Player: No reduced volume option set")
        except:
            log("VolumeDrop: %s" % traceback.format_exc(), xbmc.LOGERROR)

    def restoreVolume(self):
        try:
            if Settings.isUseAudioSuspend():
                xbmc.audioResume()
            # Don't change the volume unless requested to
            elif self.screensaverVolume > -1:
                self._setVolume(self.original_volume)
        except:
            log("VolumeDrop: %s" % traceback.format_exc(), xbmc.LOGERROR)


# Class to store all the schedule details and work out which video should
# be playing at a given time
class Scheduler(object):
    def __init__(self, *args):
        self.scheduleDetails = []

        # Collect together all of the scheduled videos
        numScheduleEntries = Settings.getNumberOfScheduleRules()
        log("Schedule: Number of schedule entries is %d" % numScheduleEntries)
        itemNum = 1
        while itemNum <= numScheduleEntries:
            videoFile = Settings.getRuleVideoFile(itemNum)
            if videoFile not in [None, ""]:
                # Support special paths like smb:// means that we can not just call
                # os.path.isfile as it will return false even if it is a file
                # (A bit of a shame - but that's the way it is)
                if videoFile.startswith("smb://") or os_path_isfile(videoFile):
                    overlayFile = Settings.getRuleOverlayFile(itemNum)
                    startTime = Settings.getRuleStartTime(itemNum)
                    endTime = Settings.getRuleEndTime(itemNum)
                    log("Schedule: Item %d (Start:%d, End:%d) contains video %s" % (itemNum, startTime, endTime, videoFile))
                    details = {'id': itemNum, 'start': startTime, 'end': endTime, 'video': videoFile, 'overlay': overlayFile}
                    self.scheduleDetails.append(details)
                else:
                    log("Schedule: File does not exist: %s" % videoFile)
            else:
                log("Schedule: Video file not set for entry %d" % itemNum)
            itemNum = itemNum + 1

    # Get the ID of which schedule should be used
    def getScheduleEntry(self):
        # Get the current time that we are checking the schedule for
        localTime = time.localtime()
        currentTime = (localTime.tm_hour * 60) + localTime.tm_min

        # Check the scheduled items to see if any cover the current time
        for item in self.scheduleDetails:
            if (item['start'] <= currentTime) and (item['end'] >= currentTime):
                return item['id']

        return -1

    # Get the video for a given Id
    def getScheduleVideo(self, id):
        videoFile = None
        # Find the entry matching this Id
        for item in self.scheduleDetails:
            if item['id'] == id:
                videoFile = item['video']
                break
        return videoFile

    # Get the overlay image for a given Id
    def getScheduleOverlay(self, id):
        imageFile = None
        # Find the entry matching this Id
        for item in self.scheduleDetails:
            if item['id'] == id:
                if item['overlay'] not in [None, ""]:
                    imageFile = item['overlay']
                break
        return imageFile


##################################
# Main of the Video Screensaver
##################################
if __name__ == '__main__':
    # Check for the case where the screensaver has been launched as a script
    # But needs to behave like the full screensaver, not just a video player
    # This is the case for things like screensaver.random
    if (len(sys.argv) > 1) and ("screensaver" in sys.argv[1]):
        # Launch the core screensaver script - this will ensure all the pre-checks
        # are done (like TvTunes) before running the screensaver
        log("Screensaver started by script with screensaver argument")
        xbmc.executebuiltin('RunScript(%s)' % (os.path.join(__cwd__, "default.py")))
    else:
        # Before we start, make sure that the settings have been updated correctly
        Settings.cleanAddonSettings()

        screenWindow = ScreensaverWindow.createScreensaverWindow()

        xbmcgui.Window(10000).setProperty("VideoScreensaverRunning", "true")

        try:
            # Now show the window and block until we exit
            screensaverTimeout = Settings.screensaverTimeout()
            numScheduleEntries = Settings.getNumberOfScheduleRules()

            if (screensaverTimeout < 1) and (numScheduleEntries < 1):
                log("Starting Screensaver in Modal Mode")
                screenWindow.doModal()
            else:
                log("Starting Screensaver in Show Mode")
                screenWindow.show()

                # The timeout is in minutes, and the sleep is in msec, so convert the
                # countdown into the correct "sleep units" which will be every 0.1 seconds
                checkInterval = 100
                countdown = screensaverTimeout * 60 * (1000 / checkInterval)

                # Now wait until the screensaver is closed
                while not screenWindow.isComplete():
                    xbmc.sleep(checkInterval)
                    if screensaverTimeout > 0:
                        # Update the countdown
                        countdown = countdown - 1
                        if countdown < 1:
                            log("Stopping Screensaver as countdown expired")
                            # Close the screensaver window
                            screenWindow.close()
                            # Reset the countdown to stop multiple closes being sent
                            countdown = 100
                    # Check to see if there is anything that needs to be done
                    # for the screensaver, like change the video on schedule
                    screenWindow.check()
        except:
            log("VideoScreensaver ERROR: %s" % traceback.format_exc(), xbmc.LOGERROR)

        xbmcgui.Window(10000).clearProperty("VideoScreensaverRunning")

        del screenWindow
        log("Leaving Screensaver Script")
