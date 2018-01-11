import argparse, sys, os, re
from pprint import pprint
from airPLS import airPLS
import numpy
from scipy import signal
from clint.textui import prompt, puts, colored, validators, indent
_version = '1.0'

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


def main(argv):
    puts("Welcome to Sab Spectra %s" % (_version))
    with indent(4):
        puts("""
             Sab Spectra takes raman(x) and intensity(y) in CSV txt files separated by tabs and outputs averaged\n
             and baselined data through several methods.
         """)
    dataDirs = {}
    addMoreData = False
    while len(dataDirs) < 1 or addMoreData:
        contineAdding = True
        dataName = prompt.query("Data Name:")
        if dataName in dataDirs:
            puts(colored.yellow("WARNING: '%s' already exists in data list" % (dataName, )))
            contineAdding = prompt.yn("Edit '%s' Data Settings?" % (dataName, ))
        if contineAdding:
            dataInputDir = prompt.query("Data Input Directory:", validators=[validators.PathValidator()])
            dataOutputDir = prompt.query("Data Output Directory:", validators=[validators.PathValidator()])

            dataDirs[dataName] = {
                'input': dataInputDir,
                'output': dataOutputDir
            }
            #Weirdly clint compares answer against default in order to return boolean
            addMoreData = not prompt.yn('Add More Data?', default='n')

    exit()
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
    inputPathBasename = os.path.basename(args.input)
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
        dirAvgFileName = "dir_%s_methodB_smooth%d_porder%d_maxit%d_v%%d.csv" % (inputPathBasename, args.smooth, args.porder, args.max_it)
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
