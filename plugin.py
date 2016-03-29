# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urlparse
import traceback
import xbmc
import xbmcvfs
import xbmcgui
import xbmcplugin
import xbmcaddon

__addon__ = xbmcaddon.Addon(id='screensaver.video')
__icon__ = __addon__.getAddonInfo('icon')
__fanart__ = __addon__.getAddonInfo('fanart')
__cwd__ = __addon__.getAddonInfo('path').decode("utf-8")
__resource__ = xbmc.translatePath(os.path.join(__cwd__, 'resources').encode("utf-8")).decode("utf-8")
__lib__ = xbmc.translatePath(os.path.join(__resource__, 'lib').encode("utf-8")).decode("utf-8")


sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from collectSets import CollectSets


###################################################################
# Class to handle the navigation information for the plugin
###################################################################
class MenuNavigator():
    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle

    # Creates a URL for a directory
    def _build_url(self, query):
        return self.base_url + '?' + urllib.urlencode(query)

    # The root menu shows all of the available collections
    def rootMenu(self):
        collectionCtrl = CollectSets()
        collectionMap = collectionCtrl.getCollections()

        log("VideoScreensaverPlugin: Available Number of Collections is %d" % len(collectionMap))

        for collectionKey in sorted(collectionMap.keys()):
            li = xbmcgui.ListItem(collectionKey, iconImage=__icon__)
            li.setProperty("Fanart_Image", __fanart__)
            url = self._build_url({'mode': 'collection', 'name': collectionKey, 'link': collectionMap[collectionKey]})
            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=True)

        del collectionCtrl

        xbmcplugin.endOfDirectory(self.addon_handle)

    # Lists all the available videos for a given collection
    def viewCollection(self, name, link):
        log("VideoScreensaverPlugin: %s (%s)" % (name, link))

        collectionCtrl = CollectSets()
        collectionDetails = collectionCtrl.loadCollection(link)
        del collectionCtrl

        # If the file was not processed just don't display anything
        if collectionDetails in [None, ""]:
            return

        screensaverFolder = Settings.getScreensaverFolder()

        for videoItem in collectionDetails['videos']:
            # Create the list-item for this video
            li = xbmcgui.ListItem(videoItem['name'], iconImage=videoItem['image'])
            # Remove the default context menu
            li.addContextMenuItems([], replaceItems=True)

            # Set the background image
#             if videoItem['fanart'] is not None:
#                 li.setProperty("Fanart_Image", videoItem['fanart'])

            # If theme already exists flag it using the play count
            # This will normally put a tick on the GUI
            if screensaverFolder not in [None, ""]:
                videoLocation = os_path_join(screensaverFolder, videoItem['filename'])

                log("VideoScreensaverPlugin: Checking id %s already downloaded to %s" % (videoItem['filename'], videoLocation))
                if xbmcvfs.exists(videoLocation):
                    li.setInfo('video', {'PlayCount': 1})

            li.addContextMenuItems(self._getContextMenu(videoItem), replaceItems=True)

            # TODO: Also add an option to delete
            url = self._build_url({'mode': 'download', 'name': videoItem['name'], 'filename': videoItem['filename'], 'primary': videoItem['primary'], 'secondary': videoItem['secondary']})

            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def download(self, name, filename, primary, secondary):
        log("VideoScreensaverPlugin: Downloading %s" % name)

        tmpdestination = os_path_join(Settings.getTempFolder(), filename)
        destination = os_path_join(Settings.getScreensaverFolder(), filename)

        # Create a list of the links that can be used
        downloadURLs = [primary, secondary]

        # Check to see if there is already a file present
        if xbmcvfs.exists(destination):
            useExisting = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32005), __addon__.getLocalizedString(32301), name, __addon__.getLocalizedString(32302))
            if useExisting:
                # Don't want to overwrite, so nothing to do
                log("Download: Reusing existing video file %s" % destination)
                return
            else:
                log("Download: Removing existing file %s ready for fresh download" % destination)
                xbmcvfs.delete(destination)

        # Create a progress dialog for the  download
        downloadProgressDialog = xbmcgui.DialogProgress()
        downloadProgressDialog.create(__addon__.getLocalizedString(32303), name, filename, destination)

        # Callback method to report progress
        def _report_hook(count, blocksize, totalsize):
            percent = int(float(count * blocksize * 100) / totalsize)
            downloadProgressDialog.update(percent, name, filename, destination)

        showError = False
        downloadOK = False
        for downloadURL in downloadURLs:
            try:
                log("Download: Using server: %s" % downloadURL)

                # Now retrieve the actual file
                fp, h = urllib.urlretrieve(downloadURL, tmpdestination, _report_hook)
                log(h)

                # Check to make sure that the file created downloaded correctly
                st = xbmcvfs.Stat(tmpdestination)
                fileSize = st.st_size()
                log("Download: Size of file %s is %d" % (tmpdestination, fileSize))
                # Check for something that has a size greater than zero (in case some OSs do not
                # support looking at the size), but less that 1,000,000 (As all our files are
                # larger than that
                if (fileSize > 0) and (fileSize < 1000000):
                    log("Download: Detected that file %s did not download correctly as file size is only %d" % (downloadURL, fileSize))
                    if showError:
                        xbmcgui.Dialog().ok(__addon__.getLocalizedString(32005), __addon__.getLocalizedString(32306), __addon__.getLocalizedString(32307))
                else:
                    log("Download: Copy from %s to %s" % (tmpdestination, destination))
                    copy = xbmcvfs.copy(tmpdestination, destination)
                    if copy:
                        log("Download: Copy Successful")
                        downloadOK = True
                    else:
                        log("Download: Copy Failed")
                xbmcvfs.delete(tmpdestination)
            except:
                log("Download: Theme download Failed!!!", xbmc.LOGERROR)
                log("Download: %s" % traceback.format_exc(), xbmc.LOGERROR)
                if not showError:
                    log("Download: Trying different server", xbmc.LOGERROR)
            # If we have downloaded OK, there is no need to loop
            if downloadOK:
                break
            # If the second option fails then show the error
            showError = True

        # Make sure the progress dialog has been closed
        downloadProgressDialog.close()
        # Now reload the screen to reflect the change
        xbmc.executebuiltin("Container.Refresh")

    # Delete an existing file
    def delete(self, name, filename):
        log("VideoScreensaverPlugin: Deleting %s" % name)

        destination = os_path_join(Settings.getScreensaverFolder(), filename)

        # Check to see if there is already a file present
        if xbmcvfs.exists(destination):
            deleteFile = xbmcgui.Dialog().yesno(__addon__.getLocalizedString(32005), __addon__.getLocalizedString(32014), name)
            if deleteFile:
                log("Download: Removing existing file %s" % destination)
                xbmcvfs.delete(destination)
                # Now reload the screen to reflect the change
                xbmc.executebuiltin("Container.Refresh")
        else:
            log("VideoScreensaverPlugin: Files does not exists %s" % destination)

    def play(self, name, filename):
        log("VideoScreensaverPlugin: Playing %s" % name)

        destination = os_path_join(Settings.getScreensaverFolder(), filename)

        # Check to see if there is already a file present
        if xbmcvfs.exists(destination):
            player = xbmc.Player()
            player.play(destination)
            del player
        else:
            log("VideoScreensaverPlugin: Files does not exists %s" % destination)

    # Construct the context menu
    def _getContextMenu(self, videoItem):
        ctxtMenu = []

        # Check if the file has already been downloaded
        destination = os_path_join(Settings.getScreensaverFolder(), videoItem['filename'])
        if not xbmcvfs.exists(destination):
            # If not already exists, add a download option
            cmd = self._build_url({'mode': 'download', 'name': videoItem['name'], 'filename': videoItem['filename'], 'primary': videoItem['primary'], 'secondary': videoItem['secondary']})
            ctxtMenu.append((__addon__.getLocalizedString(32013), 'RunPlugin(%s)' % cmd))
        else:
            # If already exists then add a play option
            cmd = self._build_url({'mode': 'play', 'name': videoItem['name'], 'filename': videoItem['filename']})
            ctxtMenu.append((__addon__.getLocalizedString(32015), 'RunPlugin(%s)' % cmd))
            # If already exists then add a delete option
            cmd = self._build_url({'mode': 'delete', 'name': videoItem['name'], 'filename': videoItem['filename']})
            ctxtMenu.append((__addon__.getLocalizedString(32014), 'RunPlugin(%s)' % cmd))

        return ctxtMenu


######################################
# Main of the VideoScreensaver Plugin
######################################
if __name__ == '__main__':
    # Get all the arguments
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    args = urlparse.parse_qs(sys.argv[2][1:])

    # Record what the plugin deals with, files in our case
    xbmcplugin.setContent(addon_handle, 'files')

    # Get the current mode from the arguments, if none set, then use None
    mode = args.get('mode', None)

    log("VideoScreensaverPlugin: Called with addon_handle = %d" % addon_handle)

    # If None, then at the root
    if mode is None:
        log("VideoScreensaverPlugin: Mode is NONE - showing collection list")
        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.rootMenu()
        del menuNav

    elif mode[0] == 'collection':
        log("VideoScreensaverPlugin: Mode is collection")

        name = ''
        link = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        linkItem = args.get('link', None)
        if (linkItem is not None) and (len(linkItem) > 0):
            link = linkItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.viewCollection(name, link)
        del menuNav

    elif mode[0] == 'download':
        log("VideoScreensaverPlugin: Mode is download")

        name = ''
        filename = None
        primary = None
        secondary = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        filenameItem = args.get('filename', None)
        if (filenameItem is not None) and (len(filenameItem) > 0):
            filename = filenameItem[0]

        primaryItem = args.get('primary', None)
        if (primaryItem is not None) and (len(primaryItem) > 0):
            primary = primaryItem[0]

        secondaryItem = args.get('secondary', None)
        if (secondaryItem is not None) and (len(secondaryItem) > 0):
            secondary = secondaryItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.download(name, filename, primary, secondary)
        del menuNav

    elif mode[0] == 'delete':
        log("VideoScreensaverPlugin: Mode is delete")

        name = ''
        filename = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        filenameItem = args.get('filename', None)
        if (filenameItem is not None) and (len(filenameItem) > 0):
            filename = filenameItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.delete(name, filename)
        del menuNav

    elif mode[0] == 'play':
        log("VideoScreensaverPlugin: Mode is play")

        name = ''
        filename = None

        nameItem = args.get('name', None)
        if (nameItem is not None) and (len(nameItem) > 0):
            name = nameItem[0]

        filenameItem = args.get('filename', None)
        if (filenameItem is not None) and (len(filenameItem) > 0):
            filename = filenameItem[0]

        menuNav = MenuNavigator(base_url, addon_handle)
        menuNav.play(name, filename)
        del menuNav
