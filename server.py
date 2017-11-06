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
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler  # Socket specifically designed to handle HTTP requests
from httplib import HTTPConnection  # Create a HTTP connection, as a client (for POST requests to the other vessels)
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
    #------------------------------------------------------------------------------------------------------
    # We add a value received to the store
    def add_value_to_store(self, value):
        # We add the value to the store
        self.current_key += 1
        self.store[self.current_key] = value
        return self.current_key
    #------------------------------------------------------------------------------------------------------
    # We modify a value received in the store
    def modify_value_in_store(self,key,value):
        # we modify a value in the store if it exists
        result_modify = false
        # We test if the value exists
        if key in self.store: #The key exist
            self.store[key] = value
            result_modify = true
        else: #THe key does not exist
            print "Internal error: Modify"

        return result_modify

    #------------------------------------------------------------------------------------------------------
    # We delete a value received from the store
    def delete_value_in_store(self,key):
        # we delete a value in the store if it exists
        result_delete = false
        # We test if the value exists
        if key in self.store:  # The key exist
            del self.store[key]
            result_delete = true

        else:  # THe key does not exist
            print "Internal error: Delete"

        return result_delete
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
    def propagate_value_to_vessels(self, path, action, key, value):
        # We iterate through the vessel list
        for vessel in self.vessels:
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != ("10.1.0.%s" % self.vessel_id):
                # A good practice would be to try again if the request failed
                # Here, we do it only once
                self.contact_vessel(vessel, path, action, key, value)
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
        # We use the global variables here so we need to recall them here
        global board_frontpage_footer_template, board_frontpage_header_template
        global boardcontents_template, entry_template

        # We set the response status code to 200 (OK)
        self.set_HTTP_headers(200)

        # get the content of the header file
        board_frontpage_header_template = self.get_file_content('server/board_frontpage_header_template.html')

        # check if there is any entry in the server store
        if len(self.server.store) != 0:
            entry_template = self.get_entry_forms()

        # get the content of the boardcontents file
        # and fill the variables in this file
        boardcontents_template = self.get_file_content('server/boardcontents_template.html') % ("Board @",entry_template)

        # get the content of the footer file
        board_frontpage_footer_template = self.get_file_content('server/board_frontpage_footer_template.html')

        #html_reponse = "<html><head><title>Basic Skeleton</title></head><body>This is the basic HTML content when receiving a GET</body></html>"
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
        action = ""

        # if 'action' is a key of post_body
        # then it's a POST request from another vessel
        if 'action' in post_body :
            success = self.handle_post_from_vessel(post_body['action'],post_body['key'],post_body['value'])
            if success :
                self.set_HTTP_headers(200)

        # no 'action' key in post_body means that
        # it's a POST request from a client browser
        else:
            # this request must be propagated to the others vessels
            propagate = True

            # a POST on /entries means an addition of a new entry
            if self.path == "/entries":
                action = "add"
                # add the new value to the store
                # and store the key for this entry
                entry_key = self.server.add_value_to_store(post_body["entry"][0])


            # a POST on /entries/%d means an modification or a suppression
            # of a new entry
            elif self.path[:9] == "/entries/":
                print "x"



        # return the appropriate headers
        self.set_HTTP_headers()

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
        status = False
        # if it's an addition, add it to the store
        if action[0] == "add":
            val = value[0][2:-2]
            self.server.add_value_to_store(val)
            status = True

        return status


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
