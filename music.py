#!/usr/bin/env python
#A program for monitoring the Dwarf Fortress gamelog.txt and playing music/sound effects.
#By Thomas Liu

import re
import pygame
import os
import sys
import random
import win32file
import win32event
import win32con
import time

class player():
    def __init__(self, season="music/explore"):
        self.priority = 0
        self.season = season  #path to season folder music
        
    def analyze(self, line):
        musicBindings = self.parseMusicBindings("music.txt")# example format of dictionary: {r'Spring has arrived!|Spring has arrived on the calendar':(info.season,0)}
        for regex in musicBindings.keys():
            if re.search(regex,line):
                print("Match found: {0}".format(line))
                return musicBindings[regex]
        return None
        
    def queueMusic(self, name, priority):    #Determines whether to play music, or just play the sound effect, or just change the season 
        if priority == -1: #sound effect
            weather = pygame.mixer.Channel(0)
            rain = pygame.mixer.Sound(name)
            weather.play(rain,loops=-1,fade_ms=2000)
        elif priority == -2: #stop sound effects
            weather = pygame.mixer.Channel(0)
            weather.fadeout(2000)
        elif priority == 0: #assume season change
            self.season = name
            if self.priority <= 1: #if there's no important music playing
                self.playMusic(self.season)
                self.priority = 0
        elif priority == 1: #Menu music
            self.priority = priority
            self.playMusic(name, -1)
        elif priority >= self.priority: #Differing levels of priority of action music that overrides all other music
            self.priority = priority
            self.playMusic(name)
                
    def playMusic(self, fileOrFolder, loops=0):    #Plays actual music file, or randomly selects a music from the folder
        if re.search(r'.ogg|.mp3|.wav',fileOrFolder): #If it's a specific file
            try:
                pygame.mixer.music.load(fileOrFolder)  #then just load it
                pygame.mixer.music.play(loops)
                print('Playing {0}'.format(fileOrFolder))
            except pygame.error:
                self.playMusic(self.season)
        else:
            try:
                files = os.listdir(fileOrFolder)
                music = random.choice(files)
                pygame.mixer.music.load(fileOrFolder+'/'+music)
                pygame.mixer.music.play(loops)
                print('Playing {0}'.format(music))
            except OSError:
                self.playMusic(self.season)   #fall back to season music, which ideally does exist.
            
    def parseMusicBindings(self,path="music.cfg"):
        musicFile = open(path,'r')
        output = dict()
        for line in musicFile:
            lineSplit = line.split(';',2)
            regex = lineSplit[0]
            musicPath = lineSplit[1]
            priority = int(lineSplit[2])
            output[regex] = (musicPath, priority)
        return output #returns a dictionary with keys of type string and values of tuples of a string and an int
    
class gameLog():
    def __init__(self, path = "gamelog.txt"):
        self.size = os.path.getsize(path)
        self.path = path
        self.diff = 0
        
    def changed(self):
        change_handle = win32file.FindFirstChangeNotification (os.dirname(self.path), False, win32con.FILE_NOTIFY_CHANGE_SIZE)
        result = win32event.WaitForSingleObject (change_handle, 500)   #Returns an object after a file size change
        if result == win32con.WAIT_OBJECT_0:
            if os.path.getsize(self.path) > self.size:   #If it's the actual gamelog that changed
                self.diff = self.size - os.path.getsize(self.path)
                self.size = os.path.getsize(self.path)
                win32file.FindCloseChangeNotification (change_handle)
                return True
            else:
                win32file.FindNextChangeNotification (change_handle)   #I'm not actually sure if this code is doing what I'm trying to do
        
    def getLines(self):
        log = open(self.path,'r')
        log.seek(self.diff,2)   #Goes to the |self.diff|th byte before the end of the file
        lastLines = log.readlines()
        log.close()
        return(lastLines)
        
class loader():
    def __init__(self, path):
        self.path = path
    
    def loadSeason(self, player):
        try:
            f = open(self.path,'r')
        except IOError:
            self.saveSeason(player)
            f = open(self.path,'r')
        player.season = f.readline()
        print("Loaded " + player.season)
        f.close()
        
    def saveSeason(self, player):
        f = open(self.path,'w')
        f.write(player.season)
        print("Saved {0} to {1}.".format(player.season, self.path))
        f.close()
        
if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_endevent(1)
    pygame.display.set_mode((200,100))
    player = player()
    gameLog = gameLog("gamelog.txt")
    
    for parameter in ('-l', '--load'):
        if parameter in sys.argv:
            loader = loader(sys.argv[sys.argv.index(parameter) + 1])
            loader.loadSeason(player)
            break
    
    while True:
        try:
            if gameLog.changed():   #Will return true when a change is made to the gamelog
                # print(gameLog.getLines())
                for line in gameLog.getLines():
                    match = player.analyze(line)
                    if match:
                        player.queueMusic(match[0],match[1])
                if not pygame.mixer.music.get_busy():
                    player.playMusic(player.season)
            
        except KeyboardInterrupt:
            print("Quitting.")
            want = ""
            while want.lower() not in ('y','n'):
                want = raw_input("Do you want to save the season? (y/n): ")
                if want.lower() == 'y':
                    loader.saveSeason(player)
            break
        
