#!/usr/bin/python2
'''
Copyright (c) 2012, Andrew Klaus <andrewklaus@gmail.com>
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
import time
#import argparse
import shutil
import shlex
import sys
import logging
import subprocess
import mutagen              # ID3 Tags
import threading
import multiprocessing      # for cpu count


# Name : (executable_name , extension , pipe command (stdout)

decoders = {
            'flac' : ('flac','.flac','', \
                      '{exe} -c -d "{input_file}" {flags}'),
            }

# Name : (executable_name , extension , flags, stdin command. )

encoders = {
            'mp3' : ('lame','.mp3','-V 0', \
                     '{exe} - "{output_file}" {flags}'),

            'ogg' : ('oggenc','.ogg','-q 6', \
                     '{exe} - -o "{output_file}" {flags}'),            
            # NOT CURRENTLY IMPLEMENTED
            #'aac' : ('ffmpeg','.m4a','', \
            #         ''),   

            }

class Codec:
    def __init__(self,codec_type='decoder',name='flac'):

        self.__set_codec__(codec_type,name)
        self.__find_exe__()
        self.__check_executable__()
        self.__get_version__()

    def __set_codec__(self,codec_type,name):
        
        if codec_type == 'decoder' and name in decoders:
            self.name = decoders[name][0]
            self.ext = decoders[name][1]
            self.flags = decoders[name][2]
            self.command = decoders[name][3]
            
        elif codec_type == 'encoder' and name in encoders:
            self.name = encoders[name][0]
            self.ext = encoders[name][1]
            self.flags = encoders[name][2]
            self.command = encoders[name][3]

        else:
            raise NameError('InvalidCodec')

        self.codec_type = codec_type
        
    def __find_exe__(self):
        
        if os.path.isfile(self.name):
            pass    # full encoder path passed in
        else:
            self.path = self.__check_default_path__()
            logging.debug('Codec found at: ' + self.path)
                
        
        
    def __check_default_path__(self):
        """ Searches the default path for a specific named encoder """
    
        def_paths = os.path.defpath.split(':')
    
        # Check if encoder in default path exists
        for path in def_paths:
            current = os.path.join(path,self.name)
    
            if os.path.isfile(current):
                # Return first instance if encoder found
                return current
    
        # Encoder not found if reached here
        raise NameError('CodecNotFoundInDefaultPath')

    def __check_executable__(self):
        """ Checks if executable is executable """
        
        if os.access(self.path,os.X_OK) is False:
            raise NameError('CodecNotExecutable')   
    
    def __get_version__(self):
        """ Gets version information about the codec """
        
        # run command --version
        self.version = ''
    
class LosslessToLossyConverter:
    def __init__(self,source_dir,dest_dir,source_codec,dest_codec):
        
        # Remove trailing slashes
        self.source_dir = source_dir.rstrip('/')
        self.dest_dir = dest_dir.rstrip('/')
        
        self.num_threads = multiprocessing.cpu_count()
        
        self.Source_Codec = Codec('decoder',source_codec)
        self.Dest_Codec = Codec('encoder',dest_codec)
        
        self.to_convert = []    # Music to convert

        self.success = 0        # Successful conversions
        self.error_conv = []    # List of error conversions
        self.error_id3 = []     # List of error id3 tags

    def get_convert_list(self):
        """Populates list with files needing conversion."""
        
        logging.debug('Get convert list starting')
        try:
            for dirpath, dirnames, filenames in os.walk(self.source_dir):
                
                for filename in filenames:
                    
                    if os.path.splitext(filename)[1] in self.Source_Codec.ext \
                    and os.path.splitext(filename)[1] != '':
                        #logging.debug('filename extension: ' + os.path.splitext(filename)[1])
                        #logging.debug('comparing extension: ' + self.source_ext)
                        if self.does_lossy_file_exist(os.path.join(dirpath,filename)) == False:
                            logging.debug('***Adding to_convert: ' + os.path.join(dirpath,filename))
                            # Lossy song does not exist
                            self.to_convert.append(os.path.join(dirpath,filename))
                            
        except Exception, ex:
            logging.exception('Something happened in get_convert_list')
            raise SystemExit

    def translate_src_to_dest(self,lossless_file_path):
        """Provides translation between the source file and destination file"""
        
        # Remove "src_path" from path
        logging.debug('translate got: '+ lossless_file_path)
        dest = os.path.join(self.dest_dir, lossless_file_path[1+len(self.source_dir):])
        
        # Add extension
        dest = os.path.splitext(dest)[0] + self.Dest_Codec.ext
        logging.debug('translate changed dest to: '+ dest)
        
        return dest
    
    def does_lossy_file_exist(self, source_file_path):
        """ Checks if .lossless -> .lossy file already exists """
        #logging.debug('does_lossy_file_exist received: '+ source_file_path)
        dest = self.translate_src_to_dest(source_file_path)
        
        # Remove ext and add .mp3 extension
        dest = os.path.splitext(dest)[0] + self.Dest_Codec.ext
        
        #logging.debug('does_lossy_file_exist dest: '+ dest)
        return  os.path.exists(dest)

    def create_dest_folders(self):
        """ This creates an identical folder structure as the source directory
            It attempts to create a folder (even if it exists), but catches any 
            FolderAlreadyExists exceptions that may arise. 
        """
        logging.debug('Creating folder structure')
        for dirpath, dirnames, filenames  in os.walk(self.source_dir):
            try:
                os.makedirs(os.path.join(self.dest_dir,dirpath[1+len(self.source_dir):]))
            except:
                pass   

    def get_num_of_running_threads(self):
        """Returns number of non-main Python threads"""
        
        main_thread = threading.currentThread()
        
        count = 0
        
        # Count all threads except the main thread
        for t in threading.enumerate():
            if t is main_thread:
                continue
            count += 1
            
        return count

    def encode_and_tagging(self,lossless_file,lossy_file):
        logging.debug('Starting encode_and_tagging. Received: ' \
                      +' ' + lossless_file + ' ' + lossy_file)
        
        conv_result = self.convert_to_lossy(lossless_file,lossy_file)
    
        # Only ID3 tag if conversion successful
        if conv_result == 0:
            self.update_lossy_tags(lossless_file,lossy_file)

    def convert_to_lossy(self,lossless_file,lossy_file):

        try:
            lossy_file_tmp = lossy_file + '.tmp'
            
            source_cmd = self.Source_Codec.command.format( \
                            exe = self.Source_Codec.path, \
                            input_file = lossless_file, \
                            flags = self.Source_Codec.flags)
            
            logging.debug('source command: ' + source_cmd)
            
            dest_cmd = self.Dest_Codec.command.format(  \
                            exe= self.Dest_Codec.path,
                            output_file = lossy_file_tmp,
                            flags = self.Dest_Codec.flags)
            
            logging.debug('dest command: ' + dest_cmd)
                        

            src_args = shlex.split(source_cmd)
            dest_args = shlex.split(dest_cmd)

            p1 = subprocess.Popen(src_args,stdout=subprocess.PIPE)
            p2 = subprocess.Popen(dest_args, stdin=p1.stdout)

            output = p2.communicate()[0]
            
            logging.debug('Encode output: ' + str(output))
#            status = os.system(command)
#            if status == 2 :
#                print("\n\nCancelled by user")
#                raise SystemExit
#            elif status > 0:
#                raise NameError('FlacConversionFailed')
        
            # Move .tmp after conversion
            shutil.move(lossy_file_tmp, lossy_file)
        
        except Exception, ex:
            logging.exception('Could not encode')
            self.error_conv.append(lossless_file)
            
            return 1
        
        else:
            
            self.success += 1
            
            return 0
        
    def update_lossy_tags(self,lossless_file,lossy_file):
        """ Copies ID3 tags from lossless file to lossy file. """
        try:
            lossless_tags = mutagen.File(lossless_file, easy=True)
            lossy_tags = mutagen.File(lossy_file, easy=True)
        
            for k in lossless_tags:
                if k in ('album','artist','title','performer','tracknumber','date','genre',):
                    lossy_tags[k] = lossless_tags[k]
        
            lossy_tags.save()
        except:
            self.error_id3.append(lossy_file)    



    def print_results(self):
        """ Print a final summary of successful and/or failed conversions"""
        output = ''
    
        count_failed_conv = len(self.error_conv)
        count_failed_id3 = len(self.error_id3)
    

        if count_failed_conv > 0:
            output += '{} songs failed to convert\n'.format(count_failed_conv)
        else:
            output += 'No conversion errors\n'
    
        if count_failed_id3 > 0:
            output += '{} ID3 tags failed to write\n'.format(count_failed_id3)    
        else:
            output += 'No ID3 tag errors\n'
                
        if self.success > 0:
            output += '{} songs successfully converted'.format(self.success)
        else:
            output += 'No songs converted'
    
        print(output)

    def start(self):
        ''' Start the full conversion process '''
        logging.debug('Starting Conversion')
        # Build directory structure
        self.create_dest_folders()
        
        self.get_convert_list()
        
        logging.debug('Number of items in convert list: ' + str(len(self.to_convert))) 
                   
        # Start Threaded Converting
        while len(self.to_convert) > 0:
            
            # Get file from list and remove
            lossless_file = self.to_convert.pop()
            lossy_file = self.translate_src_to_dest(lossless_file)
            
            t = threading.Thread(target=self.encode_and_tagging, \
                                 args=(lossless_file,lossy_file))
        
            t.start()
         
            # Don't allow more than max_cpu threads to run 
            while self.get_num_of_running_threads() >= self.num_threads: 
                # Check every 3 seconds if more threads needed
                time.sleep(1)   
                
                
    
        # Wait for threads to complete
        main_thread = threading.current_thread()
        
        for t in threading.enumerate():
            if t is main_thread:
                continue
            t.join()


def main():
    logging.basicConfig(level=logging.DEBUG)

    source_dir = '/FLAC' 
    dest_dir = '/MP3'
    
    Converter = LosslessToLossyConverter(source_dir,dest_dir, \
                                         'flac','mp3')

    Converter.start()
    Converter.print_results()

    return(0)

if __name__ == "__main__": 
    sys.exit(main())
