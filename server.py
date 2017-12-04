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
# Create a HTTP connection, as a client
from httplib import HTTPConnection
from random import randint
from threading import Thread  # Thread Management
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

    # -------------------------------- Store Functions ----------------------

    def add_value_to_store(self, value, seq = None, source = None,
                           key = None):
        """ Add a new value to the store

        :param value: the value to add
        :param seq: the Logical Clock of the POST request
                    which triggered this addition
        :param source: the vessel address which originated the
                        POST request
        :param key: the key of the new value to add
        :return: the new key inserted
        """

        conflict = False
        # if the seq parameter is None
        # -> it's a local addition
        if seq is None:
            # update the last sequence number
            self.last_seq_number += 1
            # the next key of the value to add
            self.current_key += 1
            # source is a client web browser
            # we assume that it's the current vessel
            # more practical for the store organization
            source = "10.1.0.%d" % (self.vessel_id)
            # add the value at the end of the store
            self.store[self.current_key] = [value,
                                            self.last_seq_number,
                                            source]
        else:
            # otherwise the seq corresponds to a POST
            # which has been received from another vessel
            self.current_key += 1
            # if the received POST happened 'after'
            # the last event
            if seq >= self.last_seq_number:
                self.last_seq_number = seq + 1
            elif seq < self.last_seq_number: # otherwise
                self.last_seq_number += 1
            self.store[self.current_key] = [value, seq, source]

            # classify the store then
            self.store = self.classify_store(self.store)

        return self.current_key

    def classify_store (self,store):
        """ Add a new value to the store

        :param store: classify the store based on the values
                      of the LC and the IP source address
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

    def delete_value_in_store(self,key):
        """ Delete an entry in the store

        :param key: the key of the entry to delete
        :return: True if the suppression succeeds, False otherwise
        """
        # check if the value exists
        if key in self.store:
            del self.store[key]
            return True
        else:
            print " Delete error: %d doesn't exist in store" % (key)
            return False

    def modify_value_in_store(self,key,value):
        """ Modify the value of an entry in the store

        :param key: the key of the value being modified
        :param value: the new value to add
        :return: True if the modification succeeds, False otherwise
        """

        # check if the key exists
        if key in self.store:
            # modify the value
            self.store[key] = value
            return True
        else:
            print "Modify error: %d doesn't exist in the store" % (key)
            return False

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
                                   'value': value, 'LS':seq_number})
        # format the HTTP headers with the type of data being transported
        headers = {"Content-type": "application/json"}

        try:
            # contact vessel:PORT_NUMBER since they all use the same port
            # set a timeout, after which the connection fails if nothing happened
            connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout = 30)
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
        """ Send unicast/broadcast information to one/all the vessel(s)

        :param path: the path of the request
        :param action: the action to perform on value
        :param key: the key of value
        :param value: the value itself
        :param seq_number: the sequence of the POST propagated (LS(value))
        """

        #TODO: after x attempts, just drop it

        # We iterate through the vessel list
        for vessel in self.vessels:
            success_contact = False
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != ("10.1.0.%s" % self.vessel_id):
                while not success_contact:
                    success_contact = self.contact_vessel(vessel, path,
                                                        action, key,
                                                        value,seq_number)


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
                           % (action, id, entry)

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

    def handle_post_from_vessel(self, action, key, value, source, seq):
        """ Handle a POST request received from a vessel -- propagation

        :param action: the action to perform on the propagated value
        :param key: the key of the propagated value
        :param value: the propagated value itself
        :param source: the ip address of the vessel which propagated
                the POST
        :param seq: the timestamp of the POST
        :return status: None if something goes wrong or an integer
        """

        # update the logical clock

        status = 1

        # if it's an addition, add it to the store
        if action == 'add':
            status = self.server.add_value_to_store(value, seq, source, key)
        if action == 'modify':
            if not self.server.modify_value_in_store(int(key),value):
                status = None
        elif action == 'delete':
            if not self.server.delete_value_in_store(int(key)):
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
            fields.append(self.server.add_value_to_store
                                            (post_body['entry']))

        # it's a modification or a suppression
        if '/entries/' in path:
            # get the id : path = /entries/id
            key = self.path[9:]

            # check whether it's a modification or a suppression
            if post_body['delete'][0] == "0":
                # fill the POST request field
                fields.append('modify')
                # modify the new value
                if not self.server.modify_value_in_store(int(key),
                                                      post_body['entry']):
                    return None
            else:
                fields.append('delete')

                if not self.server.delete_value_in_store(int(key)):
                    return None

            # add the key
            fields.append(key)

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
        print("POST request received on path %s" % self.path)
        propagate = False
        action = ''
        seq_number = 0

        # application / json --> POST request from a vessel
        if self.headers["Content-type"] == "application/json" :
            propagate = False

            # read the content of the file
            post_body = self.parse_POST_request()
            post_body = json.loads(post_body)

            action, entry_key, post_entry, post_seq\
                        = post_body["action"], \
                            post_body["key"], \
                            post_body["value"], \
                            post_body["LS"]

            # handle the post
            handle_result = self.handle_post_from_vessel\
                                        (action, entry_key,
                                        post_entry,self.client_address[0],
                                            post_seq)

            if handle_result is None:
                self.set_HTTP_headers(404)

        # www-urlencoded... --> POST request from a client browser
        elif self.headers["Content-type"] == \
                "application/x-www-form-urlencoded":

            # a propagation will be needed
            propagate = True

            # get the seq number of the new POST
            seq_number = self.server.last_seq_number + 1

            # parse the content with parse_qs and format it correctly
            post_body = self.handle_formatting\
                            (self.parse_POST_request(False))
            # get the actual value
            post_entry = post_body['entry']

            # handle the POST received
            handle_post = self.handle_post_from_browser(self.path,
                                                        post_body)

            if handle_post is None: # something went wrong
                self.set_HTTP_headers(404)
            else:
                # make the affectations
                action,entry_key = handle_post
                self.set_HTTP_headers()

        # propagate to the other vessels
        if propagate:
            # do_POST send the message only when the function finishes
            # We must then create threads if we want to do some heavy computation
            #
            # Random content
            thread = Thread(target=self.server.propagate_value_to_vessels,
                            args=(self.path,action, entry_key, post_entry,
                                  seq_number) )
            # We kill the process if we kill the server
            thread.daemon = True
            # We start the thread
            thread.start()
        #------------------------------------------------------------------------------------------------------
        # POST Logic
        #------------------------------------------------------------------------------------------------------






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
