import argparse, sys, os, re
from pprint import pprint
from airPLS import airPLS
import numpy
from scipy import signal
from clint.textui import prompt, puts, colored, validators, indent
from sab_clint import validators as sab_validators
_version = '1.0'

dataRe = re.compile('^(?P<ramanShift>\d+\.\d+)\s+(?P<intensity>\d+\.\d+)$')

def nextVersion(root_path, file_format, version=1):
    version_path = getVersionPath(root_path, file_format, version)
    while os.path.exists(version_path):
        version += 1
        version_path = getVersionPath(root_path, file_format, version)
    return version

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

def printDataSets(allDataSets):
    for dataState, dataSets in allDataSets.iteritems():
        if dataState == 'active':
            puts(colored.green("Active:"))
        else:
            puts(colored.red("Inactive:"))
        with indent(4):
            if len(dataSets) < 1:
                puts('No Data Sets')
                continue
            for dataSetName, dataSetSettings in dataSets.iteritems():
                puts("Data Set Name: %s" % dataSetName)
                with indent(4):
                    puts("Input: %s" % dataSetSettings['input'])
                    puts("Output: %s" % dataSetSettings['output'])
def modifySettings(settings):
    putSeparator()
    puts('Modify Settings:')
    with indent(4):
        invalidSettings = True
        while invalidSettings:
            settings['method'] = prompt.query('Output Method:', default=settings['method'], validators=[validators.RegexValidator(regex=re.compile('[a-b]+'))])
            settings['min'] = prompt.query('Minimum X Value:', default="%f" % settings['min'], validators=[sab_validators.FloatValidator()])
            settings['max'] = prompt.query('Max X Value:', default="%f" % settings['max'], validators=[sab_validators.FloatValidator()])
            if settings['min'] > settings['max']:
                puts(colored.red('Minimum X value can not be larger than Maximum X value!'))
                continue
            settings['smooth'] = prompt.query('AirPLS Smoothing:', default=str(settings['smooth']), validators=[validators.IntegerValidator()])
            settings['max_it'] = prompt.query('AirPLS Max Iterations:', default=str(settings['max_it']), validators=[validators.IntegerValidator()])
            settings['porder'] = prompt.query('AirPLS POrder:', default=str(settings['porder']), validators=[validators.IntegerValidator()])

            invalidSettings = False

def modifyDataSets(dataSets):
    putSeparator()
    puts("Modify Data Sets:")
    putSeparator('-', 10)
    printDataSets(dataSets)
    putSeparator('-', 10)
    modifyingData = True
    while modifyingData or len(dataSets['active']) < 1:
        contineEditing = True
        dataName = prompt.query("Data Set Name:")
        if dataName in dataSets['active'] or dataName in dataSets['inactive']:
            puts(colored.yellow("WARNING: '%s' already exists in data list" % (dataName, )))
            contineEditing = prompt.yn("Edit '%s' Data Settings?" % (dataName, ))
        if contineEditing:
            try:
                defaultInput = dataSets['active'][dataName]['input']
                defaultOutput = dataSets['active'][dataName]['output']
            except KeyError:
                try:
                    defaultInput = dataSets['inactive'][dataName]['input']
                    defaultOutput = dataSets['inactive'][dataName]['output']
                except KeyError:
                    defaultInput = ''
                    defaultOutput = ''
            dataInputDir = prompt.query("Data Input Directory:", default=defaultInput, validators=[sab_validators.PathValidator()])
            dataOutputDir = prompt.query("Data Output Directory:", validators=[sab_validators.PathValidator()], default=defaultOutput)
            dataState = 'active' if prompt.yn("Active:") else 'inactive'

            dataSets['active'].pop(dataName, None)
            dataSets['inactive'].pop(dataName, None)

            dataSets[dataState][dataName] = {
                'input': dataInputDir,
                'output': dataOutputDir
            }
            #Weirdly clint compares answer against default in order to return boolean
            modifyingData = not prompt.yn('Continue Modifying Data Sets?', default='n')

def putSeparator(char='=', length=20):
    separator = char * length
    puts("\n%s\n" % separator)

def mainMenu(totalDataSets, settings):
    editSettingsPrompt = "Edit Settings(Min: %(min)f, Max: %(max)f, Method: %(method)s, Smooth: %(smooth)d, POrder: %(porder)d, Max It: %(max_it)d)" % settings
    menuOptions = [
        {'selector': '1', 'prompt': "Data Sets(Total: %d)" % totalDataSets},
        {'selector': '2', 'prompt': editSettingsPrompt},
        {'selector': '3', 'prompt': 'Process Data Sets'},
        {'selector': '4', 'prompt': 'Quit Sab Spectra'}
    ]
    putSeparator()
    return prompt.options('Main Menu:', menuOptions, default='3')

def dataSetsMenu(dataSets):
    putSeparator()
    puts("Current Data Sets:")
    with indent(4):
        printDataSets(dataSets)

    putSeparator('-', 10)

    menuOptions = [
        {'selector': '1', 'prompt': 'Modify Data Sets'},
        {'selector': '2', 'prompt': 'Back to Main Menu'}
    ]

    return prompt.options('Data Sets Menu:', menuOptions, default='1')

def processDataFile(dataSetFileName, dataSetFilePath, dataOutputPath, dataSetData, settings, fileVersion):
    puts("Processing Data File %s:" % dataSetFilePath)
    fileNameBase = os.path.splitext(dataSetFileName)[0]
    with indent(4):
        dataSetData['files'][dataSetFileName] = filterDataFile(settings['min'], settings['max'], dataSetFilePath, dataSetData['dir'])
        dataSetFileData = dataSetData['files'][dataSetFileName]
        airData = airPLS.airPLS(dataSetFileData['intensity']['filtered'], lambda_=settings['smooth'], porder=settings['porder'], itermax=settings['max_it'])
        baselinedData = numpy.subtract(dataSetFileData['intensity']['filtered'], airData)
        try:
            for i,value in enumerate(baselinedData):
                try:
                    dataSetData['dir']['intensity']['baselined'][i].append(value)
                except IndexError:
                    dataSetData['dir']['intensity']['baselined'].append([value])
        except KeyError:
            pass

        dataSetFileData['intensity']['airpls'] = baselinedData
        dataFileNameAir = "%s_airPLS_smooth%d_maxit%d_porder%d_v%%d.csv" % (fileNameBase, settings['smooth'], settings['max_it'], settings['porder'])
        dataPathAir = getVersionPath(dataOutputPath, dataFileNameAir, fileVersion)
        filteredMatrix = zip(dataSetFileData['raman'], dataSetFileData['intensity']['filtered'])
        dataFilteredFileName = "%s_filtered_v%%d.csv" % (fileNameBase)
        dataFilteredPath = getVersionPath(dataOutputPath, dataFilteredFileName, fileVersion)
        baselinePath = getVersionPath(dataOutputPath, 'air_baseline_v%d.csv', fileVersion)
        airMatrix = zip(dataSetFileData['raman'],  baselinedData)
        printData(filteredMatrix, dataFilteredPath)
        puts('Saved Filtered To: %s' % dataFilteredPath)
        printData(zip(dataSetFileData['raman'], airData), baselinePath)
        puts('Saved Baseline To: %s' % baselinePath)
        printData(airMatrix, dataPathAir)
        puts('Saved Baseline Subtracted To: %s' % dataPathAir)




def filterDataFile(xmin, xmax, dataSetFilePath, dirData):
    global dataRe
    filteredDirRaman = dirData['raman']
    filteredDirIntensity = dirData['intensity']['filtered']
    with open(dataSetFilePath, 'r') as dataFile:
        puts('Filtering')
        filteredDataRaman = []
        filteredDataIntensity = []
        i = 0
        for line in dataFile:
            line = line.strip()
            dataMatch = dataRe.match(line)
            if dataMatch:
                ramanShift = float(dataMatch.group('ramanShift'))
                if ramanShift >= xmin and ramanShift <= xmax:
                    filteredDataRaman.append(ramanShift)
                    intensity = float(dataMatch.group('intensity'))
                    filteredDataIntensity.append(intensity)
                    try:
                        filteredDirRaman[i] = ramanShift
                        filteredDirIntensity[i].append(intensity)
                    except IndexError:
                        filteredDirRaman.append(ramanShift)
                        filteredDirIntensity.append([intensity])
                    i += 1
        if len(filteredDataRaman) > 1:
            return {
                'raman': numpy.array(filteredDataRaman),
                'intensity': {
                    'filtered': numpy.array(filteredDataIntensity)
                }
            }
        else:
            puts(colored.yellow('WARNING: Not enough data after filtering %s between %f and %f' % (filePath, xmin, xmax)))

def processDataSet(dataSetName, dataSet, settings):
    puts('Processing Data Set: %s' % dataSetName)
    dataSet['data'] = {
        'files': {},
        'dir': {
            'raman': [],
            'intensity': {'filtered': []}
        }
    }
    if 'a' in settings['method']:
        dataSet['data']['dir']['intensity']['baselined'] = []
    outputPathBaseName = "%s_v%%d" % dataSetName.replace(' ', '_').lower()
    fileVersion = nextVersion(os.path.abspath(dataSet['output']), outputPathBaseName)
    outputPath = getVersionPath(os.path.abspath(dataSet['output']), outputPathBaseName, fileVersion)
    puts('Creating Output Directory: %s' % (outputPath,))
    try:
        os.makedirs(outputPath)
    except OSError as e:
        if e[0] == 17 or e[0] == 183:
            pass
        else:
            print e[0]
            raise
    inputPathBasename = os.path.basename(dataSet['input'])
    with indent(4):
        for fileName in os.listdir(dataSet['input']):
            if fileName[-3:] == 'txt':
                processDataFile(fileName,  os.path.join(dataSet['input'], fileName), outputPath, dataSet['data'], settings, fileVersion)

        if len(dataSet['data']['dir']['raman']) > 0:
            if 'b' in settings['method']:
                puts("Running Method B: Averaging All Data and Then Baselining")
                dirAvg = numpy.array(dataSet['data']['dir']['intensity']['filtered']).mean(axis=1)
                dirAvgBaseline = airPLS.airPLS(dirAvg, lambda_=settings['smooth'], porder=settings['porder'], itermax=settings['max_it'])
                dirAvgSubtracted = numpy.subtract(dirAvg, dirAvgBaseline)
                dirAvgFileName = "dir_%s_methodB_smooth%d_porder%d_maxit%d_v%%d.csv" % (inputPathBasename, settings['smooth'], settings['porder'], settings['max_it'])
                dirAvgPath = getVersionPath(outputPath, dirAvgFileName, fileVersion)
                printData(zip(dataSet['data']['dir']['raman'], dirAvgSubtracted), dirAvgPath)
                puts('Saved Method B to: %s' % dirAvgPath)
            if 'a' in settings['method']:
                puts('Running Method A: Averaging All Baselined Data and Then Baselining')
                methodAAvg = numpy.array(dataSet['data']['dir']['intensity']['baselined']).mean(axis=1)
                methodABaseline = airPLS.airPLS(methodAAvg, lambda_=settings['smooth'], porder=settings['porder'], itermax=settings['max_it'])
                methodASubtracted = numpy.subtract(methodAAvg, methodABaseline)
                methodAFileName = "dir_%s_methodA_smooth%d_porder%d_maxit%d_v%%d.csv" % (inputPathBasename, settings['smooth'], settings['porder'], settings['max_it'])
                methodAPath = getVersionPath(outputPath, methodAFileName, fileVersion)
                printData(zip(dataSet['data']['dir']['raman'], methodASubtracted), methodAPath)
                puts('Saved Method A to: %s' % methodAPath)
    putSeparator('-', 10)

def processDataSets(settings, dataSets):
    putSeparator()
    for dataSetName, dataSet in dataSets.iteritems():
        processDataSet(dataSetName, dataSet, settings)

def main(argv):
    puts("Welcome to Sab Spectra %s" % (_version))
    with indent(4):
        puts("""
             Sab Spectra takes raman(x) and intensity(y) in CSV txt files separated by tabs and outputs averaged\n
             and baselined data through several methods.
         """)

    defaultSettings = {
     'max': 4000,
     'min': 0,
     'smooth': 100,
     'max_it': 15,
     'porder': 1,
     'method': 'b'
    }
    settings = dict(defaultSettings)

    dataDirs = {'active': {}, 'inactive': {}}

    modifyDataSets(dataDirs)

    menuChoice = 0
    while menuChoice != '4':
        menuChoice = mainMenu(len(dataDirs['active']) + len(dataDirs['inactive']), settings)

        if menuChoice == '1':
            dataMenuChoice = dataSetsMenu(dataDirs)
            if dataMenuChoice == '1':
                modifyDataSets(dataDirs)
        elif menuChoice == '2':
            modifySettings(settings)
        elif menuChoice == '3':
            processDataSets(settings, dataDirs['active'])

    puts('Sab Spectra Quitting')
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
