#!/usr/bin/env python
#-*- coding: utf8 -*-
"""A Bot to demonstrate the power of decorators
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from cmdbot_evented.core import Bot
from cmdbot_evented.decorators import direct, admin, no_verb, no_help
from cmdbot_evented.configs import ArgumentConfiguration


class ArgumentBot(Bot):
    config_class = ArgumentConfiguration

    @direct
    def do_direct(self, line):
        self.say('I only say that because you summon me')

    @admin
    def do_admin(self, line):
        self.say("I only say that because you're an admin")

    @admin
    @direct
    def do_direct_admin(self, line):
        self.say("I only say that because you summon me as an admin")

    @no_verb
    def nothing_special(self, line):
        self.say('I say nothing special, you did not include a known verb')

    @no_help
    def do_nohelp(self):
        "I will never display this"
        pass

if __name__ == '__main__':
    bot = ArgumentBot()
    bot.run()
