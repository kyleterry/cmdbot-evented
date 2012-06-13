#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Cmd Bot, a bot with a brainy cmd attitude.

This is the core bot module. It's already usable, even if you can't actually
use it for something interesting.

Every other bot you will want to build with this module can be class that
extends the Bot main class.
"""
import os
import sys
import socket
import logging
from ssl import wrap_socket, CERT_NONE
import time

if "CMDBOT_DEBUG" in os.environ:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

#i18n installation
import gettext
try:
    locale_path = os.path.join(os.path.dirname(os.path.abspath('.')), 'locale')
    t = gettext.translation('cmdbot', locale_path)
    t.install()
    _ = t.gettext
except:
    _ = gettext.gettext
    logging.info("Translation Not Found. Fallback to default")

from cmdbot.configs import IniFileConfiguration
from cmdbot.decorators import direct


class Line(object):
    "IRC line"
    def __init__(self, nick, message, direct=False):
        self.nick_from = nick
        self._raw_message = message
        self.message = message.lower()
        self.verb = ''
        if self.message:
            self.verb = self.message.split()[0]
        self.direct = direct

    def __repr__(self):
        return '<%s: %s>' % (self.nick_from, self.message)


class Bot(object):
    "Main bot class"

    class Brain(object):

        def knows(self, key, include_falses=False):
            """Return True if the brain.key value is known *and* not None.
            If the "with_none" option is set to True, event the 'false' values
            (None, '', (), [], etc.) values are counted.
            """
            return hasattr(self, key) and (getattr(self, key) or include_falses)

    welcome_message = _("Hi everyone.")
    exit_message = _("Bye, all")
    # One can override this
    config_class = IniFileConfiguration

    def __init__(self):
        self.config = self.config_class()
        # special case: admins
        self.admins = self.config.admins
        self.brain = self.Brain()  # this brain can contain *anything* you want.

        self.available_functions = []
        self.no_verb_functions = []
        self.no_help_functions = []
        for name in dir(self):
            func = getattr(self, name)
            if callable(func):
                if name.startswith('do_'):
                    self.available_functions.append(name.replace('do_', ''))
                if hasattr(func, 'no_verb'):
                    self.no_verb_functions.append(func)
                if hasattr(func, "no_help"):
                    self.no_help_functions.append(func)
                    # little trick. helps finding out if function is decorated
                    self.no_help_functions.append(name.replace('do_', ''))
        logging.debug(self.no_help_functions)

    def connect(self):
        "Connect to the server and join the chan"
        logging.info(_("Connection to host..."))

        if self.config.ssl:
            self.s = wrap_socket(socket.socket(), server_side=False, cert_reqs=CERT_NONE)
        else:
            self.s = socket.socket()

        while 1:
            try:
                self.s.connect((self.config.host, self.config.port))
                break
            except socket.error as e:
                logging.exception(e)
                logging.info("sleeping for 5 secs ...")
                time.sleep(5)

        if self.config.password:
            self.send("PASS %s\r\n" % self.config.password)
        self.send("NICK %s\r\n" % self.config.nick)
        self.send("USER %s %s bla :%s\r\n" % (
            self.config.ident, self.config.host, self.config.realname))
        channel = "%s %s" % (self.config.chan, self.config.chan_password)
        self.send("JOIN %s\r\n" % channel.strip())
        self.say(self.welcome_message)

    def close(self):
        """ closing connection """
        self.s.close()

    def send(self, msg):
        """ sending message to irc server """
        logging.debug("send: %s" % msg)
        self.s.send(msg)

    def say(self, message):
        "Say that `message` to the channel"
        msg = 'PRIVMSG %s :%s\r\n' % (self.config.chan, message)
        self.send(msg)

    def me(self, message):
        "/me message"
        self.say("\x01%s %s\x01" % ("ACTION", message))

    def nick(self, new_nick):
        """/nick new_nick
        """
        self.config.nick = new_nick
        self.send("NICK %s\r\n" % self.config.nick)

    def parse_line(self, line):
        "Analyse the line. Return a Line object"
        message = nick_from = ''
        direct = False
        meta, _, raw_message = line.partition(self.config.chan)
        # strip strings
        raw_message = raw_message.strip()
        # extract initial nick
        meta = meta.strip()
        nick_from = meta.partition('!')[0].replace(':', '')

        if raw_message.startswith(':%s' % self.config.nick):
            direct = True
            _, _, message = raw_message.partition(' ')
        else:
            message = raw_message.replace(':', '').strip()
        # actually return the Line object
        return Line(nick_from, message, direct)

    def process_noverb(self, line):
        """Process the no-verb lines
        (i.e. a line with a first verb unreferenced in the do_<verb> methods."""
        for func in self.no_verb_functions:
            func(line)

    def process_line(self, line):
        "Process the Line object"
        try:
            func = None
            try:
                func = getattr(self, 'do_%s' % line.verb)
            except UnicodeEncodeError:
                pass  # Do nothing, it won't work.
            except AttributeError:
                if line.direct:
                    # it's an instruction, we didn't get it.
                    self.say(_("%(nick)s: I have no clue...") % {'nick': line.nick_from})
                self.process_noverb(line)
            if func:
                return func(line)
        except:
            logging.exception('Bot Error')
            self.me("is going to die :( an exception occurs")

    def _raw_ping(self, line):
        "Raw PING/PONG game. Prevent your bot from being disconnected by server"
        self.send(line.replace('PING', 'PONG'))

    @direct
    def do_ping(self, line):
        "(direct) Reply 'pong'"
        self.say(_("%(nick)s: pong") % {'nick': line.nick_from})

    @direct
    def do_help(self, line):
        "(direct) Gives some help"
        splitted = line.message.split()
        if len(splitted) == 1:
            self.say(_('Available commands: %(commands)s')
                % {'commands': ', '.join(func for func in self.available_functions if func not in self.no_help_functions)})
        else:
            command_name = splitted[1]
            try:
                func = getattr(self, 'do_%s' % command_name)
                if func in self.no_help_functions:
                    raise AttributeError
                self.say('%s: %s' % (command_name, func.__doc__))
            except AttributeError:
                self.say(_('Sorry, command "%(command)s" unknown')
                    % {'command': command_name})

    def run(self):
        "Main programme. Connect to server and start listening"
        self.connect()
        readbuffer = ''
        try:
            while 1:
                readbuffer = readbuffer + self.s.recv(1024).decode('utf')
                if not readbuffer:
                    # connection lost, reconnect
                    self.close()
                    self.connect()
                    continue
                temp = readbuffer.split("\n")  # string.split
                readbuffer = temp.pop()
                for raw_line in temp:
                    logging.debug("recv: %s" % raw_line.rstrip())
                    if raw_line.startswith('PING'):
                        self._raw_ping(raw_line)
                    elif self.config.chan in raw_line and 'PRIVMSG' in raw_line:
                        line = self.parse_line(raw_line.rstrip())
                        self.process_line(line)
        except KeyboardInterrupt:
            self.send('QUIT :%s\r\n' % self.exit_message)
            self.close()
            sys.exit(_("Bot has been shut down. See you."))


if __name__ == '__main__':
    bot = Bot()
    bot.run()
