# HEADERS --------------------------------
# coding = utf-8
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group: G 4
# Student names: Mayoro BADJI & Diarra TALL
# -----------------------------------------

# import the libraries
import codecs
import json
import sys
import time
# socket specifically designed to handle HTTP requests
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
# create a HTTP connection, as a client
from httplib import HTTPConnection
from threading import Thread # Thread Management
from urlparse import parse_qs  # Parse POST data
# byzantine code
from byzantine_behavior import compute_byzantine_vote_round1 \
                                as byzantine_vote
from byzantine_behavior import compute_byzantine_vote_round2 \
                                as byzantine_vector

# Global variables for HTML templates
vote_frontpage_template = ''
vote_result_template = ''

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
        :param node_id: id of the vessel (host address in the
                                            IP address)
        :param vessel_list: list of the vessels
        """
        HTTPServer.__init__(self,server_address, handler)
        # server_address = 10.1.0.vessel_id
        self.vessel_id = node_id
        self.vessels = vessel_list
        # here all nodes are considered honest generals
        self.byzantine = False
        # store of each general vote
        self.votes =  {}
        # store of votes received by each general
        self.vectors = {}
        # the vote result
        self.vote_result = None

    # -------------------------------- Agreement Functions ------------------

    def get_vector_to_send(self):
        """ Return the vector to send to the other generals

        :return vector: a list of votes
        """
        vector = []
        votes = []
        i = 0

        # Gather all the votes in a vector
        for val in self.votes.values():
            votes.append(val)

        # duplicate the votes for each general
        # so we can have a vector for each general
        # [[True,False,..., True],[True,False,..., True],...]
        # TODO: Generalize
        while i < 2:
            vector.append(votes)
            i += 1

        return vector

    def get_result(self):

        index_vector = 0
        subindex_vector = 0
        temp_list = []
        final_list = []

        values = self.vectors.values()

        # compare each element of the vector list
        # [0,1,2],[0,1,2]
        # TODO: Generalize
        while subindex_vector < 3:
            while index_vector < 2:
                temp_list.append(values[index_vector]
                                                [subindex_vector])
                index_vector += 1

            final_list.append(self.get_max(temp_list))
            del temp_list[:]

            index_vector = 0
            subindex_vector += 1

        self.vote_result = self.get_max(final_list)

    def get_max(self, list):
        """ Get the maximum of True or False variables in a list

        :return result: False where there are more False than True in list
                        True otherwise
        """
        result = False
        attack = 0
        retreat = 0

        for value in list:
            if value is not None :
                if value: attack += 1
                else:     retreat += 1

        if attack > retreat:
            result = True
        if attack == retreat:
            result = None

        return result

    # -------------------------------- Communication Functions --------------

    def contact_general(self, general_ip, path, step, votes):
        """ Contact a general with a set of votes to transmit to it

        :param general_ip: the ip of the general to contact
        :param path: the path of the request
        :param step : the step at which the protocol is (vote | vector)
        :param votes: the vote(s) to transmit
        :return success : True if everything goes well, False otherwise
        """

        success = False

        # encode the fields in a json format
        post_content = json.dumps({'step':step,'value': votes})

        # format the HTTP headers with the type of data being transported
        headers = {"Content-type": "application/json"}

        try:
            # contact vessel:PORT_NUMBER since they all use the same port
            # set a timeout, after which the connection fails if nothing happened
            connection = HTTPConnection("%s:%d" % (general_ip, PORT_NUMBER),
                                        timeout = 180)
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
            print "Error while contacting %s" % general_ip
            # print the error given by Python
            print(e)

        return success

    def propagate_value_to_generals(self, path, step, votes_set):
        """ Send broadcast information to all the generals

        :param path: the path of the request
        :param step : the step at which the protocol is
                        (vote | vector)
        :param votes_set: a list of votes to send to each general
        """

        i = 0

        # the votes_set set is to send to all generals
        for general in self.vessels:
            success_contact = False
            # avoid send to yourself
            if general != ("10.1.0.%s" % self.vessel_id):

                while not success_contact:
                    # send each element of vote_set to a general
                    success_contact = self.contact_general \
                        (general, path, step, votes_set[i])

                i += 1


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
        global vote_frontpage_template, vote_result_template

        # We set the response status code to 200 (OK)
        self.set_HTTP_headers(200)

        html_reponse = ""

        # get the content of the frontpage file
        vote_frontpage_template = self.get_file_content \
            ('server/vote_frontpage_template.html')


        temp = "Votes \n" + str(self.server.votes.values()) + \
               "\n\nVectors \n" + str(self.server.vectors.values())

        # get the content of the result file
        vote_result_template = self.get_file_content \
                                   ('server/vote_result_template.html') \
                               % (temp + "\n\nFinal Result " +
                                  str(self.server.vote_result))
        if self.path == "/":
            # format the html response
            html_reponse = vote_frontpage_template + \
                            vote_result_template

        elif "/vote" in self.path:
            # format the html response
            # return only the last part
            html_reponse = vote_result_template

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

    def handle_post_from_vessel(self, step, value, source_ip):
        """ Handle a POST request received from a general

        :param step : the step at which the algorithm is vote | vector
        :param value : the propagated votes
        :param source_ip : the ip of the general that sends the POST
                            needed for the vote storage
        :return : a tuple of 2 values vote_to_propagate, vector_to_propagate
                    that specifies if a propagation of a vote, vector is
                    needed after the handle of the POST
        """

        vote_to_propagate = None
        vector_to_propagate = None

        # get the id of the source (last byte)
        source_id = int(source_ip[7:])

        # vote step
        if step == 'vote' :
            # insert the new value in the votes store
            self.server.votes[source_id] = value

            # the current vessel may be an honest general
            # in that case, check if the vote store is full
            if not self.server.byzantine and len(self.server.votes) == 3:
                # get the vector to propagate
                vector_to_propagate = self.server.get_vector_to_send()

            # the current vessel may be a byzantine
            # in that case, check if only the current node's vote remains
            elif self.server.byzantine and len(self.server.votes) == 2 :
                # make it vote and store it for a later propagation
                vote_to_propagate = byzantine_vote(2, True)

                # add a random value to the votes store
                self.server.votes[self.server.vessel_id] = vote_to_propagate[-1]

                # get the vector to propagate
                vector_to_propagate = byzantine_vector(2,3, True)

        # vector step
        elif step == 'vector' :
            # insert the new value in the vectors tore
            self.server.vectors[source_id] = value
            # check if the vector list is full
            # the current vessel vector is not included
            if len(self.server.vectors) == 2:
                # calcul the result of the vote
                self.server.get_result()

        return vote_to_propagate, vector_to_propagate

    def handle_post_from_browser(self,path):
        """ Handles a POST request received from a browser

        :param path: the path of the request
        :return a list of votes to send to each general
                attack -> [True,True,...,True]
                retreat -> [False,False,...,False]
                byzantine -> [True,False,...,True] if all the generals
                have voted
                            None otherwise
        """

        vote = None

        # TODO: Generalize

        # it's an attack
        if path == '/vote/attack':
            # add it to the votes list
            self.server.votes[self.server.vessel_id]= True
            # set the vote variable to send to the other generals
            vote = [True, True] # 2 other nodes
        # it's a retreat
        elif path == '/vote/retreat':
            # add it to the votes list
            self.server.votes[self.server.vessel_id] = False
            # set the vote variable to send to the other generals
            vote = [False, False]
        # it's a byzantine vote
        elif path == '/vote/byzantine':
            # set the byzantine boolean
            self.server.byzantine = True
            # the byzantine general waits for all the honest generals'
            # votes
            # check if those votes have been received
            if len(self.server.votes) == 2: # 2 honest generals

                # make the byzantine node vote
                vote = byzantine_vote(2, True)

                # add a random value to the votes store
                self.server.votes[self.server.vessel_id] = vote[-1]
                # drop this value from the list
            # if all the votes from the honest generals
            # have not yet been received do nothing

        return vote

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

        """

        print("POST request received on path %s" % self.path)
        propagate_vote = False
        propagate_vector = False
        votes = ''
        vectors = ''
        vote_step = 'vote'
        vector_step = 'vector'

        # application / json --> POST request from a general
        if self.headers["Content-type"] == "application/json" :

            # read the content of the file
            post_body = self.parse_POST_request()
            post_body = json.loads(post_body)


            # get the votes received
            step, value = post_body["step"], post_body["value"]

            # handle the post
            handle_post = self.handle_post_from_vessel \
                                (step, value, self.client_address[0])

            # in handle_post we have a tuple of 2 values
            # vote_to_propagate and vector_to_propagate
            # both set to None if there is nothing to propagate
            # on both sides
            if handle_post[0] is not None:
                propagate_vote = True
                votes = handle_post[0]

            if handle_post[1] is not None:
                propagate_vector = True
                vectors = handle_post[1]

            self.set_HTTP_headers()

        # www-urlencoded... --> POST request from a client browser
        elif self.headers["Content-type"] == \
                "application/x-www-form-urlencoded":

            # handle the POST received
            votes = self.handle_post_from_browser(self.path)

            # votes is None only
            # if the node is byzantine
            # and all the honest generals have not sent their votes yet
            if votes is not None:
                # in here, there are 2 possibilities
                # 1- the current vessel is an honest general
                # 2- the current vessel is a byzantine and all the honest
                #    generals have sent their votes

                # in both cases, the vote must be propagated to the other
                # generals
                propagate_vote = True

                # In the second case, the byzantine node must propagate
                # its vector to the other nodes
                if self.server.byzantine:
                    propagate_vector = True
                    vectors = byzantine_vector(2,3,True)

            self.set_HTTP_headers()

        # propagate the current general vote to the other generals
        if propagate_vote:
            thread_vote = Thread(target=self.server.propagate_value_to_generals,
                                 args=(self.path, vote_step, votes))
            thread_vote.daemon = True
            thread_vote.start()

        # propagate the vector of votes received from the other generals
        if propagate_vector:
            thread_vect = Thread(target=self.server.propagate_value_to_generals,
                                 args=(self.path, vector_step, vectors))
            thread_vect.daemon = True
            time.sleep(2)
            thread_vect.start()

#------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------
# Execute the code
if __name__ == '__main__':

    ## read the templates from the corresponding html files
    # .....

    general_list = []
    general_id = 0
    # Checking the arguments
    if len(sys.argv) != 3: # 2 args, the script and the general name
        print("Arguments: general_ID number_of_generals")
    else:
        # We need to know the general IP
        general_id = int(sys.argv[1])
        # We need to write the other generals IP, based on the knowledge of their number
        for i in range(1, int(sys.argv[2])+1):
            general_list.append("10.1.0.%d" % i) # We can add ourselves, we have a test in the propagation

    # We launch a server
    server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, general_id, general_list)
    print("Starting the server on port %d" % PORT_NUMBER)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Stopping Server")
#------------------------------------------------------------------------------------------------------
