# -*- coding: utf-8 -*-
"""
@author: GitHub@Oscarshu0719
"""

from math import floor
from pymongo import MongoClient
import re

class Model(object):
    """ Class:
    The operations about MongoDB.
    """
    IMPORT_ERROR_LOG_PATH = r".\import_error.log"
    
    def __init__(self, parent=None):
        self.DB_NAME = "data"
        self.client = MongoClient("mongodb://localhost:27017/")
        self.database = self.client[self.DB_NAME]
        
    def query(self, input_text, quality_is_ckecked):
        """ Function:
        Query the input text in the database, and the text is *insensitive*.
        """
        
        regex = ['No', 'Video name', 'Actress name', 'Type', 'Quality']
        search_results = list()
        
        regex_text = "{"
        # Check if the key is firstly countered in the input sequence.
        check_first = 1
        for i in range(4 + int(quality_is_ckecked)):
            if input_text[i].strip() != '':
                regex_text += "'" + regex[i] + "': {'$regex': '.*" 
                regex_text += input_text[i] + ".*', '$options': 'i'}"
                
                if check_first:
                    regex_text += ', '
                    check_first = 0
        regex_text += "}"
    
        for collection in self.database.list_collection_names():
            doc_list = self.database[collection].find(eval(regex_text))
            
            for doc in doc_list:
                search_results.append(doc)
                
        return search_results
    
    def specific_query(self, selected_item):
        """ Function:
        Specific query for the videos' names started with '.' or None.
        """
        
        for collection in self.database.list_collection_names():
            for col in self.database[collection].find():
                dot_index = col["_id"].rfind(".")
                if col["_id"][:dot_index] == selected_item:
                    return collection
     
    def add_to_remove_from_favorite(self, selected_item, option, flag):
        """ Function:
        Available text of item: Video number, Actress name, and Full name.
        Notice that if the user add or remove an Actress from favorite, *all* 
        videos that the actress acts will be added or removed.
        After the operation is finished, the full name will not change, but 
        only change the 'Favorite' attribute of the video in the database.
        """
        
        new_query = [{"$set": {"Favorite": True}}, 
                     {"$set": {"Favorite": False}}]
        print(option)
        
        if option == 1:
            """
            No.
            """
            
            self.database[selected_item].update_one({}, new_query[flag])
        elif option == 2:
            """
            Actress name.
            """
            
            for col_name in self.database.list_collection_names():
                for col in self.database[col_name].find():
                    if selected_item in col['Actress name']:
                        self.database[col_name].update_one({}, new_query[flag])
        elif option == 3:
            """
            Full name with common No..
            """
            
            self.database[selected_item].update_one({}, new_query[flag])
        elif option == 4:
            """
            Full name with specific No., like '' and '.CD1'.
            """
            
            result = self.specific_query(selected_item)
            self.database[result].update_one({}, new_query[flag])
    
    def import_manual(self, input_data):
        """ Function:
        Manually Import.
        """
        
        doc = ClassifyData.init_data_manual(input_data[6])
        
        if doc == False:
            return False
        
        regex = ['No', 'Video name', 'Actress name', 'Favorite', 'Type', 
                 'Quality']
        regex_find = {"_id": doc['_id']}
        for collection in self.database.list_collection_names():
            if self.database[collection].find_one(regex_find) != None:
                for i in range(6):
                    if input_data[i] != '':
                        regex_update = {"$set": {regex[i]: input_data[i]}}
                        self.database[collection].update_one({}, regex_update)
                if input_data[6] != '':
                    regex_update = {"$set": 
                        {'Location': input_data[6][:input_data[6].rfind('/')]}}
                    self.database[collection].update_one({}, regex_update)
                    
                return True

        collection = self.database[doc['No']]
        collection.insert_one(doc)
        
        return True
            
    def import_batch(self, folder):
        """ Function:
        Batch import.
        """
        
        doc_list, succeeded, failed = ClassifyData.init_data_folder(folder)
        
        # The index of videos which have no 'No'.
        no_number_video_index = 1
        # Use to keep the index when one video has no 'No' but has several 'CD'.
        # e.g. .CD1, .CD2
        check_cd_number = 0
        
        error_log = ''
        
        total_progress = len(doc_list)
        progress = 0
        print_label = 0
        # Store the prepared data.
        for doc in doc_list:
            if doc['No'] == '':
                if check_cd_number == 1:
                    no_number_video_index += 1
                    check_cd_number = 0
                collection_name = 'None_' + str(no_number_video_index)
                no_number_video_index += 1
            elif doc['No'][:3] == '.CD':
                collection_name = 'None_' + str(no_number_video_index) + doc['No']
                check_cd_number = 1
            else:
                collection_name = doc['No']
            regex_find = {"_id": doc['_id']}
            
            # Check if the imported video exists in the database.
            flag_exist = True
            for collection in self.database.list_collection_names():
                if self.database[collection].find_one(regex_find) != None:
                    succeeded -= 1
                    failed += 1
                    flag_exist = False
                    error_log += 'Warning: Failed to import. ' + doc['_id'] + ' exists.\n'
                    break
            if flag_exist:
                collection = self.database[collection_name]
                collection.insert_one(doc)
            
            # Print the progress.
            progress += 1
            progress_percent = floor(progress / total_progress * 100)
            if progress_percent // 10 != print_label:
                msg = r'Progress (Checking existence): {}% ({}/{}).'.format(progress_percent, 
                                 progress, total_progress)
                print(msg)
                print_label = progress_percent // 10

        if error_log != '':
            with open(Model.IMPORT_ERROR_LOG_PATH, 'a', encoding='utf8') as error_output:
                error_output.write(error_log)
            
        return succeeded, failed
    
    def show_all_videos(self):
        doc_list = list()
        for collection in self.database.list_collection_names():
            doc_list.append(self.database[collection].find_one())
            
        return doc_list

class ClassifyData(object):
    """ Class:
    Classify the input data.
    """
    
    pattern = re.compile(r'(.*)_(.*)_(.*)_(.*)_(.*)\.(?:.*)')

    @staticmethod
    def init_data_folder(folder):
        """ Function:
        Batch import.
        """
        
        video_no = list()
        video_name = list()
        actress_name_list = list()
        type_list = list()
        quality = list()
        doc_list = list()
        tmp = set()
        
        # Count the times of succeeded and failed.
        succeeded = 0
        failed = 0
        
        input_path = 'data\\' + folder[folder.rfind('/') + 1:] + '.log'

        input_text_list = list()
        with open(input_path, 'r', encoding='utf8') as input_file:
            input_text_list = [line for line in input_file]
            
        total_progress = len(input_text_list)
        progress = 0
        print_label = 0
        for line_text in input_text_list:
            match = ClassifyData.pattern.match(line_text)
            
            if match:
                doc = dict()
                
                # Full video name.
                doc['_id'] = match.group(0)
                
                # Video No..
                doc['No'] = match.group(1)
                video_no.append(match.group(1))
                
                # Video name.
                doc['Video name'] = match.group(2)
                video_name.append(match.group(2))
                
                # Actress's name.
                tmp = match.group(3).split(', ')
                doc['Actress name'] = tmp
                actress_name_list.append(tmp)
                
                # Video genre and Favorite.
                tmp = match.group(4).split(', ')
                if 'Favorite' in tmp:
                    doc['Favorite'] = True
                else:
                    doc['Favorite'] = False
                    
                doc['Type'] = tmp
                type_list.append(tmp)
                
                # Video quality.
                doc['Quality'] = match.group(5)
                quality.append(match.group(5))
                
                # Location.
                doc['Location'] = folder
                
                # Documents' list.
                doc_list.append(doc)
                
                succeeded += 1
            else:
                print('Warning: The file', line_text[:-1], 
                      'doesn\'t match the expression.')
                with open(Model.IMPORT_ERROR_LOG_PATH, 'a', encoding='utf8') as error_output:
                    error_msg = 'Warning: ' + line_text[:-1] + ' doesn\'t match the expression.\n'
                    error_output.write(error_msg)
                failed += 1
            
            # Print the progress.
            progress += 1
            progress_percent = floor(progress / total_progress * 100)
            if progress_percent // 10 != print_label:
                msg = r'Progress (Loading): {}% ({}/{}).'.format(progress_percent, 
                                 progress, total_progress)
                print(msg)
                print_label = progress_percent // 10
        
        return doc_list, succeeded, failed
                    
    @staticmethod
    def init_data_manual(filename):
        """ Function:
        Manually import.
        """
        
        match = ClassifyData.pattern.match(filename[(filename.rfind('/') + 1):])
        if match:
            tmp = match.group(4).split(', ')
            
            return {'_id': match.group(0), 'No': match.group(1), 
                    'Video name': match.group(2), 
                    'Actress name': match.group(3).split(', '), 
                    'Favorite': 'Favorite' in tmp, 
                    'Type': tmp, 'Quality': match.group(5), 
                    'Location': filename[:filename.rfind('/')]}
        else:
            return False
