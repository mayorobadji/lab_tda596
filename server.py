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
    def add_value_to_store(self, value):
        # We add the value to the store
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

    """ This function starts the leader election process
        PS: executed as a Thread
    """

    def start_elect(self):

        # the election message
        value = []
        # generate a random time the vessel will wait for
        wait = randint(1, 5)
        time.sleep(wait)

        # check if an election has started
        #TODO: drop the 2nd condition
        if not self.elect_started:
            # append your id to the election message
            value.append(str(self.vessel_id))
            # get your neighbour address
            key = self.get_neighbour(self.vessel_id)
            # fill the other fields
            action = 'elect'
            path = 'elect/started'
            # propagate the message to your neighbour
            self.propagate_value_to_vessels(path, action, key, value, False)
            print "\n -------------------------- Starting of the election process\n\n"

    """ This function handles an election message received from 
        another vessel
    """
    def handle_elect(self, e_msg):
        val = []
        # we need to set the elect_started flag only once
        if not self.elect_started:
            self.elect_started = True
        # if your id is in e_msg
        # then your election message has made it through the ring
        #if e_msg[0] == str(self.ves1sel_id):
        if str(self.vessel_id) == e_msg[0].replace("\'",""):
            print "%s is in the selection" % self.vessel_id
            self.select_leader(e_msg)
        else: # otherwise add yourself and propagate

            val.extend(e_msg)
            val.append(str(self.vessel_id))
            # get your neighbour address
            key = self.get_neighbour(self.vessel_id)
            # fill the other fields
            action = 'elect'
            path = 'elect/received'
            # propagate
            self.propagate_value_to_vessels(path,action,key,val,False)

    """ This function chooses the leader once the election message is completed
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
        key = self.get_neighbour(self.vessel_id)
        # fill the other fields
        action = 'lead'
        path = 'lead/selected'
        # propagate the message to your neighbour
        self.propagate_value_to_vessels(path, action, key, value, False)

    """ This function confirms the new leader specified in the leader message
    """
    def confirm_leader(self,e_msg):
        # check the leader's flag
        if not self.lead_found:
            self.lead_found = True
            self.lead_id = e_msg[0]
            # propagate
            key = self.get_neighbour(self.vessel_id)
            # fill the other fields
            action = 'lead'
            path = 'lead/confirm'
            # propagate the message to your neighbour
            self.propagate_value_to_vessels(path, action, key, e_msg, False)
        print "\n\nOur leader is 10.1.0.%s" % (self.lead_id)
        print "\n -------------------------- End of the election process\n\n"
    #------------------------------------------------------------------------------------------------------
    # Contact a specific vessel with a set of variables to transmit to it
    def contact_vessel(self, vessel_ip, path, action, key, value):
        # the Boolean variable we will return
        success = False
        # The variables must be encoded in the URL format, through urllib.urlencode
        post_content = urlencode({'action': action, 'key': key, 'value': value})
        # the HTTP header must contain the type of data we are transmitting, here URL encoded
        headers = {"Content-type": "application/x-www-form-urlencoded"}
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
    def propagate_value_to_vessels(self, path, action, key, value, broadcast=True):
        if broadcast:
            # We iterate through the vessel list
            for vessel in self.vessels:
                success_contact = False
                # We should not send it to our own IP, or we would create an infinite loop of updates
                if vessel != ("10.1.0.%s" % self.vessel_id):
                    while not success_contact:
                        success_contact = self.contact_vessel(vessel, path, action, key, value)
        else: # this is an unicast propagation
            vessel = "10.1.0.%s" % (key)
            success_contact = self.contact_vessel(vessel,path,action,key,value)

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
    def parse_POST_request(self):
        post_data = ""
        # We need to parse the response, so we must know the length of the content
        length = int(self.headers['Content-Length'])
        # we can now parse the content using parse_qs
        post_data = parse_qs(self.rfile.read(length), keep_blank_values=1)
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
        post_body = self.parse_POST_request()
        propagate = False
        action = ''
        error = False

        # if 'action' is a key of post_body
        # then it's a POST request from another vessel
        if 'action' in post_body :
            # handle the propagated request
            # and control if any occurs
            if not self.handle_post_from_vessel(post_body['action'],post_body['key'],post_body['value']):
                error = True
        # no 'action' key in post_body means that
        # it's a POST request from a client browser
        else:
            # this request must be propagated to the others vessels
            propagate = True
            # get the entry
            post_entry = post_body["entry"][0]

            # a POST on /entries means an addition of a new entry
            if self.path == "/entries":
                action = "add"
                # add the new value to the store
                # and store the key for this entry
                entry_key = self.server.add_value_to_store(post_entry)
            # a POST on /entries/%d means an modification or a suppression
            # of a new entry
            elif self.path[:9] == "/entries/":
                # Get the id
                entry_key = self.path[9:]
                # check whether it's a modify or a delete
                if post_body["delete"][0] == "0":
                    # there the entry in post_entry is modified
                    action = "modify"
                    if not self.server.modify_value_in_store(entry_key,post_entry):
                        error = True
                elif post_body["delete"][0] == "1":
                    # there the entry in post_entry must be deleted
                    action = "delete"
                    if not self.server.delete_value_in_store(entry_key):
                        error = True

        # return the appropriate headers
        if not error :
            self.set_HTTP_headers()
        #TODO: Personnalize the errors messages
        else:
            self.set_HTTP_headers(404)

        # If we want to retransmit what we received to the other vessels
        # Like this, we will just create infinite loops!
        if propagate:
            # do_POST send the message only when the function finishes
            # We must then create threads if we want to do some heavy computation
            #
            # Random content
            thread = Thread(target=self.server.propagate_value_to_vessels,args=(self.path,action, entry_key, post_body["entry"]) )
            # We kill the process if we kill the server
            thread.daemon = True
            # We start the thread
            thread.start()
        #------------------------------------------------------------------------------------------------------
        # POST Logic
        #------------------------------------------------------------------------------------------------------

    """ This function handles a POST request received from another vessel (propagation)
            @param action        : the action propagated (add/modify/delete)
            @param key           : the key of the entry to add/delete/modify
            @param value         : the value of the entry to add/delete/modify
            @return status       : boolean which indicates if everything is ok
    """
    def handle_post_from_vessel(self, action, key, value):
        status = True
        # concrete formatting
        value = self.handle_formatting(value)
        # if it's an addition, add it to the store
        if action[0] == 'add':
            self.server.add_value_to_store(value[0])
        elif action[0] == 'modify':
            status = self.server.modify_value_in_store(key[0],value[0])
        elif action[0] == 'delete':
            status = self.server.delete_value_in_store(key[0])
        # it can also be a leader election message
        elif action[0] == 'elect':
            # return the headers now
            self.set_HTTP_headers()
            self.server.handle_elect(value)
        elif action[0] == "lead":
            self.set_HTTP_headers()
            self.server.confirm_leader(value)
        return status

    """ This function returns a proper format of a post request body
        old format : [['a'],['b'],['c']]
        new format : ['a','b','c']
    """
    def handle_formatting(self, value):
        list = []
        for v in value:
            #v = v.replace('\"', '+')
            v = v.replace('[','')
            v = v.replace(']','')
            v = v.replace("\'","")
            v = v.replace(" ", "")
            list.append(v)
        value = list[0].split(',')
        return value
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
