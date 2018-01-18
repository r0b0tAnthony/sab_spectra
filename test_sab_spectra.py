import unittest, os
import sab_spectra

class SabSpectraTestCase(unittest.TestCase):
    """Tests for `sab_spectra.py`"""

    def test_nextVersion_nonExistentFolder(self):
        absPath = os.path.abspath(os.path.curdir)
        testBaseName = "test_sub_folder_v%d"
        firstFolder = os.path.join(absPath, testBaseName % (1,))
        try:
            os.rmdir(firstFolder)
        except OSError:
            pass
        print "Testing Path is Current Version: %s" % firstFolder
        version = sab_spectra.nextVersion(absPath, testBaseName)
        self.assertEqual(version, 1)

    def test_nextVersion_existingFolders(self):
        absPath = os.path.abspath(os.path.curdir)
        testBaseName = "test_sub_folder_v%d"
        for i in range(1, 5):
            versionFolder = os.path.join(absPath, testBaseName % (i,))
            print "Creating Folder: %s" % versionFolder
            os.makedirs(versionFolder)
        nextVersion = sab_spectra.nextVersion(absPath, testBaseName)
        self.assertEqual(nextVersion, 5)
        for i in range(1, 5):
            versionFolder = os.path.join(absPath, testBaseName % (i,))
            print "Deleted Folder: %s" % versionFolder
            os.rmdir(versionFolder)




if __name__ == '__main__':
    unittest.main()
