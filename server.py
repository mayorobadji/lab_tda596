# HEADERS --------------------------------
# coding = utf-8
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: G 4
# Student names: Mayoro BADJI & Diarra TALL
# -----------------------------------------
#TODO: improve the leader election --> election msgs with priorities
#TODO: in do_GET() --> wait for the leader to be found before responding

# import the libraries
import codecs
import json
import sys
import time
# Socket specifically designed to handle HTTP requests
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
# Create a HTTP connection, as a client
from httplib import HTTPConnection
from random import randint
from threading import Thread # Thread Management
from operator import itemgetter
from urlparse import parse_qs  # Parse POST data

# Global variables for HTML templates
board_frontpage_footer_template = ''
board_frontpage_header_template = ''
boardcontents_template = ''
entry_template = ''

# Static variable definition
PORT_NUMBER = 80



""" Main class for the vessels

This class represents a vessel
It contains the main actions a vessel can perform

"""
class BlackboardServer(HTTPServer):

    def __init__(self, server_address, handler, node_id, vessel_list):
        """ Vessel constructor

        :param server_address: IP address of the vessel
        :param handler: HTTP events handler
        :param node_id: id of the vessel (host address in the IP address)
        :param vessel_list: list of the other vessels
        """

        HTTPServer.__init__(self,server_address, handler)
        # create the dictionary of values
        self.store = {}
        # store the next id to insert
        self.current_key = -1
        # store the last sequence number
        self.last_seq_number = 0
        # server_address = 10.1.0.vessel_id
        self.vessel_id = vessel_id
        self.vessels = vessel_list
        # the latest delete
        self.recent_delete = []
        # the pending delete
        self.pending_delete = {}
        # the pending modification
        self.pending_modif = {}
        # used to record the first the vessel receives a POST
        self.started = ""

    # ---------------------- Updates Functions from Browser to Vessel  ----------------------


    def add_value_from_browser(self, value):
        """ Add a entry to the store

        upon the reception of a POST on /entries from a browser,
        this function adds a new value to the store

        :param value: the new value to add
        :return self.current_key: the key of the new value inserted
        """

        # set the logical clock for this addition
        self.last_seq_number += 1

        # increment the last key of the store
        self.current_key += 1

        # set the source field to the local vessel id
        source = "%d" % (self.vessel_id)

        # add the triplett [value, LC, src] at the end of the store
        self.store[self.current_key] = [value, self.last_seq_number,
                                            source]

        # return the key of the value inserted
        return self.current_key

    def delete_value_from_browser(self, key):
        """ Delete an entry in the store

        upon the reception of a POST on /entries/key from a browser,
        this function deletes the value at the index key in the store

        :param key: the key of the entry to delete
        :return value_deleted: the value deleted or None
        """

        # the key may be in the store
        if key in self.store:

            # get the value to delete
            value_deleted = self.store[key]

            # delete it
            del self.store[key]

            # store the suppression in the recent deletes history
            self.recent_delete.append(value_deleted)
        # the key may not be in the store
        else:
            # maybe the value has already been deleted
            # before
            value_deleted = None

        return value_deleted

    def modify_value_from_browser(self, key, new_value):
        """ Modify an entry in the store

        upon the reception of a POST on /entries/key from a browser,
        this function replaces a value in the store by new value

        :param key: the key of the value to modify
        :param new_value: the new value
        :return <list>: the couple [old_value, new_value] or None
        """


        # the key may be in the store
        if key in self.store:

            # get the old value to replace
            old_value = self.store[key]

            # set the logical clock for this modification
            self.last_seq_number += 1

            # set the source field to the the local vessel id
            source = "%d" % (self.vessel_id)

            # modify the value
            self.store[key] = [new_value,self.last_seq_number,
                                   source]

            return [old_value, self.store[key]]
        else:
            return None

    # ---------------------- Updates Functions from Vessel to Vessel  ----------------------


    def add_value_from_vessel(self, value, ts, source):
        """ Add a entry to the store

        upon the reception of a POST on /entries from a vessel,
        this function adds a new value to the store

        :param value: the value to add
        :param ts: the timestamp of the POST request received
        :param source: the id of the vessel that has sent the request
        :param key: the key of the value to add (received in the request)
        :return self_current_key: the key of the value inserted
        """

        # the POST may have happened 'after'
        # the last local event
        if ts >= self.last_seq_number:
            # set the new logical clock
            self.last_seq_number = ts + 1
        else: # otherwise
            self.last_seq_number += 1

        # increment the last key of the store
        self.current_key += 1

        # store the value received at the end of the store
        self.store[self.current_key] = [value, ts, source]

        # then classify the values in the store based on their LCs
        self.store = self.classify_store(self.store)

        # once the store is classified, one may need to check if there
        # are stored updates that need to be perform
        self.apply_pending_updates()

        return self.current_key

    def delete_value_from_vessel(self, key, value_to_delete):
        """ Delete an entry in the store

        upon the reception of a POST on /entries/key from a vessel,
        this function removes an entry from the store

        :param key: the key of the entry to delete (received in the request)
        :param value_to_delete: the value to suppress
        :return value_in_store: the value suppressed or None
        """
        value_in_store = None

        # if the value have been deleted recently
        # there is no need to delete it again
        # so the operation goes only if value_to_delete
        # has not been deleted recently
        if value_to_delete not in self.recent_delete:

            # the key may exist in the store
            if key in self.store:

                # get the value in store
                value_in_store = self.store[key]

                # since the 2 vessels may be in inconsistent states
                # the value to delete should correspond to the value
                # in the store at this point
                # same value, same LC, same IP address
                if value_in_store == value_to_delete:
                    del self.store[key]

                    # store the delete
                    self.recent_delete.append(value_in_store)
                # the values may also not correspond
                else:
                    # then one may store the suppression as a
                    # pending delete
                    self.pending_delete[key] = value_to_delete
                    value_in_store = None
            # the key may not exist in the store
            else:
                # the message may not have been arrived yet
                # so the delete should be stored
                self.pending_delete[key] = value_to_delete

        return value_in_store

    def modify_value_from_vessel(self, key, new_value, value_to_modify):
        """ Modify an entry in the store

        upon the reception of a POST on /entries/key from a vessel,
        this function replaces an entry in the store (old_value) by new_value

        :param key: the key of the value to modify
        :param new_value: the new value
        :param value_to_modify: the old value to modify in the store
        :return <list>: the couple [old_value, new_value] or None
        """

        # the key may exist in the store
        if key in self.store:

            # get the old value
            val_in_store = self.store[key]

            # check if val_in_store corresponds to the value to modify
            if val_in_store == value_to_modify:

                # if the modification request received happened after
                # the timestamp of the value in the store
                if value_to_modify[1] >= val_in_store[1]:
                        # modify
                        self.store[key] = new_value
                # otherwise
                # the request is out-of-date
                else: return None
            else:
                # the 2 vessels are in inconsistent states maybe
                # store the modification
                self.pending_modif[key] = [value_to_modify,new_value]
                return None
        else:
            # the message may has not been arrived yet
            # store the modification
            self.pending_modif[key] = [value_to_modify,new_value]
            return None

        return [val_in_store,self.store[key]]


    # ---------------------- Triggering Updates Functions   ----------------------

    def classify_store (self,store):
        """ classify the store based on the values
                      of the LCs and the IP source addresses

        :param store: the store to classify
        :return store_stored: a classified store
        """
        store_sorted = {}
        key = 0

        # sort the values of the store
        # based on the lowest LC
        # when 2 values have the same LC, the one with
        # the lowest IP address comes first
        sorted_values = sorted(store.values(), key = itemgetter(1,2))

        # create a new store with the sorted values
        for val in sorted_values:
            store_sorted[key] = val
            key += 1

        return store_sorted

    def apply_pending_updates(self):
        """ Apply the pending updates to the data in the store
        """

        # check if there are values to delete
        for key,to_del in self.pending_delete.items():

            # if the value to delete is in the store
            if key in self.store and self.store[key] == to_del:

                # delete it from the store and from the pending deletes
                del(self.store[key])
                del(self.pending_delete[key])

                # append the deletion to the recent deletes
                self.recent_delete.append(to_del)

        # check if there are values to modify
        for key,to_mod in self.pending_modif.items():

            # in to_mod : [[value_to_modify], [new_value]]
            if key in self.store and self.store[key] == to_mod[0]:
                # check the clocks
                if to_mod[0][1] >= self.store[key][0]:
                    # if the modification happened after the clock of the POST
                    # in the store
                    self.store[key] = to_mod[1]

                # if we got here, the modification is no more pending
                del(self.pending_modif[key])




    # -------------------------------- Communication Functions --------------

    def contact_vessel(self, vessel_ip, path, action, key, value, seq_number):
        """ Contact a vessel with a set of fields to transmit to it

        :param vessel_ip: the ip of the vessel to contact
        :param path: the path of the request
        :param action: the action to perform on value
        :param key: the key of value
        :param value: the value itself
        :param seq_number: the sequence of the POST propagated (LS(value))
        :return: True if everything goes well, False otherwise
        """

        success = False
        # encode the fields in a json format
        post_content = json.dumps({'action': action, 'key': key,
                                   'value': value, 'TS':seq_number})
        # format the HTTP headers with the type of data being transported
        headers = {"Content-type": "application/json"}

        try:
            # contact vessel:PORT_NUMBER since they all use the same port
            # set a timeout, after which the connection fails if nothing happened
            connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout = 180)
            # only POST used here
            action_type = "POST"
            # send the HTTP request
            connection.request(action_type, path, post_content, headers)
            # retrieve the response
            response = connection.getresponse()
            # check the status
            status = response.status

            if status == 200: # 200 OK
                success = True
        # catch every possible exceptions
        except Exception as e:
            print "Error while contacting %s" % vessel_ip
            # print the error given by Python
            print(e)

        return success

    def propagate_value_to_vessels(self, path, action, key, value, seq_number):
        """ Send broadcast information to one/all the vessel(s)

        :param path: the path of the request
        :param action: the action to perform on value
        :param key: the key of value
        :param value: the value itself
        :param seq_number: the sequence of the POST propagated (LS(value))
        """

        attempts = 0
        # We iterate through the vessel list
        for vessel in self.vessels:
            success_contact = False
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != ("10.1.0.%s" % self.vessel_id):
                while not success_contact:
                    success_contact = self.contact_vessel(vessel, path,
                                                        action, key,
                                                        value,seq_number)
                    attempts += 1

                    # after 15 attempts, just drop it
                    if attempts == 15:
                        print("Failed to reach %s " % (vessel) )
                        break


""" HTTP Handler class

This class handles the requests received (GET, POST)
The server attributes are accessible through self.server.*
Attributes of the server are SHARED accross all request handling/ threads!

"""
class BlackboardRequestHandler(BaseHTTPRequestHandler):

    # -------------------------------- Common Functions ----------------------

    def set_HTTP_headers(self, status_code = 200):
        """ Format an HTTP response

        :param status_code: the status code of the response
        :return: Nothing
        """

        # set the response status code
        self.send_response(status_code)
        # set the content type to HTML
        self.send_header("Content-type","text/html")
        # close the headers
        self.end_headers()

    # -------------------------------- GET Logic Functions -------------------

    def get_file_content(self,filename):
        """ Return the content of a file

        :param filename: the path of the file to read
        :return file_content: the content of the file
        """

        # open the file
        file = codecs.open(filename,'r',"utf-8")
        # read and return the content of filename
        file_content = file.read()

        return file_content

    def get_entry_forms(self):
        """ Create a form for each entry in the store

        :return entry_forms: the forms
        """

        entry_forms = ""
        prefix = "entries/"

        # create a form for each entry found in store
        # and concatenate the forms in entry_form
        for id, entry in self.server.store.items():
            # construct the form action with the prefix and the id of the entry
            # useful when modifying or deleting this entry
            action = prefix + str(id)
            entry_forms += self.get_file_content('server/entry_template.html')\
                           % (action, id, entry[0])

        return entry_forms

    def do_GET(self):
        """ Executed automatically upon a GET request reception

        :return: Nothing
        """

        print("GET request received on path %s" % self.path)
        self.do_GET_Index()

    def do_GET_Index(self):
        """ Return an HTML page upon a GET request

        :return: Nothing
        """

        # recall the global variables
        global board_frontpage_footer_template, entry_template
        global boardcontents_template, board_frontpage_header_template

        # We set the response status code to 200 (OK)
        self.set_HTTP_headers(200)

        # get the content of the header file
        board_frontpage_header_template = self.get_file_content\
            ('server/board_frontpage_header_template.html')

        # check if there is any entry in the server store
        if len(self.server.store) > 0:
            # if there is at least one, fill the entries' forms
            entry_template = self.get_entry_forms()
        else:
            # otherwise reset the entry_template
            entry_template = ""


        # get the content of the boardcontents file
        # and fill the variables in this file
        board_info = "Board @ 10.1.0." + str(self.server.vessel_id)
        boardcontents_template = self.get_file_content\
                                     ('server/boardcontents_template.html') \
                                 % (board_info,entry_template)

        # get the content of the footer file
        board_frontpage_footer_template = self.get_file_content\
                            ('server/board_frontpage_footer_template.html')
        #                     % ("10.1.0.%s" % (self.server.lead_id))

        # format the html response
        html_reponse = board_frontpage_header_template + \
                       boardcontents_template + \
                       board_frontpage_footer_template

        self.wfile.write(html_reponse)

    # -------------------------------- POST Logic Functions ------------------

    def parse_POST_request(self, json_parse=True):
        """ Parse a POST request received from a browser or a vessel

        :param json_parse: if the data is json-encoded or url-encoded
        :return post_data: the post content
        """

        post_data = ""

        # get the length of the content
        length = int(self.headers['Content-Length'])
        # read the content
        post_data = self.rfile.read(length)

        # if the data is not json-encoded
        if not json_parse: # it's url-encoded then
            # so it should be parse with parse_qs
            post_data = parse_qs(post_data,keep_blank_values=1)

        return post_data

    def handle_post_from_vessel(self, action, key, value, source, ts):
        """ Handle a POST request received from a vessel -- propagation

        :param action: the action to perform on the propagated value
        :param key: the key of the propagated value
        :param value: the propagated value itself
        :param source: the ip address of the vessel which propagated
                the POST
        :param ts: the timestamp of the POST
        :return status: None if something goes wrong or an integer
        """

        status = 1

        # if it's an addition, add it to the store
        if action == 'add':
            status = self.server.add_value_from_vessel(value, ts, source)
        if action == 'modify':
            if self.server.modify_value_from_vessel(int(key),value[1],
                                                         value[0]) is None:
                status = None
        elif action == 'delete':
            if self.server.delete_value_from_vessel(int(key),value) is None:
                status = None

        if status is not None:
            # everything wen't well, an HTTP response should be sent
            self.set_HTTP_headers()

        return status

    def handle_post_from_browser(self,path,post_body):
        """ Handles a POST request received from a browser

        :param path: the path of the request
        :param post_body: the body of the POST
        :return fields: a list -- [action, key] of the value in post_body
        """
        fields = []

        # it's an addition
        if path == '/entries':
            fields.append('add') # the action to be propagated

            # add the value to the store
            # and store the new key in fields
            fields.append(self.server.add_value_from_browser
                                            (post_body['entry']))

        # it's a modification or a suppression
        elif '/entries/' in path:
            # get the id : path = /entries/id
            key = self.path[9:]


            # check whether it's a modification or a suppression
            if post_body['delete'][0] == "0":
                # fill the POST request field
                fields.append('modify')
                # add the key
                fields.append(key)
                # modify the new value
                # the function will return [old triplet, new triplet]
                modify = self.server.modify_value_from_browser(int(key),
                                                      post_body['entry'])
                if modify is None: return None
                else:  fields.append(modify)
            else:
                # the action to perform
                fields.append('delete')
                # add the key
                fields.append(key)
                # the value to delete
                delete = self.server.delete_value_from_browser(int(key))
                # nothing was deleted
                if delete is None:  return None

                # append the value to delete to the list
                else: fields.append(delete)

        return fields

    def handle_formatting(self, dict):
        """ Return a proper format of a post request body after parsing

        the old format may be : {key_1:["'val_1'"],key_2:["'val_2'"]}
        the format returned will be : {key_1:"val_1",key_2:"val_2"}
        :param dict:
        :return:
        """

        dicto = {}
        for k,v in dict.items():
            v[0] = v[0].replace('[', '')
            v[0] = v[0].replace(']', '')
            v[0] = v[0].replace("\'", "")
            dicto[k] = v[0]
        return dicto

    def do_POST(self):
        """ Executed automatically upon a POST request reception

        :return: Nothing
        """
        if self.server.last_seq_number == 0:
            self.server.started = str(datetime.now())

        print("POST request received on path %s" % self.path)
        propagate = False
        action = ''
        timestamp = 0

        # application / json --> POST request from a vessel
        if self.headers["Content-type"] == "application/json" :
            propagate = False

            # read the content of the file
            post_body = self.parse_POST_request()
            post_body = json.loads(post_body)

            print post_body

            action, entry_key, post_entry, post_seq\
                        = post_body["action"], \
                            post_body["key"], \
                            post_body["value"], \
                            post_body["TS"]

            # handle the post
            handle_result = self.handle_post_from_vessel\
                                        (action, entry_key,
                                        post_entry,self.client_address[0][7:],
                                            post_seq)

            if handle_result is None:
                self.set_HTTP_headers(404)

        # www-urlencoded... --> POST request from a client browser
        elif self.headers["Content-type"] == \
                "application/x-www-form-urlencoded":

            # a propagation will be needed
            propagate = True

            # set the timestamp (used when the POST request
            # is propagated)
            timestamp = self.server.last_seq_number + 1

            # parse the content with parse_qs and format it correctly
            post_body = self.handle_formatting\
                            (self.parse_POST_request(False))

            # get the actual value
            post_entry = post_body['entry']

            # handle the POST received
            handle_post = self.handle_post_from_browser(self.path,
                                                        post_body)

            if handle_post is None: # nothing was deleted
                propagate = False
            else:
                # if the POST request is on /entries (addition)
                # then in handle_post we just have the action
                # and the key of the new value
                if len(handle_post) == 2:
                    action, entry_key = handle_post
                elif len(handle_post) == 3: # otherwise (modification, suppression)
                      # we may have another field which is
                      # the value to delete
                    action,entry_key,post_entry = handle_post

                self.set_HTTP_headers()

        # propagate to the other vessels
        if propagate:
            # do_POST send the message only when the function finishes
            # We must then create threads if we want to do some heavy computation
            #
            # Random content
            thread = Thread(target=self.server.propagate_value_to_vessels,
                            args=(self.path,action, entry_key, post_entry,
                                  timestamp) )
            # We kill the process if we kill the server
            thread.daemon = True
            # We start the thread
            thread.start()
        #------------------------------------------------------------------------------------------------------
        # POST Logic
        #------------------------------------------------------------------------------------------------------

        print "Started at " + self.server.started
        print "Finished at " + str(datetime.now())

#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Execute the code
if __name__ == '__main__':

    ## read the templates from the corresponding html files
    # .....

    vessel_list = []
    vessel_id = 0
    # Checking the arguments
    if len(sys.argv) != 3: # 2 args, the script and the vessel name
        print("Arguments: vessel_ID number_of_vessels")
    else:
        # We need to know the vessel IP
        vessel_id = int(sys.argv[1])
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, int(sys.argv[2])+1):
            vessel_list.append("10.1.0.%d" % i) # We can add ourselves, we have a test in the propagation

    # We launch a server
    server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
    print("Starting the server on port %d" % PORT_NUMBER)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Stopping Server")
#------------------------------------------------------------------------------------------------------
