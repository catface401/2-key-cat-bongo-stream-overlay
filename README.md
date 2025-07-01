this is unorganized im sorry :p
if you have any issues add me on discord username 'kmkt' so i can figure out where i messed up.

inside of the zip file there should be the pictures of the cat in each state, a python file that reads inputs for your two keys, an html document that you'll use as a source in obs, and a start_overlay.bat file that will start the overlay or something.

keep everything in the bongo-overlay folder or the world will fall apart. also you need python on your computer or the world will fall apart again. also also make sure you have the python dependencies: websockets, pynput, numpy, and sounddevice ("pip install websockets pynput numpy sounddevice") or the world will fall apart for a third time.
i didnt really package all of this together so you'll have to do all that shit to have things work. sorry. maybe at another point ill make it more accessible.

here's how things should be:

when you run start_overlay.bat, a web browser should open up containing the bongo cat. press 's' and 'd' a bunch and you'll see it pat its cute paws. it should also open its mouth when you talk.

additionally, the command prompt that opens with it should be blank at first but with each input show you its current state. this is for debugging, but if you find it annoying you can remove the print statement in listening.py, in which case the command prompt will just be blank forever. you'll make it sad.

to exit the program simply close the command prompt. it is basically the brains behind everything. the html page should be unresponsive after that no matter how many times you slam your keyboard or yell into your mic. feel free to close it.

if you wish to change the keys that make the cat pat, edit listening.py to use those keys (you'll see where i've put 's' and 'd', just replace those with whatever keys you want).

if the cat's mouth isn't opening, is stuck open, or somewhere in between (but not in a working way), it's probably due to your microphone volume. go to listening.py and change the "is_talking = volume > 2" value to something else. the higher it is, the louder things will need to be for the cat to open its mouth.
