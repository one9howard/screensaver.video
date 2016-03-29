# -*- coding: utf-8 -*-
import sys
import os
import urllib
import urlparse
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

            # TODO: Also add an option to delete
            url = self._build_url({'mode': 'download', 'name': videoItem['name'], 'filename': videoItem['filename'], 'primary': videoItem['primary'], 'secondary': videoItem['secondary']})

            xbmcplugin.addDirectoryItem(handle=self.addon_handle, url=url, listitem=li, isFolder=False)

        xbmcplugin.endOfDirectory(self.addon_handle)

    def download(self, name, filename, primary, secondary):
        pass


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
