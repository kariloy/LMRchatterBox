### The LMR ChatterBox -- retrieves posts from the LMR
### community Shout Box and feeds them to TTS engines

% Requirements:

Python w/ BeautifulSoup module

% Depending on the TTS engines with want to use:

festival 

pico2wave + aplay

mplayer (for the google TTS engine)


% USAGE


	import LMRchatterBox as sb


	user = 'your LMR user'
	passwd = 'your password'


	lang = "en"                         # voice language: 			en-US, en-GB, etc...
	tts_engine = "gTTS"                 # text-to-speach engine: 	festival, gTTS, pico2wave



% tuple containing the order of patterns to compile, it is
% important that patterns are compiled in the right order
% Longer patterns must be compiled first -- see example

	patt_compile_order = ('\o/', '\\o', '\o', 'o//', 'o/', '>:-D', '>:-|', '>:-)', '>:-(', '>:-p',     (...)		':)', ';)', ':x', ';x', ':D', ';D', ';|', ':|', :o)


% dictionary containing patterns to be replaced

	replacements = {
	    '\o/': '. %s rejoices.',
	    '\\o': '. %s dances.',
	    '\o': '. %s waves.',
	    'o//': '. %s dances.',
	    'o/': '. %s waves.',

	    '>:-D': '. %s grins mischievously.', 
	    '>:-|': '. %s frowns annoyedly.',
	    '>:-)': '. %s smiles mischievously.',
	    '>:-(': '. %s is annoyedly sad.',
	    '>:-p': '. %s sticks out tongue.',

	    (...)

	    ':)': '. %s smiles.',
	    ';)': '. %s winks.',
	    ':x': '. %s suddenly stops talking.',
	    ';x': '. %s suddently stops talking.',
	    ':D': '. %s grins.',
	    ';D': '. %s grins.',
	    ';|': '. %s stares blankly.',
	    ':|': '. %s stares blankly.',
	    ':o': '. %s gasps.'

	}


% create an SB eXtractor object

	X = sb.TinSBextractor(user, passwd)

% create an Handler object for the extracted shouts 
% arguments: eXtracting object, (voice) language, pattern compilation order tuple, dictionary of replacements, TTS engine

	H = sb.TextStringer(X, lang, patt_compile_order, replacements, tts_engine)



% Initialize the script and do the first run

	print "Let's get this party started!"

	lastString = ""
	readList = []

% eXtract the first posts batch
	posts = X.get_shouts()

% 1st run
	updatesList = posts.split('\n')
	lastDialog = updatesList[0]
	updatesList.reverse()
	updatesList = updatesList[1:]

% feeds first posts batch to the TTS engine
	H.feed_list(updatesList)


% Keeps the script running recursively indefinetively
	H.post_streamer(posts, lastDialog)