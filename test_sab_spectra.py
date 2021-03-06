import unittest, os
import sab_spectra, numpy
from pprint import pprint
from airPLS import airPLS

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
    def test_getVersionPath(self):
        absPath = os.path.abspath(os.path.curdir)
        testBaseName = "test_sub_folder_v%d"
        versionPath = sab_spectra.getVersionPath(absPath, testBaseName, 1)
        self.assertEqual(os.path.join(absPath, testBaseName % 1), versionPath)
    def test_parseDataLine(self):
        rawLine = '10.203   5.24'
        dataLine = sab_spectra.parseDataLine(rawLine)
        self.assertEqual({'ramanShift': 10.203, 'intensity': 5.24}, dataLine)

        rawLine = "10.203\t\t5.24"
        dataLine = sab_spectra.parseDataLine(rawLine)
        self.assertEqual({'ramanShift': 10.203, 'intensity': 5.24}, dataLine)

    def test_parseDataLine_invalid(self):
        rawLine = '10.203.5.6'
        dataLine = sab_spectra.parseDataLine(rawLine)
        self.assertFalse(dataLine)

        rawLine = '.56  5.6'
        dataLine = sab_spectra.parseDataLine(rawLine)
        self.assertFalse(dataLine)

        rawLine = 'meow  12.63'
        dataLine = sab_spectra.parseDataLine(rawLine)
        self.assertFalse(dataLine)

        rawLine ="meow10.203  \t5.24woof"
        dataLine = sab_spectra.parseDataLine(rawLine)
        self.assertFalse(dataLine)

    def test_filterDataLine(self):
        rawLine = '10.203  5.24'
        dataLine = sab_spectra.filterDataLine(0, 200, rawLine)
        self.assertEqual({'ramanShift': 10.203, 'intensity': 5.24}, dataLine)

    def test_filterDataLine_invalid(self):
        rawLine = '215.6  5.24'
        dataLine = sab_spectra.filterDataLine(0, 200, rawLine)
        self.assertFalse(dataLine)

        rawLine = '215.6  5.24'
        dataLine = sab_spectra.filterDataLine(250, 300, rawLine)
        self.assertFalse(dataLine)

    def test_baselineData(self):
        data = numpy.array([5.6, 3.5, 4.2, 9.5, 200.6, 53.5, 120.32])
        baseline = airPLS.airPLS(data, lambda_=100, porder=3, itermax=15)
        baselinedData = numpy.subtract(data, baseline)
        sabBaselinedData, sabBaseline = sab_spectra.baselineData(data, 100, 3, 15)

        numpy.testing.assert_almost_equal(sabBaselinedData, baselinedData)
        numpy.testing.assert_almost_equal(sabBaseline, baseline)

    def test_setSettings(self):
        settings = sab_spectra.setSettings()
        defaultSettings = {
            'method': 'b',
            'min': 0.0,
            'max': 4000.0,
            'smooth': 100,
            'max_it': 15,
            'porder': 1,
            'prec': 14,
            'formats': ['csv']
        }
        self.assertEqual(settings, defaultSettings)

        newSettings = {
            'method': 'ab',
            'min': 200.0,
            'max': 4500.0,
            'smooth': 300,
            'max_it': 10,
            'porder': 3,
            'prec': 5,
            'formats': ['csv', 'txt']
        }
        settings = sab_spectra.setSettings(method='ab', xmin=200.0, xmax=4500.0, smooth=300, max_it=10, porder=3, prec=5, formats=['csv', 'txt'])
        self.assertEqual(newSettings, settings)

    def test_formatData(self):
        dataset = [(10.65432299, 200), (3000.000567, 159.6543297654901)]
        csvFormat = sab_spectra.formatData(dataset, 'csv', 4)
        self.assertListEqual(['10.6543,200.0000\n', '3000.0006,159.6543\n'], csvFormat)

        txtFormat = sab_spectra.formatData(dataset, 'txt', 4)
        self.assertListEqual(['10.6543\t200.0000\n', '3000.0006\t159.6543\n'], txtFormat)

        self.assertRaises(ValueError, sab_spectra.formatData, dataset, 'foobar', 4)

    def test_writeData(self):
        outputData = [(numpy.float64(10.5), numpy.float64(3.5)), (numpy.float64(4.6), numpy.float64(8.9))]
        expectedOutput = {
            'csv': ['10.5000,3.5000', '4.6000,8.9000'],
            'txt': ['10.5000\t3.5000', '4.6000\t8.9000']
        }
        for format in expectedOutput.keys():
            outputFile = "./test/test_printData." + format
            formattedData = sab_spectra.formatData(outputData, format, 4)
            sab_spectra.writeData(formattedData, outputFile)

            with open(outputFile) as r:
                self.assertEqual(r.readline().strip(), expectedOutput[format][0])
                self.assertEqual(r.readline().strip(), expectedOutput[format][1])

            os.remove(outputFile)
if __name__ == '__main__':
    unittest.main()
