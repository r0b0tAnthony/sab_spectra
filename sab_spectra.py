import argparse, sys, os, re, copy
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
    putSeparator('-', 30)
    printDataSets(dataSets)
    putSeparator('-', 30)
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
            modifyingData = prompt.yn('Continue Modifying Data Sets?')

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

    putSeparator('-', 30)

    menuOptions = [
        {'selector': '1', 'prompt': 'Modify Data Sets'},
        {'selector': '2', 'prompt': 'Back to Main Menu'}
    ]

    return prompt.options('Data Sets Menu:', menuOptions, default='1')
def baselineData(data, smooth, porder, max_it):
    baseline = airPLS.airPLS(data, lambda_=smooth, porder=porder, itermax=max_it)
    baselinedData = numpy.subtract(data, baseline)
    return (baselinedData, baseline)

def processDataFile(dataSetFileName, dataSetFilePath, dataOutputPath, dataSetData, settings, fileVersion):
    puts("Processing Data File %s:" % dataSetFilePath)
    fileNameBase = os.path.splitext(dataSetFileName)[0]
    with indent(4, quote=' >'):
        dataSetData['files'][dataSetFileName] = filterDataFile(settings['min'], settings['max'], dataSetFilePath, dataSetData['dir'])
        dataSetFileData = dataSetData['files'][dataSetFileName]

        dataFilteredFileName = "%s_filtered_v%%d.csv" % (fileNameBase)
        dataFilteredPath = getVersionPath(dataOutputPath, dataFilteredFileName, fileVersion)
        printData(zip(dataSetFileData['raman'], dataSetFileData['intensity']['filtered']), dataFilteredPath)
        with indent(4, quote='>'):
            puts('Saved Filtered To: %s' % dataFilteredPath)

        puts('Baselining')
        baselinedData, airData = baselineData(dataSetFileData['intensity']['filtered'], settings['smooth'], settings['porder'], settings['max_it'])
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
        baselinePath = getVersionPath(dataOutputPath, 'air_baseline_v%d.csv', fileVersion)
        airMatrix = zip(dataSetFileData['raman'],  baselinedData)
        with indent(4, quote='>'):
            printData(zip(dataSetFileData['raman'], airData), baselinePath)
            puts('Saved Baseline To: %s' % baselinePath)
            printData(airMatrix, dataPathAir)
            puts('Saved Baseline Subtracted To: %s' % dataPathAir)
    putSeparator('-', 30)


def parseDataLine(line):
    global dataRe
    dataMatch = dataRe.match(line)
    if dataMatch:
        return {
            'ramanShift': float(dataMatch.group('ramanShift')),
            'intensity': float(dataMatch.group('intensity'))
        }
    else:
        return False

def filterDataLine(xmin, xmax, line):
    line = line.strip()
    dataMatch = parseDataLine(line)
    if dataMatch and dataMatch['ramanShift'] >= xmin and dataMatch['ramanShift'] <= xmax:
        return dataMatch
    else:
        return False


def filterDataFile(xmin, xmax, dataSetFilePath, dirData):
    filteredDirRaman = dirData['raman']
    filteredDirIntensity = dirData['intensity']['filtered']
    with open(dataSetFilePath, 'r') as dataFile:
        puts('Filtering')
        filteredDataRaman = []
        filteredDataIntensity = []
        i = 0
        for line in dataFile:
            dataMatch = filterDataLine(xmin, xmax, line)
            if dataMatch:
                filteredDataRaman.append(dataMatch['ramanShift'])
                filteredDataIntensity.append(dataMatch['intensity'])
                try:
                    filteredDirRaman[i] = dataMatch['ramanShift']
                    filteredDirIntensity[i].append(dataMatch['intensity'])
                except IndexError:
                    filteredDirRaman.append(dataMatch['ramanShift'])
                    filteredDirIntensity.append([dataMatch['intensity']])
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
        putSeparator('-', 30)
        puts('Created Output Directory: %s' % (outputPath,))
        putSeparator('-', 30)
        for fileName in os.listdir(dataSet['input']):
            if fileName[-3:] == 'txt':
                processDataFile(fileName,  os.path.join(dataSet['input'], fileName), outputPath, dataSet['data'], settings, fileVersion)

        if len(dataSet['data']['dir']['raman']) > 0:
            if 'b' in settings['method']:
                puts("Running Method B: Averaging All Data and Then Baselining")
                dirAvg = numpy.array(dataSet['data']['dir']['intensity']['filtered']).mean(axis=1)
                dirAvgBaseline, dirAvgSubtracted = baselineData(dirAvg, settings['smooth'], settings['porder'], settings['max_it'])
                dirAvgFileName = "dir_%s_methodB_smooth%d_porder%d_maxit%d_v%%d.csv" % (inputPathBasename, settings['smooth'], settings['porder'], settings['max_it'])
                dirAvgPath = getVersionPath(outputPath, dirAvgFileName, fileVersion)
                printData(zip(dataSet['data']['dir']['raman'], dirAvgSubtracted), dirAvgPath)
                with indent(4, quote='>'):
                    puts('Saved Method B to: %s' % dirAvgPath)
            if 'a' in settings['method']:
                puts('Running Method A: Averaging All Baselined Data and Then Baselining')
                methodAAvg = numpy.array(dataSet['data']['dir']['intensity']['baselined']).mean(axis=1)
                methodABaseline, methodASubtracted = baselineData(methodAAvg, settings['smooth'], settings['porder'], settings['max_it'])
                methodAFileName = "dir_%s_methodA_smooth%d_porder%d_maxit%d_v%%d.csv" % (inputPathBasename, settings['smooth'], settings['porder'], settings['max_it'])
                methodAPath = getVersionPath(outputPath, methodAFileName, fileVersion)
                printData(zip(dataSet['data']['dir']['raman'], methodASubtracted), methodAPath)
                with indent(4, quote='>'):
                    puts('Saved Method A to: %s' % methodAPath)
    putSeparator('-', 20)

def processDataSets(settings, dataSets):
    putSeparator()
    for dataSetName, dataSet in dataSets.iteritems():
        processDataSet(dataSetName, dataSet, settings)

def setSettings(method='b', xmin=0.0, xmax=4000.0, smooth=100, max_it=15, porder=1):
    if xmin > xmax:
        raise ValueError("Xmin(%f) Can Not Be Larger than Xmax(%f)" % (xmin, xmax))
    if 'a' not in method and 'b' not in method:
        raise ValueError("Invalid methods chosen. Please choose a, b, or a combination thereof.")

    return {
        'method': method,
        'min': float(xmin),
        'max': float(xmax),
        'smooth': smooth,
        'max_it': max_it,
        'porder': porder
    }

def main(argv):
    puts("Welcome to Sab Spectra %s" % (_version))
    with indent(4):
        puts("""
             Sab Spectra takes raman(x) and intensity(y) in CSV txt files separated by tabs and outputs averaged\n
             and baselined data through several methods.
         """)
    settings = setSettings()

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

if __name__ == '__main__':
    main(sys.argv)
