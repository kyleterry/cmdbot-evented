#!/usr/bin/env python
#-*- coding: utf8 -*-
"""A dummy Bot only there to illustrate how to use an EnvironmentConfiguration
rather than the default IniFileConfiguration class.

If you want to run it::

    export CMDBOT_HOST=IRC_SERVER
    export CMDBOT_CHAN=IRC_CHANNEL
    export CMDBOT_NICK=IRC_NICKNAME
    python envbot.py
"""
import logging
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

from cmdbot.core import Bot
from cmdbot.decorators import direct, admin, no_verb, regex
from cmdbot.configs import EnvironmentConfiguration

import subprocess


class EnvBot(Bot):
    config_class = EnvironmentConfiguration

    @direct
    @admin
    def do_hello(self, line):
        self.say("You're my master")

    @direct
    def do_shell(self, line):
        logging.debug(line.message.split())
        cmd = subprocess.Popen(line.message.split()[1:], stdout=subprocess.PIPE)
        self.say(cmd.communicate()[0])

    @no_verb
    @regex("^\.status (?P<resource>\w+)$")
    def test_regex(self, line, match):
        self.me("%s is fine" % match.group("resource"))


if __name__ == '__main__':
    bot = EnvBot()
    bot.run()
