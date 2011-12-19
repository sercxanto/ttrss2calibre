#!/usr/bin/python
""" ttrss2calibre.py
   
    Generates a calibre news recipe of unread TTRSS feeds"""
#
#   Copyright (C) 2011 Georg Lutz <georg AT NOSPAM georglutz DOT de>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import logging
import optparse
import os
import sys
import urllib2



def readPass(filename):
    '''Reads and returns the password stored in filename.
    In case of any error None is returned'''

    try:
        f = open(filename, "r")
    except:
        return None
    
    return f.readline().rstrip("\n").rstrip("\r\n")


class Ttrss:
    def __init__(self, apiurl):
        self._apiurl = apiurl
        self._session_id = ""


    def doRequest(self, jsonData):
        '''Sends the jsonData to the server given in the constructor. jsonData is expected to be a python dict.
           Returns either None in case of any error or the decoded json answer (python dict).'''
        jdata = json.dumps(jsonData)
        response = []
        logging.info("Request: " + self._apiurl + " with data " + jdata)
        try:
            response = urllib2.urlopen(self._apiurl, jdata)
        except:
            return None

        textualResponse = ""
        for line in response.readlines():
            textualResponse += line

        logging.info("Response: " + textualResponse)
        decoded = []
        try:
            decoded = json.loads(textualResponse)
        except:
            return None
        return decoded

    def _hasValidContent(self, response):
        '''Checks if a response to a request has a valid content field'''
        if ( response is not None ) and \
             response.has_key("status") and ( response["status"] == 0 ) and \
             response.has_key("content"):
            return True
        else:
            return False

    def _hasValidContentKey(self, response, key):
        '''Checks if a response to a request has a valid content field and the given key inside'''
        if self._hasValidContent(response) and response["content"].has_key(key):
            return True
        else:
            return False

    def login(self, username, password):
        '''Tries to login with username, password. Returns True on success, otherwise False.'''

        response = self.doRequest({"op":"login", "user":username, "password":password})
        
        if self._hasValidContentKey(response, "session_id"):
            self._session_id = response["content"]["session_id"]
            return True
        else:
            return False

    def isLoggedIn(self):
        '''Checks if current session is logged in. False on any error.'''
        response = self.doRequest({"op":"isLoggedIn", "sid":self._session_id})

        if self._hasValidContentKey(response, "status"):
            return response["content"]["status"]
        else:
            return False


    def getFeeds(self):
        '''Returns a list of feeds or None on any error.'''
        response = self.doRequest({"op":"getFeeds", "sid":self._session_id})
        if self._hasValidContent(response):
            return response["content"]
        else:
            return None

    def getFeedAccessKey(self, feed_id):
        '''Returns a single access key for the given feed'''
        response = self.doRequest({"op":"getFeedAccessKey", "feed_id":feed_id, "sid":self._session_id})
        if self._hasValidContent(response):
            return response["content"]
        else:
            return None

    def getUnread(self):
        response = self.doRequest({"op":"getUnread", "sid":self._session_id})

        if self._hasValidContentKey(response, "unread"):
            return response["content"]["unread"]
        else:
            return None

    def logout(self):
        '''Logout from TTRS, True if sucessfully, otherwise False.'''
        response = self.doRequest({"op":"logout", "sid":self._session_id})

        if ( response is not None ) and response.has_key("status"):
            return response["status"] == "OK"
        else:
            return False


########### MAIN PROGRAM #############
def main():
    ''' main function, called when __main__'''


    parser = optparse.OptionParser(
            usage="%prog -a http://www.example.com/ttrss/api -u username -p ~/.ttrsspass",
        version="%prog " + os.linesep +
        "Copyright (C) 2011 Georg Lutz <georg AT NOSPAM georglutz DOT de")

    parser.add_option("-s", "--serverurl", dest="serverurl",
            type="string", action="store",
            help="URL pointing to the base/root of the TTRS installation.")

    parser.add_option("-u", "--username", dest="username",
            type="string", action="store",
            help="TTRSS username")
   
    parser.add_option("-p", "--passwordfile", dest="passwordfile",
            type="string", action="store",
            help="Path to the file where the password is stored for the given user is stored. The file must contain exactly one line with the password.")
 
    parser.add_option("-d", "--debuglevel", dest="debuglevel", type="int",
            help="Sets numerical debug level, see library logging module. Default is 30 (WARNING). Possible values are CRITICAL 50, ERROR 40, WARNING 30, INFO 20, DEBUG 10, NOTSET 0. All log messages with debuglevel or above are printed. So to disable all output set debuglevel e.g. to 100. If debuglevel is DEBUG or below temporary files will not be removed")

        
    (options, args) = parser.parse_args()

    if ( options.serverurl is None ) or not ( options.serverurl.startswith("http://") or options.serverurl.startswith("https://") ):
        print "Error: Please provide valid server url"
        sys.exit(2)

    if options.username is None:
        print "Error: Please provide username"
        sys.exit(2)

    if options.passwordfile is None:
        print "Error: Please provide password file"
        sys.exit(2)

    if not os.path.isfile(os.path.expanduser(options.passwordfile)):
        print "Error: Cannot open the password file \"" + options.passwordfile + "\"."
        sys.exit(2)

    logging.basicConfig(format="%(message)s", level=options.debuglevel)

    password = readPass(options.passwordfile)
    logging.info("Password is '" + password + "'")

    ttrss = Ttrss(options.serverurl + "/api/") # trailing "/" is important!

    if not ttrss.login(options.username, password):
        print "Login failed!"
        sys.exit()

    feeds = ttrss.getFeeds()

    i = 0
    while i < len(feeds):
        key = ttrss.getFeedAccessKey(feeds[i]["id"])
        if key is not None:
            feeds[i]["access_key"] = key
        i +=1
    ttrss.logout()


    print "Output, ready to be pasted to calibre user recipe (\"feed = ...\" part):"
    print "--------------------------------------------------"
    print ""
    
    calibreConfig = []
    for feed in feeds:
        title = feed["title"]
        url = options.serverurl + "/public.php?op=rss&view-mode=unread&limit=200" # set limit explicitely as default is only 30
        url += "&id=" + str(feed["id"]) + "&key=" + feed["access_key"]
        calibreConfig.append((title, url))

    print calibreConfig


if __name__ == "__main__":
    main()
