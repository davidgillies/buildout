"""Bootstrap a buildout-based project.
$Id$
"""

from optparse import OptionParser
import atexit
import os
import shutil
import subprocess
import sys
import tempfile
import urllib2

parser = OptionParser(usage="python bootstrap.py\n\n"
                      "Bootstrap the installation process.",
                      version="bootstrap.py $Revision$")
parser.add_option(
    "--setuptools", dest="setuptools", action='store_true',
    help="use setuptools instead of distribute")
parser.add_option(
    "--buildout-config", dest="config", default="buildout.cfg",
    help="specify buildout configuration file to use, default to buildout.cfg")
parser.add_option(
    "--buildout-profile", dest="profile",
    help="specify a buildout profile to extends as configuration")
parser.add_option(
    "--buildout-version", dest="buildout_version", default="1.4.4",
    help="specify version of zc.buildout to use, default to 1.4.4")
parser.add_option(
    "--install", dest="install", action="store_true", default=False,
    help="directly start the install process after bootstrap")
parser.add_option(
    "--virtualenv", dest="virtualenv", action="store_true", default=False,
    help="create a virtualenv to install the software. " \
        "This is recommended if you don't need to rely on globally installed " \
        "libraries")

options, args = parser.parse_args()

bin_dir = 'bin'
if sys.platform.startswith('win'):
    bin_dir = 'Scripts'

tmp_eggs = tempfile.mkdtemp()
atexit.register(shutil.rmtree, tmp_eggs)
to_reload = False
try:
    import pkg_resources
    # Verify it is distribute
    if ((not options.setuptools) and
        (not hasattr(pkg_resources, '_distribute'))):
        to_reload = True
        raise ImportError
except ImportError:
    # Install setup tools or distribute
    setup_url = 'http://dist.infrae.com/thirdparty/distribute_setup.py'
    if options.setuptools:
        setup_url = 'http://peak.telecommunity.com/dist/ez_setup.py'
    ez = {}
    ez_options = {'to_dir': tmp_eggs, 'download_delay': 0}
    if not options.setuptools:
        ez_options['no_fake'] = True
    exec urllib2.urlopen(setup_url).read() in ez
    ez['use_setuptools'](**ez_options)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources


def execute(cmd, env=None, stdout=None):
    if sys.platform == 'win32':
        quoted = [cmd[0]]
        for arg in cmd[1:]:
            if arg and arg[0] != '-':
                arg = '"%s"' & arg
            quoted.append(arg)
        cmd = quoted
    return subprocess.call(cmd, env=env, stdout=stdout)


def install(requirement):
    print "Installing %s ..." % requirement
    if options.setuptools:
        egg = 'setuptools'
    else:
        egg = 'distribute'
    cmd = 'from setuptools.command.easy_install import main; main()'
    cmd_path = pkg_resources.working_set.find(
        pkg_resources.Requirement.parse(egg)).location
    if execute(
        [sys.executable, '-c', cmd, '-mqNxd', tmp_eggs, requirement],
        env={'PYTHONPATH': cmd_path}, stdout=subprocess.PIPE):
        sys.stderr.write(
            "\n\nFatal error while installing %s\n" % requirement)
        sys.exit(1)

    pkg_resources.working_set.add_entry(tmp_eggs)
    pkg_resources.working_set.require(requirement)


if options.virtualenv:
    python_path = os.path.join(bin_dir, os.path.basename(sys.executable))
    if not os.path.isfile(python_path):
        install('virtualenv >= 1.5')
        import virtualenv
        print "Running virtualenv"
        args = sys.argv[:]
        sys.argv = ['bootstrap', os.getcwd(),
                    '--clear', '--no-site-package', '--distribute']
        virtualenv.main()
        execute([python_path] + args)
        sys.exit(0)


if options.profile:
    if not os.path.isfile(options.profile):
        sys.stderr.write('No such profile file: %s\n' % options.profile)
        sys.exit(1)

    print "Creating configuration '%s'" % os.path.abspath(options.config)
    config = open(options.config, 'w')
    config.write("""[buildout]
extends = %s
""" % options.profile)
    config.close()


install('zc.buildout == %s' % options.buildout_version)
import zc.buildout.buildout
zc.buildout.buildout.main(['-c', options.config, 'bootstrap'])


if options.install:
    print "Start installation ..."
    # Run install
    execute(
        [sys.executable, os.path.join(bin_dir, 'buildout'),
         '-c', options.config, 'install'])

sys.exit(0)
