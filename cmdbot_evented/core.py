#!/usr/bin/env python
#-*- coding: utf-8 -*-
"""Cmd Bot, a bot with a brainy cmd attitude.

This is the core bot module. It's already usable, even if you can't actually
use it for something interesting.

Every other bot you will want to build with this module can be class that
extends the Bot main class.

Some IRC Line parsing code is bought from the cloudbot guys (https://github.com/ClouDev/CloudBot). Thanks a lot :)
"""

import os
import sys
import logging
import gevent
from gevent import monkey
from gevent import socket, queue
from gevent.ssl import wrap_socket
from ssl import CERT_NONE
import time
from threading import Thread, Lock


monkey.patch_all()


#if "CMDBOT_DEBUG" in os.environ:
#    logging.basicConfig(level=logging.DEBUG)
#else:
#    logging.basicConfig(level=logging.INFO)
logging.basicConfig(level=logging.DEBUG)

#i18n installation
import gettext
try:
    locale_path = os.path.join(os.path.dirname(os.path.abspath('.')), 'locale')
    t = gettext.translation('cmdbot_evented', locale_path)
    t.install()
    _ = t.gettext
except:
    _ = gettext.gettext
    logging.info("Translation Not Found. Fallback to default")

from cmdbot_evented.configs import IniFileConfiguration
from cmdbot_evented.decorators import direct, no_help

import re
irc_prefix_rem = re.compile(r'(.*?) (.*?) (.*)').match
irc_noprefix_rem = re.compile(r'()(.*?) (.*)').match
irc_netmask_rem = re.compile(r':?([^!@]*)!?([^@]*)@?(.*)').match
irc_param_ref = re.compile(r'(?:^|(?<= ))(:.*|[^ ]+)').findall


class Line(object):
    """ IRC line

    Code bought from cloudbot guys (https://github.com/ClouDev/CloudBot)
    """
    def __init__(self, config, line):
        # parse the message
        self._raw_message = line

        if line.startswith(":"):  # has a prefix
            prefix, self.command, params = irc_prefix_rem(line).groups()
        else:
            prefix, self.command, params = irc_noprefix_rem(line).groups()

        self.nick_from, self.user, self.host = irc_netmask_rem(prefix).groups()
        self.mask = self.user + "@" + self.host
        self.paramlist = irc_param_ref(params)
        lastparam = ""
        if self.paramlist:
            if self.paramlist[-1].startswith(':'):
                self.paramlist[-1] = self.paramlist[-1][1:]
            lastparam = self.paramlist[-1]

        self.channel = self.paramlist[0]
        self.message = lastparam.lower()
        self.direct = self.message.startswith(config.nick)
        self.verb = ''
        if self.message:
            try:
                if self.direct:
                    self.verb = self.message.split()[1]
                else:
                    self.verb = self.message.split()[0]
            except IndexError:
                self.verb = 'confused'

        if self.direct:
            # remove 'BOTNICK: ' from message
            self.message = " ".join(self.message.split()[1:])

    def __repr__(self):
        return '<%s: %s>' % (self.nick_from, self.message)


def chunks(s, n):
    """  split string 's' into chunks of length 'n'
    """
    for start in xrange(0, len(s), n):
        yield s[start:start + n]


class BotBrain(object):
    def __init__(self):
        super(BotBrain, self).__setattr__("lock", Lock())

    def __setattr__(self, key, value):
        logging.debug('Waiting for lock')
        with self.lock:
            super(BotBrain, self).__setattr__(key, value)


class Connection(object):

    def __init__(self, config):
        self.config = config
        self._ibuffer = ''
        self._obuffer = ''
        self.iqueue = queue.Queue()
        self.oqueue = queue.Queue()
        self._socket = self._create_socket()

    def _create_socket(self):
        if self.config.ssl:
            logging.debug("creating ssl socket")
            return wrap_socket(socket.socket(), server_side=False, cert_reqs=CERT_NONE)
        else:
            logging.debug("creating non-ssl socket")
            return socket.socket()

    def connect(self):
        """ Connect to the server
        """
        logging.info(_("Connection to host..."))
        while True:
            try:
                logging.info(_('Creating socket...'))
                self._socket.connect((self.config.host, self.config.port))
                break
            except socket.error as e:
                logging.exception(e)
                logging.info("sleeping for 5 secs ...")
                time.sleep(5)
        gevent.spawn(self._spawn_send_and_recv_loops)

    def _spawn_send_and_recv_loops(self):
        try:
            jobs = [gevent.spawn(self._recv_loop), gevent.spawn(self._send_loop)]
            gevent.joinall(jobs)
        finally:
            gevent.killall(jobs)


    def _close(self):
        """ closing irc connection
        """
        self._socket.close()

    def _recv_loop(self):
        while True:
            data = self._socket.recv(1024).decode('utf')
            self._ibuffer += data
            while '\r\n' in self._ibuffer:
                line, self._ibuffer = self._ibuffer.split('\r\n', 1)
                self.iqueue.put(line)

    def _send_loop(self):
        while True:
            #line = self.oqueue.get().splitlines()[0]
            line = self.oqueue.get()
            self._obuffer += line.encode('utf-8', 'replace') + '\r\n'
            while self._obuffer:
                sent = self._socket.send(self._obuffer)
                self._obuffer = self._obuffer[sent:]
                time.sleep(.5)


class Bot(object):
    """ Main bot class
    """
    welcome_message = _("Hi everyone.")
    exit_message = _("Bye, all")
    # One can override this
    config_class = IniFileConfiguration

    def __init__(self, config_module=None):
        self.config = self.config_class()
        # special case: admins
        self.admins = self.config.admins

        # bot brain
        self.brain = BotBrain()

        self.available_functions = []
        self.no_verb_functions = []
        self.no_help_functions = []

        self._create_commands()
        self._bootstrap_connect()

    def _create_commands(self):
        for name in dir(self):
            func = getattr(self, name)
            if callable(func):
                if name.startswith('do_'):
                    self.available_functions.append(name.replace('do_', ''))
                if hasattr(func, 'no_verb'):
                    self.no_verb_functions.append(name)
                if hasattr(func, "no_help"):
                    self.no_help_functions.append(name.replace('do_', ''))
        logging.debug(self.no_help_functions)

    def _set_nick_and_join(self):
        if self.config.password:
            self.send("PASS %s" % self.config.password)
        self.send("NICK %s" % self.config.nick)
        self.send("USER %s %s bla :%s" % (
            self.config.ident, self.config.host, self.config.realname))

        # join channels
        for channel in self.config.channels:
            self.join(channel, self.welcome_message)

    def _bootstrap_connect(self):
        self.conn = Connection(self.config)
        self.conn.connect()
        self._set_nick_and_join()

    def _parse_line(self, line):
        """ Analyse the line. Return a Line object
        """
        # actually return the Line object
        return Line(self.config, line)

    def _process_noverb(self, line):
        """ Process the no-verb lines
        (i.e. a line with a first verb unreferenced in the do_<verb> methods.
        """
        for func in self.no_verb_functions:
            f = getattr(self, func)
            f(line)

    def _process_line(self, line):
        """ Process the Line object
        """
        try:
            try:
                func = getattr(self, 'do_%s' % line.verb)
                return func(line)
            except UnicodeEncodeError:
                pass  # Do nothing, it won't work.
            except AttributeError:
                if line.direct:
                    # it's an instruction, we didn't get it.
                    self.say(_("%(nick)s: I have no clue...") % {'nick': line.nick_from})
                self._process_noverb(line)
        except:
            logging.exception('Bot Error')
            self.me("might die :(")

    def _raw_ping(self, line):
        """ Raw PING/PONG game. Prevent your bot from being disconnected by server
        """
        msg = line.replace('PING', 'PONG')
        self.send(msg)

    def _fork(self, line):
        """ fork and exec callback
        """
        try:
            # call callback for current irc command
            func = getattr(self, "irc_reply_%s" % self.line.command.lower())
            Thread(target=func, args=(line,)).start()
        except AttributeError:
            pass

    def run_call(self):
        pass

    # public methods
    def run(self):
        "Main programme. Connect to server and start listening"
        try:
            while True:
                raw_line = self.conn.iqueue.get()
                logging.info("recv: %s" % raw_line.rstrip())
                if raw_line.startswith('PING'):
                    self._raw_ping(raw_line)
                else:
                    #:TODO: self.line is probably going to be problematic
                    self.line = self._parse_line(raw_line.rstrip())
                    self.run_call(self.line)
                    # exec callback as seperated process
                    self._fork(self.line)
        except KeyboardInterrupt:
            self.send('QUIT :%s' % self.exit_message)
            self.conn._close()
            sys.exit(_("Bot has been shut down."))

    def send(self, msg):
        """ sending irc message to irc server
        """
        msg = msg.strip()
        logging.info("sent: %s" % msg)
        self.conn.oqueue.put(msg)

    def join(self, channel, message=None):
        """ join a irc channel
        """
        password = ""
        if "," in channel:
            channel, password = channel.split(",")
        chan = "%s %s" % (channel, password)
        logging.debug('join: %s' % chan)
        self.send("JOIN %s" % chan.strip())
        if message:
            self.say(message, channels=channel)

    def say(self, message, channels=None):
        """ Say that `message` into given or current channel
        """
        if not channels:
            channels = self.line.channel
        if type(channels) not in (list, tuple):
            channels = (channels,)
        for line in str(message).splitlines():
            for chunk in chunks(line, 800):
                for channel in channels:
                    msg = 'PRIVMSG %s :%s' % (channel.strip(), chunk.strip())
                    self.send(msg)

    def me(self, message):
        """ /me 'message'
        """
        for line in message.splitlines():
            self.say("\x01%s %s\x01" % ("ACTION", line.strip()))

    def nick(self, new_nick):
        """ /nick new_nick
        """
        self.config.nick = new_nick
        self.send("NICK %s" % self.config.nick)

    # standard irc_reply callbacks
    def irc_reply_privmsg(self, line):
        """ default handler for PRIVMSG
        """
        self._process_line(self.line)

    # standard actions
    @direct
    def do_ping(self, line):
        """ Reply 'pong'
        """
        self.say(_("%(nick)s: pong") % {'nick': line.nick_from})

    @direct
    def do_help(self, line):
        """ Gives some help
        """
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

    @direct
    def do_info(self, line):
        if self.config.as_dict['general']['enable_info']:
            self.say('I am an evented IRC bot written in Python and gevent.')
            self.say('I was made evented by http://github.com/kyleterry')

    @direct
    @no_help
    def do_confused(self, line):
        self.say('%(nick)s: I am totally confused. You have nothing to say?' % {'nick': line.nick_from})


if __name__ == '__main__':
    bot = Bot()
    bot.run()
