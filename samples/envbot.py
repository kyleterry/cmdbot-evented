#!/usr/bin/env python
#-*- coding: utf8 -*-
"""A dummy Bot only there to illustrate how to use an EnvironmentConfiguration
rather than the default IniFileConfiguration class.

If you want to run it::

    export CMDBOT_HOST=IRC_SERVER
    export CMDBOT_CHANNEL=IRC_CHANNEL
    export CMDBOT_NICK=IRC_NICKNAME
    python envbot.py
"""
import logging
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import time
import multiprocessing

from cmdbot_evented.core import Bot
from cmdbot_evented.decorators import direct, admin, regex
from cmdbot_evented.configs import EnvironmentConfiguration


class EnvBot(Bot):
    config_class = EnvironmentConfiguration

    def irc_reply_topic(self, line):
        print line.message
        print line.channel
        self.brain[line.channel] = {'topic': line.message}

    @direct
    @admin
    def do_hello(self, line):
        self.say("You're my master")

    @direct
    @admin
    def do_multiline(self, line):
        self.say("line 1\nline 2\r\nline 3")

    @direct
    @admin
    def do_long(self, line):
        self.say("This is a very long message! " * 100)

    @regex("^\.status (?P<resource>\w+)$")
    def test_regex(self, line, match):
        self.me("%s is fine" % match.group("resource"))

    @direct
    def do_sleep(self, line):
        self.say("%s: i'm going to sleep" % multiprocessing.current_process().pid)
        time.sleep(10)
        self.say("%s: i'm awake" % multiprocessing.current_process().pid)

    @direct
    def do_save(self, line):
        self.brain['message'] = line.message

    @direct
    def do_get(self, line):
        self.say("%s: %s" % (multiprocessing.current_process().pid, self.brain.get('message', "unknown")))
        self.say(self.brain.get(line.channel, "unknown"))


if __name__ == '__main__':
    bot = EnvBot()
    bot.run()
