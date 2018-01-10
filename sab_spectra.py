import argparse, sys, os, re
from pprint import pprint
from airPLS import airPLS
import numpy
from scipy import signal
_version = '0.1'

def nextVersionPath(root_path, file_format, version=1):
    version_path = getVersionPath(root_path, file_format, version)
    while os.path.exists(version_path):
        version += 1
        version_path = getVersionPath(root_path, file_format, version)
    return version_path

def getVersionPath(root_path, file_format, version):
    return os.path.join(root_path, file_format % (version))

def printData(outputData, outputPath, format = 'CSV'):
    with open(outputPath, 'w') as dataFile:
        for data in outputData:
            dataFile.write("%f,%f\n" % data)

def isArgDir(arg):
    if not os.path.isdir(arg):
        raise argparse.ArgumentTypeError("'%s' is not a directory")
    return arg

def getArgs():
    argEpilog = "sab_spectra Version %s. MIT License" % _version
    argDescription = "sab_spectra takes in XY(raman shift, intensity) from a directory of text files formatted in two side by side columns with white-space delimiters. Output is a directory with two sub-directories for 'method-a' and 'method-b' proccessing of the data. See README.md for description of processing methods."
    parser = argparse.ArgumentParser(version=_version, prog='sab_spectra.py', epilog=argEpilog, description=argDescription)
    parser.add_argument(
        '-i',
        '--input',
        action='store',
        type=isArgDir,
        help='Input directory of text files containing raman shift in column 1(x) and intensity in column 2(y)'
    )
    parser.add_argument(
        '-o',
        '--output',
        action='store',
        type=str,
        required=True,
        help='Output directory where a method-a and method-b folder will be generated with the input data. See README.md for method-a and method-b explanations.'
    )
    parser.add_argument(
        '--min',
        action='store',
        type=float,
        default=0.0,
        help='Raman shift(x) minimum value to start at. Default is 0.0. Type required is float.'
    )
    parser.add_argument(
        '--max',
        action='store',
        type=float,
        default=4000.0,
        help='Raman shift(x) maximum value to end at. Default is 4000.0. Type required is float.'
    )
    parser.add_argument(
        '--smooth',
        action='store',
        type=int,
        default=100,
        help='Lambda setting that smoothes airPLS baseline data.'
    )
    parser.add_argument(
        '--max_it',
        action='store',
        type=int,
        default=15,
        help='AirPLS baseline iteration function parameter'
    )
    parser.add_argument(
        '--porder',
        action='store',
        type=int,
        default=1,
        help='AirPLS: adaptive iteratively reweighted penalized least squares for baseline fitting'
    )
    parser.add_argument(
        '--method',
        action='store',
        type=str,
        required=True,
        choices=['a', 'b', 'ab'],
        help="""
        Method of how the data is processed. Method 'a' will output individual baselined files and an average of all baselines.
        Method 'b' will average all the data and then baseline that avg.
        Method 'ab' combines both methods 'a' and 'b'.
        """
    )

    return parser.parse_args()


def main(argv):
    args = getArgs()
    dataRe = re.compile('^(?P<ramanShift>\d+\.\d+)\s+(?P<intensity>\d+\.\d+)$')
    if args.min >= args.max:
        raise argparse.ArgumentError('--max', 'Your float value for --max must be greater than your --min value.')
    data = {}
    dirData = {'raman': [], 'intensity': []}
    for fileName in os.listdir(args.input):
        if fileName[-3:] == 'txt':
            filePath = os.path.join(args.input, fileName)
            with open(filePath, 'r') as dataFile:
                print "Reading In File: %s" % filePath
                filteredDataRaman = []
                filteredDataIntensity = []
                i = 0
                for line in dataFile:
                    line = line.strip()
                    dataMatch = dataRe.match(line)
                    if dataMatch:
                        ramanShift = float(dataMatch.group('ramanShift'))
                        if ramanShift >= args.min and ramanShift <= args.max:
                            filteredDataRaman.append(ramanShift)
                            intensity = float(dataMatch.group('intensity'))
                            filteredDataIntensity.append(intensity)
                            try:
                                dirData['raman'][i] = ramanShift
                                dirData['intensity'][i].append(intensity)
                            except IndexError:
                                dirData['raman'].append(ramanShift)
                                dirData['intensity'].append([intensity])
                            i += 1
                if len(filteredDataRaman) > 1:
                    data[fileName] = {
                        'raman': numpy.array(filteredDataRaman),
                        'intensity': {
                            'original': numpy.array(filteredDataIntensity)
                        }
                    }
                else:
                    print 'WARNING: Not enough data after filtering %s between %f and %f' % (filePath, args.min, args.max)
    outputPath = os.path.abspath(args.output)
    print 'Creating Output Directory: %s' % (outputPath,)
    try:
        os.makedirs(outputPath)
    except OSError as e:
        if e[0] == 17 or e[0] == 183:
            pass
        else:
            print e[0]
            raise
    if 'b' in args.method:
        print 'Running Method B: Averaging All Data and Then Baselining'
        dirAvg = numpy.array(dirData['intensity']).mean(axis=1)
        dirAvgBaseline = airPLS.airPLS(dirAvg, lambda_=args.smooth, porder=args.porder, itermax=args.max_it)
        dirAvgSubtracted = numpy.subtract(dirAvg, dirAvgBaseline)
        dirAvgFileName = "dir_methodB_smooth%d_porder%d_maxit%d_v%%d.csv" % (args.smooth, args.porder, args.max_it)
        dirAvgPath = nextVersionPath(outputPath, dirAvgFileName)

        printData(zip(dirData['raman'], dirAvgSubtracted), dirAvgPath)
        print 'Saved Method B to: ', dirAvgPath
        exit()
    for dataFileName, inputData in data.iteritems():
        pprint(inputData['intensity']['original'])
        smoothedData = signal.savgol_filter(inputData['intensity']['original'], 29, 4, mode='nearest')
        pprint(smoothedData)
        airData = airPLS.airPLS(inputData['intensity']['original'], lambda_=args.smooth, porder=args.porder, itermax=args.max_it)
        subtractedData = numpy.subtract(inputData['intensity']['original'], airData)
        inputData['intensity']['airpls'] = subtractedData
        dataFileNameAir = "%s_airPLS_smooth%d_maxit%d_porder%d_v%%d.csv" % (os.path.splitext(dataFileName)[0], args.smooth, args.max_it, args.porder)
        dataPathAir = nextVersionPath(outputPath, dataFileNameAir)
        originalMatrix = zip(inputData['raman'], inputData['intensity']['original'])
        airMatrix = zip(inputData['raman'], subtractedData)
        printData(zip(inputData['raman'], airData), os.path.join(outputPath, 'air_baseline.csv'))
        printData(originalMatrix, os.path.join(outputPath, dataFileName))
        printData(airMatrix, dataPathAir)
        break

if __name__ == '__main__':
    main(sys.argv)
