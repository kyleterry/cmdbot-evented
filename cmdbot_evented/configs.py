"""
Config file modules. Here you can pick your favorite configuration tool to
handle bot parameters.

"""
import os
import argparse
from ConfigParser import SafeConfigParser

# these arguments have a default value.
DEFAULT_VARS = {
    'port': '6667',
    'nick': 'cmdbot',
    'password': '',
    'ident': 'cmdbot',
    'realname': 'Cmd Bot',
    'admins': '',
    'ssl': False
}


class GenericConfiguration(object):
    def _normalize_channels(self, chan_list):
        channels = []
        for chan in chan_list:
            if not chan.startswith("#"):
                chan = '#' + chan
            channels.append(chan)
        return channels

    def __repr__(self):
        result = []
        keys = ('host', 'channels', 'port', 'nick')
        for key in keys:
            result.append('* %s' % getattr(self, key))
        result.append('* %s' % ', '.join(self.admins))
        return '\n'.join(result)


class IniFileConfiguration(GenericConfiguration):
    "Basic Configuration class. Loads a .ini file "
    def __init__(self):
        self.as_dict = {}
        parser = argparse.ArgumentParser("CmdBot")
        parser.add_argument('ini_file',
            help='path to the ini file to extract configuration from')
        args = parser.parse_args()

        config = SafeConfigParser()
        config.read(args.ini_file)

        # Host and chan are the only arguments that *need* a user-defined value
        self.host = config.get('general', 'host')
        self.channels = self._normalize_channels(str(config.get('general', 'channels')).split())

        self.port = int(config.get('general', 'port'))
        self.ssl = True if config.has_option('general', 'ssl') else DEFAULT_VARS['ssl']
        self.nick = config.get('general', 'nick')
        self.password = config.get('general', 'password', vars=DEFAULT_VARS)
        self.ident = config.get('general', 'ident', vars=DEFAULT_VARS)
        self.realname = config.get('general', 'realname')

        # special case: admins
        if config.has_option("general", "admins"):
            admins = config.get('general', 'admins')
            if ',' in admins:
                admins = admins.split()
            else:
                admins = [admins]
        else:
            admins = []
        self.admins = admins

        for section in config.sections():
            self.as_dict[section] = {}
            for key, value in config.items(section):
                self.as_dict[section][key] = value


class DictConfiguration(GenericConfiguration):

    def __init__(self):
        pass

class ArgumentConfiguration(GenericConfiguration):
    "Argument-based configuration."
    def __init__(self):
        parser = argparse.ArgumentParser("CmdBot")
        # mandatory arguments
        parser.add_argument('host', help="IRC server name")
        parser.add_argument('channel', nargs='+',
            help='Channel with/without password. ex: "channel1,password" (Mind not to add the "#" as a first character)')
        # optional arguments
        parser.add_argument('--port', default=DEFAULT_VARS['port'], type=int,
            help='The port number.')
        parser.add_argument('--ssl', default=DEFAULT_VARS['ssl'], action="store_true",
            help='Use SSL connection.')
        parser.add_argument('--ident', default=DEFAULT_VARS['ident'],
            help='The string to use to authenticate with the servers')
        parser.add_argument('--nick', default=DEFAULT_VARS['nick'],
            help="Your bot's nickname")
        parser.add_argument('--password', default=DEFAULT_VARS['password'],
            help="IRC server password")
        parser.add_argument('--realname', default=DEFAULT_VARS['realname'],
            help="What will be used as a 'real name' by your bot")
        parser.add_argument('--admins', default='',
            help="A list of comma-separated nicks that will be your bot's admins")

        args = parser.parse_args()

        self.host = args.host
        self.channels = self._normalize_channels(args.channel)
        self.port = int(args.port)
        self.ssl = args.ssl
        self.nick = args.nick
        self.password = args.password
        self.ident = args.ident
        self.realname = args.realname
        # special case
        self.admins = args.admins.split(',')


class EnvironmentConfiguration(GenericConfiguration):
    "Get configuration via user environment."
    def __init__(self):
        self.host = os.environ.get("CMDBOT_HOST", False)
        if not self.host:
            raise Exception("CMDBOT_HOST is not set")

        # split chan env var into channels with/without password
        # ex. CMDBOT_CHANNEL="channel1,password channel2 channel3,password3"
        self.channels = self._normalize_channels(os.environ.get("CMDBOT_CHANNEL", []).split())
        if not self.channels:
            raise Exception("CMDBOT_CHANNEL is not set")

        self.port = int(os.environ.get("CMDBOT_PORT", DEFAULT_VARS['port']))
        self.ssl = True if "CMDBOT_SSL" in os.environ else DEFAULT_VARS['ssl']
        self.nick = os.environ.get("CMDBOT_NICK", DEFAULT_VARS['nick'])
        self.password = os.environ.get("CMDBOT_PASSWORD", DEFAULT_VARS['password'])
        self.ident = os.environ.get("CMDBOT_IDENT", DEFAULT_VARS['ident'])
        self.realname = os.environ.get("CMDBOT_REALNAME", DEFAULT_VARS['realname'])
        admins = os.environ.get("CMDBOT_ADMINS", DEFAULT_VARS['admins'])
        if "," in admins:
            self.admins = admins.split(",")
        else:
            self.admins = [admins]
