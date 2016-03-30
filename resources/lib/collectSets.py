# -*- coding: utf-8 -*-
import traceback
import base64
import xml.etree.ElementTree as ET
import xbmc
import xbmcaddon
import xbmcvfs

__addon__ = xbmcaddon.Addon(id='screensaver.video')
__addonid__ = __addon__.getAddonInfo('id')
__icon__ = __addon__.getAddonInfo('icon')

# Import the common settings
from settings import log
from settings import os_path_join


class CollectSets():
    def __init__(self):
        addonRootDir = xbmc.translatePath('special://profile/addon_data/%s' % __addonid__).decode("utf-8")
        self.collectSetsFile = os_path_join(addonRootDir, 'collectsets.xml')
        self.disabledVideosFile = os_path_join(addonRootDir, 'disabled.xml')
        self.tempDir = os_path_join(addonRootDir, 'temp')
        self.videoDir = os_path_join(addonRootDir, 'videos')

    def getCollections(self):
        collectionMap = {}
        # Add the default set of collections
        collectionsDir = __addon__.getAddonInfo('path').decode("utf-8")
        collectionsDir = xbmc.translatePath(os_path_join(collectionsDir, 'resources')).decode("utf-8")

        collectionsDir = os_path_join(collectionsDir, 'collections')
        collectionMap['Aquarium'] = os_path_join(collectionsDir, 'aquarium.xml')
        collectionMap['Beach'] = os_path_join(collectionsDir, 'beach.xml')
        collectionMap['Clock'] = os_path_join(collectionsDir, 'clock.xml')
        collectionMap['Fireplace'] = os_path_join(collectionsDir, 'fireplace.xml')
        collectionMap['Miscellaneous'] = os_path_join(collectionsDir, 'miscellaneous.xml')
        collectionMap['Snow'] = os_path_join(collectionsDir, 'snow.xml')
        collectionMap['Space'] = os_path_join(collectionsDir, 'space.xml')
        collectionMap['Waterfall'] = os_path_join(collectionsDir, 'waterfall.xml')

        # http://a1.phobos.apple.com/us/r1000/000/Features/atv/AutumnResources/videos/entries.json
        collectionMap['Apple TV'] = os_path_join(collectionsDir, 'appletv.xml')

        # Check if the collections file exists
        if xbmcvfs.exists(self.collectSetsFile):
            # Load the file
            pass

        return collectionMap

    def loadCollection(self, collectionFile):
        log("CollectSets: Loading collection %s" % collectionFile)
        if not xbmcvfs.exists(collectionFile):
            log("CollectSets: Failed to load collection file: %s" % collectionFile, xbmc.LOGERROR)
            return None

        # Load all of the videos that are disabled
        disabledVideos = self.getDisabledVideos()

        collectionDetails = None
        try:
            # Load the file as a string
            collectionFileRef = xbmcvfs.File(collectionFile, 'r')
            collectionStr = collectionFileRef.read()
            collectionFileRef.close()

            collectionElem = ET.ElementTree(ET.fromstring(collectionStr))

            collectionName = collectionElem.find('collection')
            if collectionName in [None, ""]:
                return None

            collectionDetails = {'name': None, 'videos': []}
            collectionDetails['name'] = collectionName.text

            log("CollectSets: Collection Name is %s" % collectionDetails['name'])

            isEncoded = False
            encodedElem = collectionElem.getroot().find('encoded')
            if encodedElem not in [None, ""]:
                if encodedElem.text == 'true':
                    isEncoded = True

            # Get the videos that are in the collection
            for elemItem in collectionElem.findall('video'):
                video = {'name': None, 'filename': None, 'image': __icon__, 'duration': None, 'primary': None, 'secondary': None, 'enabled': True}

                nameElem = elemItem.find('name')
                if nameElem not in [None, ""]:
                    video['name'] = nameElem.text

                filenameElem = elemItem.find('filename')
                if filenameElem not in [None, ""]:
                    video['filename'] = filenameElem.text

                imageElem = elemItem.find('image')
                if imageElem not in [None, ""]:
                    video['image'] = imageElem.text

                durationElem = elemItem.find('duration')
                if durationElem not in [None, "", 0]:
                    video['duration'] = int(durationElem.text)

                primaryElem = elemItem.find('primary')
                if nameElem not in [None, ""]:
                    if isEncoded:
                        video['primary'] = base64.b64decode(primaryElem.text)
                    else:
                        video['primary'] = primaryElem.text

                secondaryElem = elemItem.find('secondary')
                if secondaryElem not in [None, ""]:
                    if isEncoded:
                        video['secondary'] = base64.b64decode(secondaryElem.text)
                    else:
                        video['secondary'] = secondaryElem.text

                # Check if this video is in the disabled list
                if video['filename'] in disabledVideos:
                    video['enabled'] = False

                collectionDetails['videos'].append(video)
        except:
            log("CollectSets: Failed to read collection file %s" % collectionFile, xbmc.LOGERROR)
            log("CollectSets: %s" % traceback.format_exc(), xbmc.LOGERROR)

        return collectionDetails

    # Gets the files that have been recorded as disabled
    def getDisabledVideos(self):
        disabledVideos = []
        # Check if the disabled videos file exists
        if not xbmcvfs.exists(self.disabledVideosFile):
            log("CollectSets: No disabled videos file exists")
            return disabledVideos

        try:
            # Load the file as a string
            disabledVideosFileRef = xbmcvfs.File(self.disabledVideosFile, 'r')
            disabledVideosStr = disabledVideosFileRef.read()
            disabledVideosFileRef.close()

            disabledVideosElem = ET.ElementTree(ET.fromstring(disabledVideosStr))

            # Expected XML format:
            # <disabled_screensaver>
            #     <filename></filename>
            # </disabled_screensaver>

            # Get the videos that are in the disabled list
            for filenameItem in disabledVideosElem.getroot().findall('filename'):
                disabledFile = filenameItem.text

                log("CollectSets: Disabled video file: %s" % disabledFile)
                disabledVideos.append(disabledFile)
        except:
            log("CollectSets: Failed to read collection file %s" % self.disabledVideosFile, xbmc.LOGERROR)
            log("CollectSets: %s" % traceback.format_exc(), xbmc.LOGERROR)

        log("CollectSets: Number of disabled videos is %d" % len(disabledVideos))
        return disabledVideos

    def saveDisabledVideos(self, disabledVideos):
        log("CollectSets: Saving %d disabled videos" % len(disabledVideos))
        # <disabled_screensaver>
        #     <filename></filename>
        # </disabled_screensaver>
        try:
            root = ET.Element('disabled_screensaver')

            for disabledVideo in disabledVideos:
                filenameElem = ET.SubElement(root, 'filename')
                filenameElem.text = disabledVideo

            fileContent = ET.tostring(root, encoding="UTF-8")

            # Save the XML file to disk
            recordFile = xbmcvfs.File(self.disabledVideosFile, 'w')
            recordFile.write(fileContent)
            recordFile.close()
        except:
            log("CollectSets: Failed to create XML Content %s" % traceback.format_exc(), xbmc.LOGERROR)
