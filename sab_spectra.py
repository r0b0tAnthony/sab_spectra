import argparse, sys
_version = '0.1'
def getArgs():
    argEpilog = 'sab_spectra smooths, averages, and baselines multiple spectra datasets. Version %s' % _version
    parser = argparse.ArgumentParser(version=_version, prog='sab_spectra.py', epilog=argEpilog)

    return parser.parse_args()


def main(argv):
    getArgs()

if __name__ == '__main__':
    main(sys.argv)
