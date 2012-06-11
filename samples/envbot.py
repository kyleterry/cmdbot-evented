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
from cmdbot.core import Bot
from cmdbot.decorators import direct, admin, no_verb, regex
from cmdbot.configs import EnvironmentConfiguration


class EnvBot(Bot):
    config_class = EnvironmentConfiguration

    @direct
    @admin
    def do_hello(self, line):
        self.say("You're my master")

    @no_verb
    @regex("^\.status (?P<resource>\w+)$")
    def test_regex(self, line, match):
        self.me("%s is fine" % match.group("resource"))


if __name__ == '__main__':
    bot = EnvBot()
    bot.run()
