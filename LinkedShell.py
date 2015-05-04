#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
from requests.auth import HTTPBasicAuth
from abc import ABCMeta, abstractmethod
import subprocess
import os
import sys

class SparqlClient:

    """Minimal Class to access SparqlEndpoints"""

    def __init__(self, endpoint, user, passw, auth):
        self.endpoint = endpoint;
        self.user = user;
        self.passw = passw;
        self.defaultHeaders = { "accept":"application/sparql-results+json" }
        self.defaultAuth = None;
        if(user!=None and passw!=None):
            if(auth==None or auth=="digest"):
                self.defaultAuth = HTTPDigestAuth(self.user, self.passw)
            else:
                self.defaultAuth = HTTPBasicAuth(self.user, self.passw)

    def execute(self, query, handler=None):

        """ Execute the given SPARQL SELECT Query
        Returns the json dict derived from the application/sparql+json response for the query
        In case a TupleQueryResultHandler was given the results are processed by the handler.
        """  

        if(self.defaultAuth!=None):
            r = requests.get(self.endpoint, auth=self.defaultAuth, headers=self.defaultHeaders, params={"query":query})
        else:
            r = requests.get(self.endpoint, headers=self.defaultHeaders, params={"query":query})

        if (r.status_code==404):
            raise Exception("404 : not found " + self.endpoint);        
        if (r.status_code==401):
            raise Exception("401 : unauthorized " + self.user + " " + self.passw)
        if (r.status_code==503):
            raise Exception("503 : server error ")
        if(handler==None):
            return r.json();
        else:
            j = r.json();
            handler.startQueryResult(j["head"]["vars"]);
            for bindingSet in j["results"]["bindings"]:
                handler.handleSolution(bindingSet);
            handler.endQueryResult();

class TupleQueryResultHandler:

    """Base Class of SPARQL SELECT Query handlers"""
    
    @abstractmethod
    def startQueryResult(self,heads):

        """ Handle the start of the query result, defaults to pass """

        pass;

    @abstractmethod
    def handleSolution(self,bindingSet):

        """ Handle each bindingSet of the query result, defaults to pass """

        pass;

    @abstractmethod
    def endQueryResult(self):

        """ Handle the end of the query result, defaults to pass """

        pass;        

class TerminalPrinter(TupleQueryResultHandler):

    """Class to handle application/sparql-results+json results by printing them to the terminal"""    

    def startQueryResult(self,heads):
        self.heads = heads;
        for head in heads:
            print "binding: %s" % head;
        print ""

    def handleSolution(self,bindingSet):
        for head in self.heads:
            print "%s:%s" % (head, bindingSet[head]["value"]);
        print "";

class CommandRunner(TupleQueryResultHandler):

    def startQueryResult(self,heads):
        self.heads = heads
        pass

    def handleSolution(self,bindingSet):
        print ("Running %s : %s " % (bindingSet["key"]["value"],bindingSet["value"]["value"])),
        if(bindingSet["key"]["value"].startswith("Step")):
            try :
                with open(os.devnull, "w") as f:
                    subprocess.check_call(bindingSet["description"]["value"].replace("$ ",""), shell=True, stdout=f, stderr=f)
                print " success"
            except subprocess.CalledProcessError as e:
                print " failed: ",e.returncode, e.output
        else:
            print ""

# MAIN 
# RUN THE DEFAULT QUERY WITH A COMMANDRUNNER RESULT HANDLER 

def main(endpoint, user, passw, auth, query):
    client = SparqlClient(endpoint,user,passw,auth);
    try:
        """ Execute the given query and print the results to the terminal """
        client.execute(query, CommandRunner());
    except Exception as ex:
        print ex.message


endpoint = "http://sparql.turnguard.com";
user = None;
passw = None;
auth = None;

if  __name__ =='__main__':
    
    query = "prefix sbg:<http://www.openlinksw.com/ontology/stepbyguide#> prefix sof:<http://www.openlinksw.com/ontology/software#> prefix dcterms:<http://purl.org/dc/terms/> prefix xsd:<http://www.w3.org/2001/XMLSchema#> prefix rdfs:<http://www.w3.org/2000/01/rdf-schema#> SELECT ?key ?value ?description WHERE {{ <<s>> dcterms:title ?value; dcterms:description ?description . BIND(\"Title\" AS ?key) BIND(\"-1\"^^xsd:integer AS ?index)} UNION { <<s>> sbg:hasStep ?step . ?step dcterms:title ?value; sbg:hasIndex ?index; dcterms:description ?description . BIND(CONCAT(\"Step \", ?index) AS ?key) } } ORDER BY ?index".replace("<s>",sys.argv[1])

    main(endpoint,user,passw,auth,query)
