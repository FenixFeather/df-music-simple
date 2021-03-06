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

class Player():
    def __init__(self, season="music/explore"):
        self.priority = 0
        self.season = season  #path to season folder music
        
    def analyze(self, line):
        music_bindings = self.parse_music_bindings("music.cfg")# example format of dictionary: {r'Spring has arrived!|Spring has arrived on the calendar':(info.season,0)}
        for regex in music_bindings.keys():
            if re.search(regex,line):
                print("Match found: {0}".format(line))
                return music_bindings[regex]
        return None
        
    def queue_music(self, name, priority):
        """ Determine whether to play music, or just play the sound effect, or just change the season. """
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
                self.play_music(self.season)
                self.priority = 0
        elif priority == 1: #Menu music
            self.priority = priority
            self.play_music(name, -1)
        elif priority >= self.priority: #Differing levels of priority of action music that overrides all other music
            self.priority = priority
            self.play_music(name)
                
    def play_music(self, file_or_folder, loops=0):
        """Play actual music file, or randomly select a music from the folder."""
        if re.search(r'.ogg|.mp3|.wav',file_or_folder): #If it's a specific file
            try:
                pygame.mixer.music.load(file_or_folder)
                pygame.mixer.music.play(loops)
                print('Playing {0}'.format(file_or_folder))
            except pygame.error:
                self.play_music(self.season)
        else:
            try:
                files = os.listdir(file_or_folder)
                music = random.choice(files)
                pygame.mixer.music.load(file_or_folder+'/'+music)
                pygame.mixer.music.play(loops)
                print('Playing {0}'.format(music))
            except OSError:
                self.play_music(self.season)   #fall back to season music, which ideally does exist.
            
    def parse_music_bindings(self,path="music.cfg"):
        """Return a dictionary with keys of type string and values of tuples of a string and an int."""
        music_file = open(path,'r')
        output = dict()
        for line in music_file:
            line_split = line.split(';',2)
            regex = line_split[0]
            music_path = line_split[1]
            priority = int(line_split[2])
            output[regex] = (music_path, priority)
        return output 
    
class GameLog():
    def __init__(self, path = "gamelog.txt"):
        self.size = os.path.getsize(path)
        self.path = path
        self.diff = 0
        
    def changed(self):
        change_handle = win32file.FindFirstChangeNotification (os.path.dirname(self.path), False, win32con.FILE_NOTIFY_CHANGE_SIZE)
        result = win32event.WaitForSingleObject (change_handle, 500)   #Returns an object after a file size change
        if result == win32con.WAIT_OBJECT_0:
            if os.path.getsize(self.path) > self.size:   #If it's the actual gamelog that changed
                self.diff = self.size - os.path.getsize(self.path)
                self.size = os.path.getsize(self.path)
                win32file.FindCloseChangeNotification (change_handle)
                return True
        return False
            # else:
            #     win32file.FindNextChangeNotification (change_handle)   #I'm not actually sure if this code is doing what I'm trying to do
        
    def get_lines(self):
        log = open(self.path,'r')
        log.seek(self.diff,2)   #Goes to the |self.diff|th byte before the end of the file
        last_lines = log.readlines()
        log.close()
        return(last_lines)

    def get_size(self):
        return os.path.getsize(self.path)
        
class Loader():
    def __init__(self, path):
        self.path = path
    
    def load_season(self, player):
        try:
            f = open(self.path,'r')
        except IOError:
            self.save_season(player)
            f = open(self.path,'r')
        saved_string = f.readline()
        player.season = saved_string.split("|")[0]
        print("Loaded " + player.season)
        f.close()
        return int(saved_string.split("|")[1])
        
    def save_season(self, player, size=0):
        f = open(self.path,'w')
        f.write(player.season + "|" + str(size))
        print("Saved {0} to {1}.".format(player.season, self.path))
        f.close()
        
if __name__ == "__main__":
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_endevent(1)
    pygame.display.set_mode((200,100))
    player = Player()
    game_log = GameLog("../../../Dwarf Fortress 0.40.23/gamelog.txt")

    old_size = 0
    
    for parameter in ('-l', '--load'):
        if parameter in sys.argv:
            loader = Loader(sys.argv[sys.argv.index(parameter) + 1])
            old_size = loader.load_season(player)
            break
        else:
            print("No file specified for loading. Usage: music.py -l filetoload")
            exit()

    game_log.diff = old_size - game_log.get_size()

    last_lines = game_log.get_lines()
    if last_lines:
        match = player.analyze(last_lines[-1])
        if match:
            player.queue_music(match[0], match[1])
        
    while True:
        try:
            pygame.event.get()
            if game_log.changed():   
                # print(game_log.get_lines())
                for line in game_log.get_lines():
                    match = player.analyze(line)
                    if match:
                        player.queue_music(match[0],match[1])
                if not pygame.mixer.music.get_busy():
                    player.play_music(player.season)
            
        except KeyboardInterrupt:
            print("Quitting.")
            want = ""
            while want.lower() not in ('y','n'):
                want = raw_input("Do you want to save the season? (y/n): ")
                if want.lower() == 'y':
                    loader.save_season(player, game_log.get_size())
            break
        
