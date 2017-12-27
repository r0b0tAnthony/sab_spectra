import argparse, sys, os, re
from pprint import pprint
from airPLS import airPLS
import numpy
_version = '0.1'

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

    return parser.parse_args()


def main(argv):
    args = getArgs()
    dataRe = re.compile('^(?P<ramanShift>\d+\.\d+)\s+(?P<intensity>\d+\.\d+)$')
    if args.min >= args.max:
        raise argparse.ArgumentError('--max', 'Your float value for --max must be greater than your --min value.')
    data = {}
    for fileName in os.listdir(args.input):
        filePath = os.path.join(args.input, fileName)
        with open(filePath, 'r') as dataFile:
            print "Reading In File: %s" % filePath
            filteredDataRaman = []
            filteredDataIntensity = []
            for line in dataFile:
                line = line.strip()
                dataMatch = dataRe.match(line)
                if dataMatch:
                    ramanShift = float(dataMatch.group('ramanShift'))
                    if ramanShift >= args.min and ramanShift <= args.max:
                        filteredDataRaman.append(ramanShift)
                        filteredDataIntensity.append(float(dataMatch.group('intensity')))
            if len(filteredDataRaman) > 1:
                data[fileName] = {
                    'raman': numpy.array(filteredDataRaman),
                    'intensity': {
                        'original': numpy.array(filteredDataIntensity)
                    }
                }
                break
            else:
                print 'Not enough data after filtering %s between %f and %f' % (filePath, args.min, args.max)
    outputPath = os.path.abspath(args.output)
    print 'Creating Output Directory: %s' % (outputPath,)
    try:
        os.makedirs(outputPath)
    except OSError as e:
        if e[0] == 17:
            pass
        else:
            raise
    for dataFileName, inputData in data.iteritems():
        print dataFileName
        pprint(inputData['intensity']['original'])
        airData = airPLS.airPLS(inputData['intensity']['original'])
        pprint(airData)
        break

if __name__ == '__main__':
    main(sys.argv)
