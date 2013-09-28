# LMRchatterBox -- an LMR Shout Box posts retriever and TTS engine feeder

from __future__ import generators

import cookielib, urllib, urllib2
import os, re, subprocess, sys, time

from BeautifulSoup import BeautifulSoup


cookie_jar = cookielib.LWPCookieJar()
turl_opener = urllib2.build_opener( urllib2.HTTPCookieProcessor(cookie_jar) )
urllib2.install_opener(turl_opener)


class TinSBextractor(object):
    """Code refactored into Class based on TinHead's code
    at http://letsmakerobots.com/node/25942#comment-62543"""
    def __init__(self, user, passwd):
        super(TinSBextractor, self).__init__()
        self.user = user
        self.passwd = passwd

        self.url = "http://letsmakerobots.com/node?destination=frontpage%252Fpanel"            
        self.http_login()
        self.token = self.get_token()


    def http_login(self):
        params = {'openid_identifier':'','name': self.user, 'pass': self.passwd, 'os_cookie': True, 'op': 'Log In', 'form_id':'user_login_block'}
        response = urllib2.urlopen(self.url, urllib.urlencode(params))

    
    def get_token(self):
        token_url = "http://letsmakerobots.com/node"
        response = urllib2.urlopen(self.url)
        print 'doing request: ' + token_url
        for line in response:
            if "shoutbox-add-form-form-token" in line:
                token = line.split()[4].split("=")[1].strip("\"")
        return token
        

    def get_shouts(self):
        shout_url = "http://letsmakerobots.com/shoutbox/js/view"
        response = urllib2.urlopen(shout_url)
        out = response.read()

        # intervene at this point if you need/want a fancier (manual) parsing...
        # BeautifulSoup(out).findAll('span', { "class" : "shout" })

        shouts = ''.join(BeautifulSoup(out).findAll(text=True))
        return shouts




class TalkieTalker(object):
    """docstring for TalkieTalker -- or the 'actual vocal strings'
       of the LMRchatterBox"""
    def __init__(self, lang):
        super(TalkieTalker, self).__init__()
        self.language = lang
        self.devnull = open('/dev/null', 'w')


    def festival_read_phrase(self, phrase):

        p1 = subprocess.Popen(["echo", phrase], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["festival", "--tts"], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()  # Allows p1 to receive a SIGPIPE if p2 exits.
        output = p2.communicate()[0]


    def mplayer_read_phrase(self, phrase):

        retcode = subprocess.call(['mplayer', '-slave', '-really-quiet', phrase], stderr=self.devnull)


    def pico2wave_read_phrase(self, phrase):
    
        retcode = subprocess.call(['pico2wave', '-l='+self.language, '-w=/tmp/picospeech.wav', phrase])
        retcode = subprocess.call(['aplay', '/tmp/picospeech.wav'], stderr=self.devnull, stdout=self.devnull)
        retcode = subprocess.call(['rm', '/tmp/picospeech.wav'])




class TextStringer(object):
    """docstring for TextStringer: Class to preprocess 
       text before feeding into the different TTS engines
       and to control the sentence feed-rate"""
    def __init__(self, conn, lang, order, repl, method=None):
        super(TextStringer, self).__init__()
        
        self.X = conn
        self.language = lang
        self.tts_engine = method
        self.chatterbox = TalkieTalker(lang)

        self.compileorder = order
        self.replacements = repl
        


    def feed_list(self, shoutlist):
        slist = shoutlist
        for s in slist:
            
            print s # DEBUG

            #  add extra processing steps here
            # =================================== #
            s = self.sanitize_sentence(s)
            s = self.parse_some_crazy_out(s)

            #time.sleep(0.2)
            # =================================== #

            if self.tts_engine == 'gTTS':
               self.process_goggle_TTS_textfeed(s)
            elif self.tts_engine == 'festival':
               self.chatterbox.festival_read_phrase(s)
            elif self.tts_engine == 'pico2wave':
               self.chatterbox.pico2wave_read_phrase(s)    
            else:
               pass

    def post_streamer(self, newtext, lastPattern):

        posts = newtext
        lastDialog = lastPattern

        index = self.kmpFirstMatch(lastDialog, posts)

        # matched at the beginning -- means no new dialog lines
        if index == 0:
            print "No new dialog lines..."
            
            updatesList = posts.split('\n')
            lastDialog = updatesList[0]

            # time (in seconds) between each SB pooling
            time.sleep(30)							
            posts = self.X.get_shouts()
            self.post_streamer(posts, lastDialog)

        # uh look, a few more new sentences...   
        elif index > 0:
            print "Activity found..."
            updatesText = posts[:index]
            updatesList = updatesText.split('\n')
            
            lastDialog = updatesList[0]
            updatesList.reverse()

            updatesList = updatesList[1:]

            # Do what you will with the updateText...
            self.feed_list(updatesList)

            posts = self.X.get_shouts()
            self.post_streamer(posts, lastDialog)

        # no match means whole new conversation developed 
        # (some dialog lines might be missed)
        # (deleted posts may 'reset' the chatter)   
        else:
            print "Peeps being overly chatty..."
            updatesList = posts.split('\n')
            
            lastDialog = updatesList[0]
            updatesList.reverse()

            updatesList = updatesList[1:]

            # Do what you will with the updateText...
            self.feed_list(updatesList)

            posts = self.X.get_shouts()
            self.post_streamer(posts, lastDialog)                        


    def sanitize_sentence(self, sentence):

        base = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~ '
        sentence = filter(lambda x: x in base, sentence)
        return sentence


    def multiple_replace(self, dict, text): 

        """ Replace in 'text' all occurences of any key in the given
        dictionary by its corresponding value.  Returns the new tring.""" 

        text = str(text)
        # Create a regular expression  from the dictionary keys
        # 3rd option --- went with tuples -- only used to compile the regex -- in the right order
        regex = re.compile("(%s)" % "|".join( [re.escape(x) for x in self.compileorder] ) )

        # For each match, look-up corresponding value in dictionary
        return regex.sub(lambda mo: dict[mo.string[mo.start():mo.end()]], text)    


    def parse_some_crazy_out(self, sentence):

        """
        Parses and transforms stuff that either the TTS
        engines have difficulty in gobbling up or they
        garble up if they "eat it raw"
        """

        # gets the name of user currently "speaking"
        upat = re.compile(r'^\s?(\w+):\s{1}.*')
        m = upat.findall(sentence)
        if m > 0:
            user = (m[0], )


        # ================================================== #    
		# Insert processing for specific names at this point #
		# ================================================== #


        # substitute funky stuff like emoticons with spoken worded action
        # e.g. (user) does this.
        ERRATA = {}
        for k in self.replacements:
            for el in self.replacements[k]:
                try:
                    ERRATA[k] = str(self.replacements[k] % str(user[0]) )
                except:
                    pass    

        sentence = self.multiple_replace(ERRATA, sentence)


        # temporary cheat -- (very) dirty fix for the vanishing img tags
        cheat = re.compile('^\s?(\w+):(\s{1,2})$')
        m = cheat.findall(sentence)
        if len(m) > 0:
            sentence = m[0][0] + ' has posted an IMAGE!'

        # it's no fun at all listening to spelled urls, is it?        
        URL = re.compile(ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')

        purl = '. '+str(user[0])+' posted an URL.'        
        sentence = re.sub(URL, purl, sentence)
        
        # replaces ':'' with ' says:'
        sentence = re.sub(r'^\s?(\w+):(\s{1}.*)', r'\1 says:\2', sentence)

        # "sweeps away" leftover characters
        cheesy = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ@\'!?,.:- '
        sentence = filter(lambda x: x in cheesy, sentence)

        print sentence # DEBUG: prints processed sentence...
        return sentence




    # Knuth-Morris-Pratt string matching
    # David Eppstein, UC Irvine, 28 Feb 2002    

    # Find and return starting position of first match, or None if no match exists
    def kmpFirstMatch(self, pattern, text):
        shift = self.computeShifts(pattern)
        startPos = 0
        matchLen = 0
        for c in text:
            while matchLen >= 0 and pattern[matchLen] != c:
                startPos += shift[matchLen]
                matchLen -= shift[matchLen]
            matchLen += 1
            if matchLen == len(pattern):
                return startPos

    # Construct shift table used in KMP matching
    def computeShifts(self, pattern):
        shifts = [None] * (len(pattern) + 1)
        shift = 1
        for pos in range(len(pattern) + 1):
            while shift < pos and pattern[pos-1] != pattern[pos-shift-1]:
                shift += shifts[pos-shift-1]
            shifts[pos] = shift
        return shifts

    # further pre-processes sentences to accomodate 
    # for the google TTS engine 100 characters limit    
    # adapted from https://github.com/hungtruong/Google-Translate-TTS    
    def process_goggle_TTS_textfeed(self, text):
        #process text into chunks
        text = text.replace('\n','')
        text_list = re.split('(\,|\.)', text)
        combined_text = []
        for idx, val in enumerate(text_list):
            if idx % 2 == 0:
                combined_text.append(val)
            else:
                joined_text = ''.join((combined_text.pop(),val))
                if len(joined_text) < 100:
                    combined_text.append(joined_text)
                else:
                    subparts = re.split('( )', joined_text)
                    temp_string = ""
                    temp_array = []
                    for part in subparts:
                        temp_string = temp_string + part
                        if len(temp_string) > 80:
                            temp_array.append(temp_string)
                            temp_string = ""
                    #append final part
                    temp_array.append(temp_string)
                    combined_text.extend(temp_array)


        #download chunks and write them to the output file
        for idx, val in enumerate(combined_text):
            mp3url = "http://translate.google.com/translate_tts?tl=%s&q=%s&total=%s&idx=%s" % (self.language, urllib.quote(val), len(combined_text), idx)

            if len(val) > 0:
                try:
                    self.chatterbox.mplayer_read_phrase(mp3url)
                except:
                    pass