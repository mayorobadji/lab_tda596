# coding=utf-8
#------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: G4
# Student names: Mayoro BADJI & Diarra TALL
#------------------------------------------------------------------------------------------------------
# We import various libraries
import sys  # Retrieve arguments
import codecs
import time
import json
import ast
import cgi
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler  # Socket specifically designed to handle HTTP requests
from httplib import HTTPConnection  # Create a HTTP connection, as a client (for POST requests to the other vessels)
from random import randint
from threading import Thread  # Thread Management
from urllib import urlencode  # Encode POST content into the HTTP header
from urlparse import parse_qs  # Parse POST data

#------------------------------------------------------------------------------------------------------


# Global variables for HTML templates
board_frontpage_footer_template = ""
board_frontpage_header_template = ""
boardcontents_template = ""
entry_template = ""

#------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 80
#------------------------------------------------------------------------------------------------------




#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
    #------------------------------------------------------------------------------------------------------
    # 3 variables added here : elect_started, lead_found, lead_id
    def __init__(self, server_address, handler, node_id, vessel_list):
        # We call the super init
        HTTPServer.__init__(self,server_address, handler)
        # we create the dictionary of values
        self.store = {}
        # We keep a variable of the next id to insert
        self.current_key = -1
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = vessel_id
        # The list of other vessels
        self.vessels = vessel_list
        # check whether an election has started or not
        self.elect_started = False
        # check whether a leader has been found or not
        self.lead_found = False
        # the leader id
        self.lead_id = None
    #------------------------------------------------------------------------------------------------------
    # We add a value received to the store
    def add_value_to_store(self, value, key=None):
        # We add the value to the store
        if key is not None:
            self.current_key = int(key)
        else:
            self.current_key += 1
        self.store[self.current_key] = value
        return self.current_key
    #------------------------------------------------------------------------------------------------------
    # We modify a value received in the store
    # return True if the modification succeed, False otherwise
    def modify_value_in_store(self,key,value):
        result_modify = True
        # here key is a str
        key = int(key)
        # We test if the key exists in the store
        if key in self.store: # The key exists
            self.store[key] = value
        else: # The key does not exist
            print "Internal error: Modify"
            result_modify = False

        return result_modify
    #------------------------------------------------------------------------------------------------------
    # We delete a value received from the store
    # return True if the suppression succeed, False otherwise
    def delete_value_in_store(self,key):
        # we delete a value in the store if it exists
        result_delete = True
        key = int(key)
        # We test if the value exists
        if key in self.store:  # The key exists
            del self.store[key]
        else:  # The key does not exist
            print " Internal error: Delete"
            result_delete = False

        return result_delete

    """ This function returns the next neighbour of a given vessel
            (ring simulation)
    """
    def get_neighbour(self, vessel_id):
        # if the vessel is the last element of the list
        # then it's neighbour is the first element
        if str(vessel_id) == self.vessels[-1][7:]:
            return '1'
        else:
            return str(vessel_id + 1)

    """ Starts the leader election process
        PS: executed as a Thread
    """
    def start_elect(self):
        # generate a random time the vessel will wait for
        # before starting an election process
        print "\n -------------------------- Starting the election process\n\n"
        wait = randint(1, 5)
        time.sleep(wait)

        # check if an election has already started
        if not self.elect_started:
            # append your id to the election message
            value = str(self.vessel_id)
            # append the path, the action and the key in fields
            fields = self.fill_fields("/elect/", "elect", self.get_neighbour(self.vessel_id))
            # propagate the message to your neighbour
            self.propagate_value_to_vessels(fields[0], fields[1],"", value, False,fields[2])

    """ Handles an election message received from 
        another vessel
    """
    def handle_elect(self, e_msg):

        value = []
        # we need to set the elect_started flag only once
        if not self.elect_started:
            self.elect_started = True
        # if your id is the first element of e_msg
        # then your election message has made it through the ring
        # str(self.vessel_id) = "1" and e_msg[0] = "'1'"
        if str(self.vessel_id) == e_msg[0]:
            # select the leader
            self.select_leader(e_msg)
        else: # otherwise add yourself to e_msg and propagate
            if type(e_msg) == list:
                value.extend(e_msg)
            else:
                value.append(e_msg)
            value.append(str(self.vessel_id))
            # get your neighbour address
            # append the path, the action and the key in fields
            fields = self.fill_fields("/elect/", "elect", self.get_neighbour(self.vessel_id))
            # propagate
            self.propagate_value_to_vessels(fields[0],fields[1],"",value,False,fields[2])

    """ Chooses the leader once the vessel's election message 
        has reached all the nodes in the ring
    """
    def select_leader(self, e_msg):
        value = []
        # set the leader boolean
        self.lead_found = True
        # set the leader id flag
        # here the leader is the one with the max host address
        self.lead_id = max(e_msg,key=int)
        # now propagate
        value.append(self.lead_id)
        # append the path, the action and the key in fields
        fields = self.fill_fields("/lead/", "lead", self.get_neighbour(self.vessel_id))
        # propagate
        self.propagate_value_to_vessels(fields[0], fields[1], "", value, False,fields[2])

    """ Confirms the new leader specified in a leader message
        received from another vessel
    """
    def confirm_leader(self,e_msg):
        # check the leader's flag
        if not self.lead_found:
            self.lead_found = True
            self.lead_id = e_msg[0]
            # append the path, the action and the key in fields
            fields = self.fill_fields("/lead/", "lead", self.get_neighbour(self.vessel_id))
            # propagate
            self.propagate_value_to_vessels(fields[0], fields[1], "", e_msg, False,fields[2])

        if self.lead_id == str(self.vessel_id):
            print "\n\nI am the leader"
        else:
            print "\n\nOur leader is 10.1.0.%s" % (self.lead_id)
        print "\n -------------------------- Ending the election process\n\n"

    """ This is a toolbox function """
    def fill_fields(self,path,action,receiver):
        fields = []
        fields.append(path)
        fields.append(action)
        fields.append(receiver)
        return fields

    #------------------------------------------------------------------------------------------------------
    # Contact a specific vessel with a set of variables to transmit to it
    def contact_vessel(self, vessel_ip, path, action, key, value):
        # the Boolean variable we will return
        success = False
        # The variables must be encoded in the URL format, through urllib.urlencode
        #post_content = urlencode({'action': action, 'key': key, 'value': value})
        post_content = json.dumps({'action': action, 'key': key, 'value': value})
        # the HTTP header must contain the type of data we are transmitting, here URL encoded
        #headers = {"Content-type": "application/x-www-form-urlencoded"}
        headers = {"Content-type": "application/json"}
        # We should try to catch errors when contacting the vessel
        try:
            # We contact vessel:PORT_NUMBER since we all use the same port
            # We can set a timeout, after which the connection fails if nothing happened
            connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout = 30)
            # We only use POST to send data (PUT and DELETE not supported)
            action_type = "POST"
            # We send the HTTP request
            connection.request(action_type, path, post_content, headers)
            # We retrieve the response
            response = connection.getresponse()
            # We want to check the status, the body should be empty
            status = response.status
            # If we receive a HTTP 200 - OK
            if status == 200:
                success = True
        # We catch every possible exceptions
        except Exception as e:
            print "Error while contacting %s" % vessel_ip
            # printing the error given by Python
            print(e)

        # we return if we succeeded or not
        return success
    #------------------------------------------------------------------------------------------------------
    # We send a received value to all the other vessels of the system
    # added broadcast variable to take unicast into account
    def propagate_value_to_vessels(self, path, action, key, value, broadcast=True, receiver=None):
        if broadcast:
            # We iterate through the vessel list
            for vessel in self.vessels:
                success_contact = False
                # We should not send it to our own IP, or we would create an infinite loop of updates
                if vessel != ("10.1.0.%s" % self.vessel_id):
                    while not success_contact:
                        success_contact = self.contact_vessel(vessel, path, action, key, value)
        else: # this is an unicast propagation
            vessel = "10.1.0.%s" % (receiver)
            self.contact_vessel(vessel,path,action,key,value)
#------------------------------------------------------------------------------------------------------







#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# This class implements the logic when a server receives a GET or POST request
# It can access to the server data through self.server.*
# i.e. the store is accessible through self.server.store
# Attributes of the server are SHARED accross all request handling/ threads!
class BlackboardRequestHandler(BaseHTTPRequestHandler):
    #------------------------------------------------------------------------------------------------------
    # We fill the HTTP headers
    def set_HTTP_headers(self, status_code = 200):
        # We set the response status code (200 if OK, something else otherwise)
        self.send_response(status_code)
        # We set the content type to HTML
        self.send_header("Content-type","text/html")
        # No more important headers, we can close them
        self.end_headers()
    #------------------------------------------------------------------------------------------------------
    # a POST request must be parsed through urlparse.parse_QS, since the content is URL encoded
    def parse_POST_request(self, json_parse=True):
        post_data = ""
        # We need to parse the response, so we must know the length of the content
        length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(length)
        # we can now parse the content using parse_qs
        if not json_parse:
            post_data = parse_qs(post_data,keep_blank_values=1)
        # we return the data
        return post_data
    #------------------------------------------------------------------------------------------------------
    #------------------------------------------------------------------------------------------------------
    # Request handling - GET
    #------------------------------------------------------------------------------------------------------
    # This function contains the logic executed when this server receives a GET request
    # This function is called AUTOMATICALLY upon reception and is executed as a thread!
    def do_GET(self):
        print("Receiving a GET on path %s" % self.path)
        # Here, we should check which path was requested and call the right logic based on it
        self.do_GET_Index()
    #------------------------------------------------------------------------------------------------------
    # GET logic - specific path
    #------------------------------------------------------------------------------------------------------
    def do_GET_Index(self):
        # We use the global variables here so we need to recall them
        global board_frontpage_footer_template, board_frontpage_header_template
        global boardcontents_template, entry_template

        # We set the response status code to 200 (OK)
        self.set_HTTP_headers(200)

        # get the content of the header file
        board_frontpage_header_template = self.get_file_content('server/board_frontpage_header_template.html')

        # check if there is any entry in the server store
        if len(self.server.store) > 0:
            # if there is at least one, fill the entries' forms
            entry_template = self.get_entry_forms()
        else:
            # otherwise reset the entry_template !! very important
            entry_template = ""


        # get the content of the boardcontents file
        # and fill the variables in this file
        board_info = "Board @ 10.1.0." + str(self.server.vessel_id)
        boardcontents_template = self.get_file_content('server/boardcontents_template.html') % (board_info,entry_template)

        # get the content of the footer file
        board_frontpage_footer_template = self.get_file_content('server/board_frontpage_footer_template.html') % ("10.1.0.%s" % (self.server.lead_id))

        # format the html response
        html_reponse = board_frontpage_header_template + boardcontents_template + board_frontpage_footer_template

        self.wfile.write(html_reponse)

    #------------------------------------------------------------------------------------------------------
    """ This function returns the content of a simple file
        @param filename      : the path of the file
        @return file_content : the content of filename in a string object
    """
    def get_file_content(self,filename):
        # open the file
        file = codecs.open(filename,'r',"utf-8")
        # read the content of filename
        file_content = file.read()
        return file_content

    """ This function creates an html form for each entry in the form
            @return file_content : the content of filename in a string object
    """
    def get_entry_forms(self):
        entry_forms = ""
        prefix = "entries/"
        # create a form for each entry found in store
        # and concatenate the forms in entry_form
        for id, entry in self.server.store.items():
            # construct the form action with the prefix and the id of the entry
            # useful when modifying or deleting this entry
            action = prefix + str(id)
            entry_forms += self.get_file_content('server/entry_template.html') % (action, id, entry)

        return entry_forms
    #------------------------------------------------------------------------------------------------------
    #------------------------------------------------------------------------------------------------------
    # Request handling - POST
    #------------------------------------------------------------------------------------------------------
    def do_POST(self):
        print("Receiving a POST on %s" % self.path)
        # parse the body of the POST
        propagate = False
        action = ''

        # TODO: need to test if the leader was found

        # application / json --> POST request from a vessel
        if self.headers["Content-type"] == "application/json" :

            # read the content of the file
            post_body = self.parse_POST_request()
            post_body = json.loads(post_body)

            action, entry_key, post_entry = post_body["action"], post_body["key"], post_body["value"]

            # check if it's a regular POST or
            # a leader election POST
            if self.path != "/elect/" and self.path != "/lead/":

                # regular POST originated by a vessel to the leader
                if self.server.lead_id == str(self.server.vessel_id):
                    propagate = True
                    # handle the post
                    handle_result = self.handle_post_from_vessel(action, entry_key, post_entry, False)
                    if handle_result is None:
                        self.set_HTTP_headers(400)
                    else:
                        if self.path == "/entries":
                            entry_key = handle_result

                # regular POST originated by the leader
                else:
                    propagate = False
                    if self.handle_post_from_vessel(action,entry_key,post_entry) is None:
                        self.set_HTTP_headers(400)

            # election POST
            else:
                # handle the election request received
                # and control if any error occurs
                if not self.handle_post_from_vessel(action,entry_key,post_entry):
                    self.set_HTTP_headers(400)

        # www-urlencoded... --> POST request from a client browser
        elif self.headers["Content-type"] == "application/x-www-form-urlencoded":

            # parse the content with parse_qs
            post_body = self.parse_POST_request(False)
            # get the entry
            post_body = self.handle_formatting(post_body)
            post_entry = post_body["entry"]

            # POST on /entries --> addition of a new entry
            if self.path == "/entries":
                action = "add"

                # if this vessel is the leader then
                if self.server.lead_id == str(self.server.vessel_id):
                    # add the new value to the store
                    # and store the key for this entry
                    entry_key = self.server.add_value_to_store(post_entry)
                    # this add request must be propagated
                    propagate = True
                    self.set_HTTP_headers()
                else:  # this request should be sent to the leader
                    if not self.server.propagate_value_to_vessels(self.path,action,"x",post_body["entry"],False,self.server.lead_id):
                        self.set_HTTP_headers(400)
                    else:
                        self.set_HTTP_headers()

            # a POST on /entries/%d means an modification or a suppression
            # of a new entry
            elif self.path[:9] == "/entries/":
                # Get the id
                entry_key = self.path[9:]
                # check whether it's a modify or a delete
                if post_body["delete"][0] == "0":   action = "modify"
                else:   action = "delete"

                # if this vessel is the leader then
                # this add request must be propagated to the others vessels
                if self.server.lead_id == str(self.server.vessel_id):
                    propagate = True
                    if action == "modify" and not self.server.modify_value_in_store(entry_key,post_entry):
                            error = True
                    if action == "delete" and not self.server.delete_value_in_store(entry_key):
                        error = True
                else:  # this request should be sent to the leader
                    if self.server.propagate_value_to_vessels(self.path,action,entry_key,post_body["entry"],False,self.server.lead_id):
                        pass

        # If we want to retransmit what we received to the other vessels
        # Like this, we will just create infinite loops!
        if propagate:
            # do_POST send the message only when the function finishes
            # We must then create threads if we want to do some heavy computation
            #
            # Random content
            thread = Thread(target=self.server.propagate_value_to_vessels,args=(self.path,action, entry_key, post_entry) )
            # We kill the process if we kill the server
            thread.daemon = True
            # We start the thread
            thread.start()
        #------------------------------------------------------------------------------------------------------
        # POST Logic
        #------------------------------------------------------------------------------------------------------

    """
    """
    def handle_post_from_leader(self):
       pass

    """
    """
    def send_post_to_leader(self):
        pass

    """
    """
    def send_post_to_vessels(self):
        pass

    """ This function handles a POST request received from another vessel (propagation)
            @param action        : the action propagated (add/modify/delete)
            @param key           : the key of the entry to add/delete/modify
            @param value         : the value of the entry to add/delete/modify
            @return status       : boolean which indicates if everything is ok
    """
    def handle_post_from_vessel(self, action, key, value, from_leader=True):
        status = None

        # if it's an addition, add it to the store
        if action == 'add':
            if from_leader:
                status = self.server.add_value_to_store(value,key)
            else:
                status = self.server.add_value_to_store(value)
        elif action == 'modify':
            if not self.server.modify_value_in_store(key,value):
                status = None
        elif action == 'delete':
            if not self.server.delete_value_in_store(key):
                status = None
        # it can also be a leader election message
        elif action == 'elect':
            # return the headers now
            self.set_HTTP_headers()
            self.server.handle_elect(value)
        elif action == "lead":
            self.set_HTTP_headers()
            self.server.confirm_leader(value)

        if status is not None and action != "elect" and action != "lead":
            self.set_HTTP_headers()
        return status

    """ This function returns a proper format of a post request body
         old format : [['a'],['b'],['c']]
         new format : ['a','b','c']
     """

    def handle_formatting(self, dict):
        dicto = {}
        for k,v in dict.items():
            # v = v.replace('\"', '+')
            v[0] = v[0].replace('[', '')
            v[0] = v[0].replace(']', '')
            v[0] = v[0].replace("\'", "")
            #v = v.replace(" ", "")
            dicto[k] = v[0]
        return dicto

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

    thread = Thread(target=server.start_elect)

    try:
        thread.start()
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Stopping Server")
#------------------------------------------------------------------------------------------------------
