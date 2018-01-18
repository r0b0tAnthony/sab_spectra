import unittest, os
import sab_spectra

class SabSpectraTestCase(unittest.TestCase):
    """Tests for `sab_spectra.py`"""

    def test_nextVersion_nonExistentFolder(self):
        absPath = os.path.abspath(os.path.curdir)
        testBaseName = "test_sub_folder_v%d"
        firstFolder = os.path.join(absPath, testBaseName % (1,))
        print "Testing Path is Current Version: %s" % firstFolder
        version = sab_spectra.nextVersion(absPath, testBaseName)
        self.assertEqual(version, 1)

    def test_nextVersion_existingFolder(self):
        absPath = os.path.abspath(os.path.curdir)
        testBaseName = "test_sub_folder_v%d"
        firstFolder = os.path.join(absPath, testBaseName % (1,))
        print "Creating Folder: %s" % firstFolder
        os.makedirs(firstFolder)
        version = sab_spectra.nextVersion(absPath, testBaseName)
        self.assertEqual(version, 2)
        os.rmdir(firstFolder)
        print "Deleted Folder: %s" % firstFolder




if __name__ == '__main__':
    unittest.main()
