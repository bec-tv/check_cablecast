#!/usr/bin/env python

import argparse
import logging
import sys
import urllib
import json
import datetime
import iso8601
import pytz # pip install pytz
from tzlocal import get_localzone # pip install tzlocal

# NAGIOS return codes :
# https://nagios-plugins.org/doc/guidelines.html#AEN78
OK       = 0
WARNING  = 1
CRITICAL = 2
UNKNOWN  = 3

mylogger = logging.getLogger(__name__)

def debug_factory(logger, debug_level):
   """
   Decorate logger in order to add custom levels for Nagios
   """
   def custom_debug(msg, *args, **kwargs):
       if logger.level >= debug_level:
           return
       logger._log(debug_level, msg, args, kwargs)
   return custom_debug


def get_args():
   """
   Supports the command-line arguments listed below.
   """
   parser = argparse.ArgumentParser(description="Nagios checks for TRMS Cablecast")
   parser._optionals.title = "Options"
   parser.add_argument('-s', '--server', nargs=1, required=True, help='full HTTP / HTTPS URL to Cablecast server', dest='host', type=str, default=['https://yourtown.cablecast.tv'])
   parser.add_argument('-l', '--location', nargs=1, required=False, help='Location ID (if used for requested command)', dest='location', type=int, default=[22])
   parser.add_argument('-t', '--test', nargs=1, required=True, help="name of test to run, one of 'ap_end'", dest='test', type=str, default=['ap_end'])
   parser.add_argument('-v', '--verbose', required=False, help='enable verbose output', dest='verbose', action='store_true')
   parser.add_argument('--log-file', nargs=1, required=False, help='file to log to (default = stdout)', dest='logfile', type=str)
   parser.add_argument('--nagios', required=False, help='enable Nagios output mode', dest='nagios_output', action='store_true')
   args = parser.parse_args()
   return args

def check_autopilot_send_end(host, location):
   target = '%s/cablecastapi/v1/autopilot/%d/stats' % (host, location)

   mylogger.debug("Requesting stats from : %s" % target)
   try:
      response = urllib.urlopen(target)
   except Exception as e:
      mylogger.critical("error while requesting stats.  error=%s" % e)
      sys.exit(UNKNOWN)

   try:
      data = json.loads(response.read())['autopilotSend']
   except Exce as e:
      mylogger.critical("error while parsing stats.  Incorrect cablecast version?  error=%s" % e)
      sys.exit(UNKNOWN)

   scheduleModified = data['scheduleModified']
   sendTo = iso8601.parse_date(data['end'])
   now = datetime.datetime.now(get_localzone())
   sendTimeRemaining = sendTo - now

   mylogger.debug('Autopilot send expires in %d seconds' % sendTimeRemaining.total_seconds())

   if sendTimeRemaining.total_seconds() <= 0:
     mylogger.critical('Autopilot send has expired')
     sys.exit(CRITICAL)
   elif sendTimeRemaining.total_seconds() < 3600:
     mylogger.warning('Autopilot send expires soon (at %d)' % sendTo)
     sys.exit(WARNING)
   else:
     mylogger.info('Autopilot send expires at %s' % sendTo.strftime("%m/%d/%Y %H:%M:%S"))
     sys.exit(OK)


def main():
  """
  CMD Line tool
  """

  # Handling arguments
  args            = get_args()
  host            = args.host[0]
  location        = args.location[0]
  test            = args.test[0]
  verbose         = args.verbose
  nagios_output   = args.nagios_output

  log_file = None
  if args.logfile:
    log_file = args.logfile[0]

  # Logging settings
  if verbose:
    log_level = logging.DEBUG
  else:
    log_level = logging.INFO

  if nagios_output:
    # Add custom level unknown
    logging.addLevelName(logging.DEBUG+1, 'UNKOWN')
    setattr(mylogger, 'unkown', debug_factory(mylogger, logging.DEBUG+1))

    # Change INFO LevelName to OK
    logging.addLevelName(logging.INFO, 'OK')

    # Setting output format for Nagios
    logging.basicConfig(filename=log_file,format='%(levelname)s - %(message)s',level=logging.INFO)
  else:
    logging.basicConfig(filename=log_file,format='%(asctime)s %(levelname)s %(message)s',level=log_level)

  if test == 'ap_end':
    check_autopilot_send_end(host, location)


if __name__ == "__main__":
  main()
