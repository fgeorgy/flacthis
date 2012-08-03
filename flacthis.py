#!/usr/bin/python2
'''
Copyright (c) 2012, Andrew Klaus
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''
import os
import argparse
import shutil
import sys
import subprocess
import mutagen

lossless_formats = ('flac',)	# For future use.



def main():
	source 	= '' 	# MUST BE SET (No trailing slash)
	dest 	= ''	# MUST BE SET (No trailing slash)
	
	flac_exec = '/usr/bin/flac' # Ensure valid paths
	lame_exec = '/usr/bin/lame'
	lame_flags = '-V 0'


	CheckEncoders(flac_exec,lame_exec)

	CreateDestFolderStructure(dest, source)

	all_music_files = []	# All lossless music files
	create_music_files = []	# For files needing conversion


	GetLosslessMusicList(source,all_music_files)

	GetLossyMusicToConvert(dest,source,all_music_files,create_music_files)

	# Need for inside loop
	count = 0 	
	failed = 0	
	failed_tag = 0

	for file in create_music_files:
		lossless_file = file
		lossy_file = TranslateSourceToDestFileName(dest,source,file)
		lossy_file_tmp = lossy_file + '.tmp'

		command = '{0} -c -d "{1}" | {2} - "{3}" {4}'.format(flac_exec,lossless_file,lame_exec,lossy_file_tmp,lame_flags)


		print 'Starting file {0} of {1}'.format(count+1,len(create_music_files))

		try:

			status = os.system(command)

			if status == 2 :
				print "\n\nCancelled by user"
				raise SystemExit
			elif status > 0:
				raise NameError('FlacConversionFailed')

			# Move .tmp after conversion
			shutil.move(lossy_file_tmp, lossy_file)

		except:
			failed += 1
		else:
			count += 1
			try:
				UpdateLossyTags(lossy_file,lossless_file)
			except: 
				failed_tag += 1

	PrintComplete(count,failed,failed_tag)

def CheckEncoders(flac_exec,lame_exec):

	if os.path.isfile(flac_exec) is False:
		print "FLAC executable does not exist"
		raise SystemExit
	elif os.path.isfile(lame_exec) is False:
		print "Lame executable does not exist"
		raise SystemExit


def GetLosslessMusicList(source,dest_list):
	for dirpath, dirnames, filenames in os.walk(source):
		for filename in filenames:
			if os.path.splitext(filename)[1][1:] in lossless_formats:
				dest_list.append(os.path.join(dirpath,filename))

def GetLossyMusicToConvert(dest,source,src_list,dest_list):
	for file in src_list:
		if DoesLossyFileExist(dest, source, file) == False:
			# Lossy song does not exist
			dest_list.append(file)


def UpdateLossyTags(lossy_file,lossless_file):

	lossless_tags = mutagen.File(lossless_file, easy=True)
	lossy_tags = mutagen.File(lossy_file, easy=True)

	for k in lossless_tags:
		if k in ('album','artist','title','performer','tracknumber','date','genre',):
			lossy_tags[k] = lossless_tags[k]

	lossy_tags.save()


def CreateDestFolderStructure(dest_dir, source_dir):
	# Try to create every folder needed and catch any exceptions (directory already created)
	# This avoids any directory creation race conditions

	for dirpath, dirnames, filenames  in os.walk(source_dir):
		try:
			os.makedirs(os.path.join(dest_dir,dirpath[1+len(source_dir):]))
		except:
			pass	



def DoesLossyFileExist(dest_dir, source_dir, source_file_path):
	# Dest with .lossless extension
	#dest = os.path.join(dest_dir, source_file_path[1+len(source):])
	dest = TranslateSourceToDestFileName(dest_dir, source_dir, source_file_path)
	# Remove ext and add .mp3 extension
	dest = os.path.splitext(dest)[0] + '.mp3'

	return  os.path.exists(dest)

def TranslateSourceToDestFileName(dest_dir, source_dir, source_file_path):
	# Remove "src_path" from path
	dest = os.path.join(dest_dir, source_file_path[1+len(source_dir):])

	# Add mp3 extension
	dest = os.path.splitext(dest)[0] + '.mp3'

	return dest

def PrintComplete(count,failed,failed_id3):
	output = ''

	if failed > 0:
		output += '{} songs failed to convert\n'.format(failed)

	if failed_id3 > 0:
		output += '{} id3 tags failed to write\n'.format(failed_id3)	

	if count > 0:
		output += '{} songs successfully converted'.format(count)
	else:
		output += 'No songs converted'

	print output

if __name__ == "__main__": 
	sys.exit(main())

