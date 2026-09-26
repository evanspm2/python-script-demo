###################################### Imports
import copy
from XXX import *
from XXX import *
from XXX import CircuitServiceStub
from XXX import DeviceServiceStub
from datetime import datetime
import difflib
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import grpc
from ipaddress import ip_network
import json
from netmiko import ConnectHandler
from netmiko import NetMikoTimeoutException, NetMikoAuthenticationException, ReadTimeout
import os
import pprint
import requests
import smtplib
import sqlite3
import sys
from ttp import ttp

###################################### Class Block
class CircuitCheck:
    
    user_run_mode                   = ""
    user_email_address              = ""
    user_circuit_list               = []
    circuit_count                   = ""
    user_id                         = ""
    device_name                     = ""
    device_model                    = ""
    device_netmiko_type             = ""
    device_ip                       = ""    
    device_username                 = ""
    device_password                 = ""
    mapping_mode_precheck           = "mode 1"
    mapping_mode_postcheck          = "mode 1"
    user_circuit_list_parsed        = []
    suffix_database                 = ".sqlite3"
    email_from                      = "XXX"
    smtp_server                     = "XXX"
    grpc_server                     = "XXX"
    netmiko_read_timeout            = 30
    nc_restapi_server               = "XXX"
   
    def _debug_log_header(self):
        
        #  write debug log header
        debug = _Debug()
        console_message = "Circuit Check Utility"
        debug.console_message(0, console_message, "_email_report()")

        # get date and time
        now = datetime.now()
        date = now.strftime("%y-%m-%d")
        time = now.strftime("%H:%M:%S")

        console_message = "Date : {}".format(date)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "Time : {}".format(time)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "Mapping Mode Precheck: {}".format(CircuitCheck.mapping_mode_precheck)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "Mapping Mode Postcheck: {}".format(CircuitCheck.mapping_mode_precheck)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "SMTP Server: {}".format(CircuitCheck.smtp_server)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "gRPC Server: {}".format(CircuitCheck.grpc_server)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "Netcracker REST API Server: {}".format(CircuitCheck.nc_restapi_server)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "Netmiki Read Timeout: {}".format(CircuitCheck.netmiko_read_timeout)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "Current Directory : {}".format(os.getcwd())
        debug.console_message(2, console_message, "_email_report()")

        console_message = "Current User : {}".format(os.getlogin())
        debug.console_message(2, console_message, "_email_report()")
        
    def _resolve_ip_address(self):

        debug = _Debug()
        console_message = "Resolving device name to IP"
        debug.console_message(0, console_message, "_resolve_ip_address()")

        console_message = "Device name : {}".format(CircuitCheck.device_name)
        debug.console_message(2, console_message, "_resolve_ip_address()")

        console_message = "Sending query to Netcracker REST API at : {}".format(CircuitCheck.nc_restapi_server)
        debug.console_message(2, console_message, "_resolve_ip_address()")

        # query netcracker
        url = "http://{}/api/v1/devices/{}/mgmt-ip".format(CircuitCheck.nc_restapi_server, CircuitCheck.device_name.upper())
        http_resp = requests.get(url)
        
        # exit utility if cannot resolve IP
        if http_resp.status_code != 200:
            console_message = "Expected response status code 200"
            debug.console_message(2, console_message, "_resolve_ip_address()")
            
            console_message = "Received response status code {} : ".format(http_resp.status_code)
            debug.console_message(2, console_message, "_resolve_ip_address()")

            console_message = "Cannot resolve device name {} to IP address".format(CircuitCheck.device_name)
            debug.console_message(2, console_message, "_resolve_ip_address()")

            _Debug.error_message = console_message
            _Debug.error_type = "Resolve Failed"
            
            return "Resolve Failed"

        # convert to dictionary and remove cidr prefix
        dict_response = http_resp.json()
        ip_mask = dict_response['MGMT_IP']
        ip_only = ip_mask.split("/")[0]

        # store result        
        CircuitCheck.device_ip = ip_only
        console_message = "Device IP is : {}".format(CircuitCheck.device_ip)
        debug.console_message(2, console_message, "_resolve_ip_address()")

        return "Success"

    def _determine_type(self):

        debug = _Debug()
        console_message = "Determine device type"
        debug.console_message(0, console_message, "_determine_device_type()")
        
        console_message = "Device type is : Juniper MX Router"
        debug.console_message(2, console_message, "_determine_device_type()")

        # the only supported device type is Juniper
        CircuitCheck.device_netmiko_type             = "juniper_junos"
        CircuitCheck.device_model                    = "mx"

    def run_circuit_check_utility(self):

        debug = _Debug()
        
        # write debug log header
        debug.console_blank_line()
        self._debug_log_header()
        debug.console_blank_line()

        # process command line augments
        self._process_cmdline_arguments()
        debug.console_blank_line()
        
        # resolve ip address
        result = self._resolve_ip_address()
        debug.console_blank_line()
        
        # if resolve failed generate report adn email
        if result == "Resolve Failed":
            self._report_and_email()
            self._exit_utility()
        
        # determine device platform
        self._determine_type()
        debug.console_blank_line()
        
        # open cli session to device
        mxconnect = _MXConnect()
        status = mxconnect.open_cli_session(CircuitCheck.device_ip, CircuitCheck.device_username, CircuitCheck.device_password, CircuitCheck.device_netmiko_type)
        debug.console_blank_line()

        # if login failed generate report and email        
        if status == "Login Failed":
            self._report_and_email()
            self._exit_utility()
        
        # open connection to sql database
        sqldatabse = _SQLDatabase()
        sqldatabse.open_sql_database()
        debug.console_blank_line()

        # create run table if it does not exist
        run_table = _RunTable()
        run_table.create_table_if_not_exist()
        
        # add row to run table for this run
        run_table.create_new_row(CircuitCheck.user_circuit_list, CircuitCheck.user_run_mode, CircuitCheck.device_name, CircuitCheck.user_email_address, CircuitCheck.device_model)

        # create circuit table if it does not exist
        circuit_table = _CircuitTable()
        circuit_table.create_table_if_not_exist()
        
        # set interface map mode
        circuit_map_mode = ""
        
        if CircuitCheck.user_run_mode == "precheck":
            circuit_map_mode = CircuitCheck.mapping_mode_precheck

        if CircuitCheck.user_run_mode == "postcheck":
            circuit_map_mode = CircuitCheck.mapping_mode_postcheck
               
        # process user circuit list
        circuit_processor = _CircuitProcessor()
        circuit_processor.process_user_circuit_list(CircuitCheck.device_name, CircuitCheck.device_model, CircuitCheck.user_run_mode)

        # generate report and email
        self._report_and_email()
        self._exit_utility()

    def _report_and_email(self):

        # generate report
        reporter = _Reporter()
        reporter.generate_report()
        
        # email report
        self._email_report()

    def _exit_utility(self):

        debug = _Debug()
        debug.console_blank_line()
        console_message = "Exiting circuit check utility"
        debug.console_message(0, console_message, "_exit_utility()")
        debug.console_blank_line()
        exit()
        
    def _process_cmdline_arguments(self):

        debug = _Debug()
        console_message = "Process command line arguments"
        debug.console_message(0, console_message, "_process_cmdline_arguments()")

        CircuitCheck.user_run_mode = sys.argv[1]
        CircuitCheck.device_name = sys.argv[2]
        CircuitCheck.user_email_address = sys.argv[3]
        CircuitCheck.user_id = sys.argv[4]
        CircuitCheck.device_username = sys.argv[5]
        CircuitCheck.device_password = sys.argv[6]

        console_message = "Email : {}".format(CircuitCheck.user_email_address)
        debug.console_message(2, console_message, "_process_cmdline_arguments()")

        console_message = "Build User ID : {}".format(CircuitCheck.user_id)
        debug.console_message(2, console_message, "_process_cmdline_arguments()")

        console_message = "Run Mode : {}".format(CircuitCheck.user_run_mode)
        debug.console_message(2, console_message, "_process_cmdline_arguments()")

        console_message = "Device : {}".format(CircuitCheck.device_name)
        debug.console_message(2, console_message, "_process_cmdline_arguments()")

        console_message = "SSH Username : {}".format(CircuitCheck.device_username)
        debug.console_message(2, console_message, "_process_cmdline_arguments()")

        # number of circuits
        CircuitCheck.circuit_count = len(sys.argv) - 7
        console_message = "Circuit Count : {}".format(CircuitCheck.circuit_count )
        debug.console_message(2, console_message, "_process_cmdline_arguments()")

        # copy circuits into user circuit list and convert to lower case
        for i in range(7, len(sys.argv)):
            CircuitCheck.user_circuit_list.append(sys.argv[i].lower())
        
    def _email_report(self):

        # init variables
        email_to = CircuitCheck.user_email_address
        email_subject = _Reporter.report_subject_line
        
        # debug messages
        debug = _Debug()
        console_message = "Email Report"
        debug.console_message(0, console_message, "_email_report()")

        console_message = "To: {}".format(email_to)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "From: {}".format(CircuitCheck.email_from)
        debug.console_message(2, console_message, "_email_report()")

        console_message = "SMTP Server: {}".format(CircuitCheck.smtp_server)
        debug.console_message(2, console_message, "_email_report()")

        # get date and time
        now = datetime.now()
        date = now.strftime("%y-%m-%d")
        time = now.strftime("%H:%M:%S")
        
        console_message = "Timestamp: {} {}".format(date, time)
        debug.console_message(2, console_message, "_email_report()")

        # construct message
        msg = MIMEMultipart()
        msg['To'] = email_to
        msg['From'] = CircuitCheck.email_from
        msg['Subject'] = email_subject
        body = MIMEText(_Reporter.complete_report, 'html')
        msg.attach(body)
              
        # convert user circuit list into a line separated string
        attachment = ""

        for circuit in CircuitCheck.user_circuit_list:
            attachment = attachment + circuit + '\n'

        # attach user circuit list
        msg.attach(MIMEApplication(_Reporter.output_diff_report, Name='outputdiff.html'))
        msg.attach(MIMEApplication(attachment, Name='circuits.txt'))
        msg.attach(MIMEApplication(_Debug.debug_log_email_attachment, Name='debug.txt'))
        
        
        # send email        
        s = smtplib.SMTP(CircuitCheck.smtp_server)
        s.sendmail(CircuitCheck.email_from, email_to, msg.as_string())
        s.quit()
        
###################################### Class Block
class _CircuitProcessor:
    
    def process_user_circuit_list(self, device_name, device_model, user_run_mode):
        mx_circuit_processor = _MXCircuitProcessor()
        mx_circuit_processor.process_mx_circuits(device_name, device_model, user_run_mode )        

###################################### Class Block
class _MXCircuitProcessor:

    interface_configurations = ""
    routing_instance_configurations = ""
    bgp_configuration = ""
    combined_configuration = ""
    parsed_configuration = ""

    def process_mx_circuits(self, device_name, device_model, user_run_mode):

        debug = _Debug()
        interface_mapper = _MXInterfaceMapper()
        signature_mapper = _MXSignatureMatcher()
        
        # get device configuration and parse it
        self._get_device_configuration()
        
        # load circuit list
        circuit_list = CircuitCheck.user_circuit_list
       
        # loop through each circuit in user circuit list
        for index, circuit_name in enumerate(circuit_list, start=1):

            console_message = "Processing circuit {} of {} \"{}\"".format(index, len(circuit_list), circuit_name)
            debug.console_blank_line()
            debug.console_message(0, console_message, "process_mx_circuits()")
            
            # skip circuit if there is no hyphen in name
            if "-" not in circuit_name:
                console_message = "004 : {} : Circuit name does not contain a hyphen".format(user_run_mode)             
                debug.console_message(2, console_message, "process_mx_circuits()")
                continue
            
            # create circuit in database if not exist
            self._create_circuit_in_db(circuit_name, device_name, device_model, user_run_mode)
            
            # skip circuit if circuit was not prechecked and run mode is postcheck
            circuit_table = _CircuitTable()
            result = circuit_table.was_circuit_prechecked(circuit_name)
            if CircuitCheck.user_run_mode == "postcheck" and result == "no":
                console_message = "003 : Postcheck : Circuit has not been prechecked"                
                debug.console_message(2, console_message, "process_mx_circuits()")
                continue          
            
            # map circuit to interface and collect interface data
            result = interface_mapper.map_circuit_to_interface(user_run_mode, circuit_name)
            
            # if no interfaces are found then skip signature detection and continue to next circuit
            if result == "No Match":
                continue
            
            # run signature matcher
            circuit_type = signature_mapper.match_circuit_signature(circuit_name)
            if circuit_type == "No Match":
                continue

            # poll circuit
            mx_poller = _MXPoller()
            mx_poller.poll_mx_circuit(circuit_name, circuit_type)
            
        # add interface polls to run table
        console_message = "Saving interface poll data to run table"
        debug.console_message(0, console_message, "process_mx_circuits()")

        mx_interface_mapper = _MXInterfaceMapper()
        run_table = _RunTable()
        mx_interface_polls_jason = json.dumps(mx_interface_mapper.interface_polls)

        if user_run_mode.lower() == "precheck":
            run_table.update_run_table('mx_interface_polls_precheck', mx_interface_polls_jason)

        if user_run_mode.lower() == "postcheck":
            run_table.update_run_table('mx_interface_polls_postcheck', mx_interface_polls_jason)

        # debug message
        console_message = "Circuit processing complete"
        debug.console_message(0, console_message, "process_mx_circuits()")
        debug.console_blank_line()
    
    def _get_device_configuration(self):
        debug = _Debug()
        mxconnect = _MXConnect()        
        
        # get interface configurations
        console_message = "Getting interface configurations from device"
        debug.console_message(0, console_message, "_get_device_configuration()")
        _MXCircuitProcessor.interface_configurations = mxconnect.run_command("show configuration interfaces | display set")

        # get routing instance configurations        
        console_message = "Getting routing instance configurations from device"
        debug.console_message(0, console_message, "_get_device_configuration()")
        _MXCircuitProcessor.routing_instance_configurations = mxconnect.run_command("show configuration routing-instances | display set")

        # get BGP configuration        
        console_message = "Getting BGP configurations from device"
        debug.console_message(0, console_message, "_get_device_configuration()")
        _MXCircuitProcessor.bgp_configuration = mxconnect.run_command("show configuration protocols bgp | display set")
        
        # combine configurations
        _MXCircuitProcessor.combined_configuration = _MXCircuitProcessor.interface_configurations + _MXCircuitProcessor.routing_instance_configurations + _MXCircuitProcessor.bgp_configuration     

        # parse device configuration        
        console_message = "Parse device configuration"
        debug.console_message(0, console_message, "_get_device_configuration()")
        _MXCircuitProcessor.parsed_configuration = mxconnect.parse_show_config(_MXCircuitProcessor.combined_configuration)
        
        # Exit utility if interface configuration is blank
        if 'interfaces' not in _MXCircuitProcessor.parsed_configuration[0][0]:
            print("Exit utility no interface configurations")
            exit()
        
    def _create_circuit_in_db(self, circuit_name, device_name, device_model, user_run_mode):

        # check if circuit exist in circuit table
        circuit_table = _CircuitTable()
        circuit_exist = circuit_table.is_circuit_in_circuit_table(circuit_name)
        
        # if circuit is not in table then add it
        if circuit_exist == "no":
            circuit_table.add_circuit_to_table(circuit_name)

        # run run table row id
        run_table = _RunTable()
        run_table_row_id_last = run_table.get_run_table_row_id()

        # save information into circuit table
        circuit_table.update_circuit_table(user_run_mode, circuit_name,"run_table_row_id_last",run_table_row_id_last)
        circuit_table.update_circuit_table(user_run_mode, circuit_name,"device_name",device_name)
        circuit_table.update_circuit_table(user_run_mode, circuit_name,"device_model",device_model)


###################################### Class Block
class _MXInterfaceMapper:

    interface_polls = {}

    def map_circuit_to_interface(self, user_run_mode, circuit_name):
        
        debug = _Debug()
        mx_circuit_processor = _MXCircuitProcessor()
        circuit_table = _CircuitTable()
        circuit_interface_list = []

        # extract circuit number from circuit name
        circuit_number = circuit_name.split("-")[0]
        circuit_number_hyphen = circuit_number + "-"

        console_message = "Circuit prefix is \"{}\"".format(circuit_number_hyphen)
        debug.console_message(2, console_message, "map_circuit_to_interface()")

        # Loop through all interfaces on router
        for interface in mx_circuit_processor.parsed_configuration[0][0]['interfaces']:
            
            # Skip interface if description is not configured
            if 'description' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
                continue

            # Store description into variable
            description = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['description']
            
            # Is circuit number and hyphen found inside description
            if circuit_number_hyphen in description.lower():

                console_message = "Circuit prefix found in description on \"{}\"".format(interface)
                debug.console_message(2, console_message, "map_circuit_to_interface()")
                
                console_message = "Circuit mapped to interface \"{}\"".format(interface)
                debug.console_message(2, console_message, "map_circuit_to_interface()")

                console_message = "Circuit name \"{}\"".format(circuit_name)
                debug.console_message(4, console_message, "map_circuit_to_interface()")

                console_message = "Interface description \"{}\"".format(description)
                debug.console_message(4, console_message, "map_circuit_to_interface()")

                # process physical interface
                if not "." in interface:
                    console_message = "\"{}\" is a physical interface did not find \".\" in it's name".format(interface)
                    debug.console_message(4, console_message, "map_circuit_to_interface()")
                    self._process_physical_interface( interface )
                
                # process logical interface
                if '.' in interface:
                    self._process_logical_interface(interface )
                    
                # build interface list
                circuit_interface_list.append(interface)


        # console message
        console_message = "Found {} interfaces with circuit name in description".format(len(circuit_interface_list))
        debug.console_message(2, console_message, "map_circuit_to_interface()")

        # save interface list to circuit table
        console_message = "Saving circuit interface list to circuit table"
        debug.console_message(2, console_message, "map_circuit_to_interface()")
        circuit_interface_list_json = json.dumps(circuit_interface_list)
        circuit_table.update_circuit_table(user_run_mode, circuit_name,"mx_circuit_interfaces",circuit_interface_list_json)
                
        # no interfaces found
        if len(circuit_interface_list) == 0:
            return "No Match"
        
        if len(circuit_interface_list) != 0:
            return "Match"
 
    def _process_physical_interface(self, interface ):
                
        debug = _Debug()
        mx_circuit_processor = _MXCircuitProcessor()

        # collect physical interface information    
        self._collect_physical_info( interface )
        
        #
        unit0_interface = interface + '.0' 
        if unit0_interface in mx_circuit_processor.parsed_configuration[0][0]['interfaces']:
            console_message = "Logical unit 0 was found \"{}\"".format(unit0_interface)
            debug.console_message(6, console_message, "_if_physical_physical()")     
            self._collect_logical_info(unit0_interface)

        if not unit0_interface in mx_circuit_processor.parsed_configuration[0][0]['interfaces']:
            console_message = "Logical unit 0 was not found \"{}\"".format(unit0_interface)
            debug.console_message(6, console_message, "_if_physical_physical()")
        
    def _process_logical_interface(self, interface ):
        
        debug = _Debug()

        # send console message if this is a logical interface
        if "." in interface:
            console_message = "\"{}\" is a logical interface found \".\" in it's name".format(interface)
            debug.console_message(4, console_message, "_process_logical_interface()")

        # collect data on logical interface
        self._collect_logical_info( interface )
        
        # collect data on physical interface
        physical_interface = interface.split('.', 1)
        console_message = "Unit \"{}\" is part of physical interface \"{}\"".format(physical_interface[1], physical_interface[0])
        debug.console_message(4, console_message, "_process_logical_interface()")        
        self._collect_physical_info( physical_interface[0] )
              
    def _collect_physical_info(self, interface ):

        mx_circuit_processor = _MXCircuitProcessor()
        mxconnect = _MXConnect()
        debug = _Debug()
                
        mydict = {
            "name"                      : "",
            "description"               : "",
            "state"                     : "",
            "show_output"               : "",
            "encapsulation"             : "",
            "vlan-tagging"              : "",
            "flexible-vlan-tagging"     : ""            
        }

        console_message = "Collecting information on physical interface \"{}\"".format(interface)
        debug.console_message(4, console_message, "_collect_physical_info()")
               
        # Do not collect information if physical interface is already on list
        if interface in _MXInterfaceMapper.interface_polls:
            console_message = "Information on \"{}\" already collected".format(interface)
            debug.console_message(4, console_message, "_collect_physical_info()")
            return
     
        # save interface name
        mydict['name'] = interface

        # get description on physical interface
        if 'description' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['description'] = "Not Configured"
            console_message = "Description is not configured on physical interface"
            debug.console_message(6, console_message, "_collect_physical_info()")
            
        if 'description' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['description'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['description']
            console_message = "Description set to \"{}\"".format(mydict['description'])
            debug.console_message(6, console_message, "_collect_physical_info()")
        
        # get encapsulation on physical interface
        if 'encapsulation' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['encapsulation'] = "Not Configured"
            
            console_message = "Encapsulation command is not configured on physical interface"
            debug.console_message(6, console_message, "_collect_physical_info")
            
        if 'encapsulation' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['encapsulation'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['encapsulation']

            console_message = "Encapsulation set to \"{}\"".format(mydict['encapsulation'])
            debug.console_message(6, console_message, "_collect_physical_info")

        # is vlan-tagging configured on physical interface
        if 'vlan-tagging' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['vlan-tagging'] = "Not Configured"

            console_message = "vlan-tagging is not configured on physical interface"
            debug.console_message(6, console_message, "_collect_physical_info")

        if 'vlan-tagging' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['vlan-tagging'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['vlan-tagging']

            console_message = "vlan-tagging is configured on physical interface"
            debug.console_message(6, console_message, "_collect_physical_info")

        # is flexible-vlan-tagging configured on physical interface
        if 'flexible-vlan-tagging' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['flexible-vlan-tagging'] = "Not Configured"

            console_message = "flexible-vlan-tagging is not configured on physical interface"
            debug.console_message(6, console_message, "_collect_physical_info")

        if 'flexible-vlan-tagging' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['flexible-vlan-tagging'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['flexible-vlan-tagging']

            console_message = "flexible-vlan-tagging is configured on physical interface"
            debug.console_message(6, console_message, "_collect_physical_info")

        # capture output of show interfaces media command
        console_message = "Collecting output from \"show interfaces {} media\"".format(interface)
        debug.console_message(6, console_message, "_collect_physical_info()")
        cmd = "show interface {} media".format(interface)
        output = mxconnect.run_command(cmd)
        
        # prepend show command to output
        output = CircuitCheck.device_name + "> " + cmd + "\n" + output
        mydict['show_output'] = output
        
        # device not found
        if 'error: device' in output:
            console_message = "Received error message from show output command cannot parse interface status"
            debug.console_message(6, console_message, "_collect_physical_info()")
            console_message = "   Message: \"{}\"".format(output.rstrip())
            debug.console_message(6, console_message, "_collect_physical_info()")
            _MXInterfaceMapper.physical_interface_list.append( mydict )       
            return
            
        # parse interface status from show output
        console_message = "Parsing interface status"
        debug.console_message(6, console_message, "_collect_physical_info()")
        parsed = mxconnect.parse_show_interfaces_media( output )
        
        # found physical interface status
        if 'oper' in parsed[0][0]['show_interfaces']:
            mydict['state'] = parsed[0][0]['show_interfaces']['oper']
            console_message = "Operational state is \"{}\"".format(mydict['state'])
            debug.console_message(6, console_message, "_collect_physical_info()")

        # could not parse physical interface status
        if 'oper' not in parsed[0][0]['show_interfaces']:
            mydict['state'] = "Not Configured"
            console_message = "Could not parse physical interface status"
            debug.console_message(6, console_message, "_collect_physical_info()")     

        # add poll data to variable for addition to run table
        _MXInterfaceMapper.interface_polls[interface] = mydict
       
    def _collect_logical_info(self, interface ):

        mx_circuit_processor = _MXCircuitProcessor()
        mxconnect = _MXConnect()
        debug = _Debug()
                
        mydict = {
            "name"                      : "",
            "unit"                      : "",
            "description"               : "",
            "state"                     : "",
            "family"                    : "",
            "encapsulation"             : "",
            "show_output"               : "",
            "ip"                        : "",
            "mask"                      : ""
        }
        
        console_message = "Collecting information on logical interface \"{}\"".format(interface)
        debug.console_message(4, console_message, "_collect_logical_info()")
        
        # Do not collect information if logical interface is already on list
        if interface in _MXInterfaceMapper.interface_polls:
            console_message = "Information on \"{}\" already collected".format(interface)
            debug.console_message(4, console_message, "_collect_logical_info()")
            return

        # save interface name and unit number
        mydict['name'] = interface
        mydict['unit'] = interface.split('.', 1)[1]
        
        # get description on logical interface
        if 'description' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['description'] = "Not Configured"
            
            console_message = "Description is not configured on logical interface"
            debug.console_message(6, console_message, "_collect_logical_info()")
            
        if 'description' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['description'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['description']

            console_message = "Description set to \"{}\"".format(mydict['description'])
            debug.console_message(6, console_message, "_collect_logical_info()")

        # get encapsulation on logical interface
        if 'encapsulation' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['encapsulation'] = "Not Configured"
            
            console_message = "Encapsulation command is not configured on logical interface"
            debug.console_message(6, console_message, "_collect_logical_info()")
            
        if 'encapsulation' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['encapsulation'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['encapsulation']

            console_message = "Encapsulation set to \"{}\"".format(mydict['encapsulation'])
            debug.console_message(6, console_message, "_collect_logical_info()")

        # get family on logical interface
        if 'family' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['family'] = "Not Configured"
            
            console_message = "Family command is not configured on logical interface"
            debug.console_message(6, console_message, "_collect_logical_info()")
            
        if 'family' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['family'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['family']

            console_message = "Family set to \"{}\"".format(mydict['family'])
            debug.console_message(6, console_message, "_collect_logical_info()")
        
        # get ip on logical interface
        if 'ip' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['ip'] = "Not Configured"
            
            console_message = "IP is not configured on logical interface"
            debug.console_message(6, console_message, "_collect_logical_info()")
            
        if 'ip' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['ip'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['ip']

            console_message = "IP set to \"{}\"".format(mydict['ip'])
            debug.console_message(6, console_message, "_collect_logical_info()")            
            
        # get mask on logical interface
        if 'mask' not in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['mask'] = "Not Configured"
            
            console_message = "Mask is not configured on logical interface"
            debug.console_message(6, console_message, "_collect_logical_info()")
            
        if 'mask' in mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]:
            mydict['mask'] = mx_circuit_processor.parsed_configuration[0][0]['interfaces'][interface]['mask']

            console_message = "Mask set to \"{}\"".format(mydict['mask'])
            debug.console_message(6, console_message, "_collect_logical_info()")            
                
        # capture output of show interfaces command
        console_message = "Collecting output from \"show interfaces {}\"".format(interface)
        debug.console_message(6, console_message, "_collect_logical_info()")
        cmd = "show interfaces {}".format(interface)
        output = mxconnect.run_command(cmd)
                
        # prepend show command to output
        output = CircuitCheck.device_name + "> " + cmd + "\n" + output
        mydict['show_output'] = output
        
        # device not found
        if 'error: device' in output:
            console_message = "Received error message from show output command will not be able to parse interface status"
            debug.console_message(6, console_message, "_collect_logical_info()")
            console_message = "   Message: \"{}\"".format(output.rstrip())
            debug.console_message(6, console_message, "_collect_logical_info()")
            _MXInterfaceMapper.logical_interface_list.append( mydict )       
            return    
        
        # parse interface status from show output
        console_message = "Parsing output"
        debug.console_message(6, console_message, "_collect_logical_info()")
        parsed = mxconnect.parse_show_interfaces_logical( output )

        # found logical interface status
        if 'flag' in parsed[0][0]['show_interfaces']:
            mydict['state'] = parsed[0][0]['show_interfaces']['flag']
            console_message = "Operational state is \"{}\"".format(mydict['state'])
            debug.console_message(6, console_message, "_collect_logical_info()")

        # could not parse logical interface status
        if 'flag' not in parsed[0][0]['show_interfaces']:
            mydict['state'] = "Not Configured"
            console_message = "Could not parse logical interface status"
            debug.console_message(6, console_message, "_collect_logical_info()")

        # add poll data to variable for addition to run table
        _MXInterfaceMapper.interface_polls[interface] = mydict

                 
###################################### Class Block
class _MXConnect:
    
    cli_session = None
    login_status  = ""
    error_message = ""
    
    def open_cli_session(self, device_ip, device_username, device_password, device_netmiko_type):

        # assembly netmiki login information
        login_info = {
            "device_type": device_netmiko_type,
            "host": device_ip,
            "username": device_username,
            "password": device_password,
        }

        # debug message
        debug = _Debug()
        console_message = "Open SSH session to {}".format(device_ip)
        debug.console_message(0, console_message, "open_cli_session()")

        console_message = "Device IP : {}".format(device_ip)
        debug.console_message(2, console_message, "open_cli_session()")

        console_message = "Username : {}".format(device_username)
        debug.console_message(2, console_message, "open_cli_session()")

        console_message = "Module : Netmiko"
        debug.console_message(2, console_message, "open_cli_session()")

        console_message = "Netmiko Device Type".format(device_netmiko_type)
        debug.console_message(2, console_message, "open_cli_session()")
        
        # attempt login and check for exception
        try:
            _MXConnect.cli_session = ConnectHandler( **login_info )
        
        # connection timed out
        except NetMikoTimeoutException:
            console_message = "Connection to {} time out".format(device_ip)
            debug.console_message(2, console_message, "open_cli_session()")
            _MXConnect.login_status = "Login Failed"
            _MXConnect.error_message = console_message
            return _MXConnect.login_status
        
        # authentication failed
        except NetMikoAuthenticationException:
            console_message = "Authentication failed logging in with username {}".format(device_username)
            debug.console_message(2, console_message, "open_cli_session()")
            _MXConnect.login_status = "Login Failed"
            _MXConnect.error_message = console_message
            return _MXConnect.login_status

        # other exception            
        except Exception as e:
            console_message = "An unexpected error occurred when trying to login: {}".format(e)
            debug.console_message(2, console_message, "open_cli_session()")
            _MXConnect.login_status = "Login Failed"
            _MXConnect.error_message = console_message
            return _MXConnect.login_status
        
        # login successful
        debug = _Debug()
        console_message = "Successfully logged into device"
        debug.console_message(2, console_message, "open_cli_session()")
        _MXConnect.login_status = "Login Successful"
        return _MXConnect.login_status
        
    def run_command(self, command):
        output = _MXConnect.cli_session.send_command(command, read_timeout=CircuitCheck.netmiko_read_timeout)
        return output

    def parse_show_config(self, show_output):

        ttp_template = '''
<group name="interfaces**.{{ name }}**" method="table" >
set interfaces {{ name }}{{ignore('.*')}}
</group>

<group name="interfaces**.{{ name }}**" method="table" >
set interfaces {{ name }} description {{ description }}
set interfaces {{ name }} encapsulation {{ encapsulation }}
set interfaces {{ name | let("vlan-tagging", True) }} vlan-tagging
set interfaces {{ name | let("flexible-vlan-tagging", True) }} flexible-vlan-tagging
</group>

<group name="interfaces**.{{ name }}**" functions="sformat('{name}.{unit}', 'name')" method="table">
set interfaces {{ name }} unit {{ unit }}{{ignore('.*')}} 
</group>

<group name="interfaces**.{{ name }}**" functions="sformat('{name}.{unit}', 'name')" method="table">
set interfaces {{ name }} unit {{ unit }} description {{ description }}
set interfaces {{ name }} unit {{ unit }} vlan-id {{ dot1q }}
set interfaces {{ name }} unit {{ unit }} encapsulation {{ encapsulation }}
set interfaces {{ name }} unit {{ unit }} family {{ family }}{{ignore('.*')}}
</group>

<group name="interfaces**.{{ name }}**" functions="sformat('{name}.{unit}', 'name')" method="table">
set interfaces {{ name }} unit {{ unit }} family inet address {{ ip }}/{{ mask }}{{ignore('.*')}}
</group>

<group name="vrf**.{{ vrf }}**" method="table" expand="">
set routing-instances {{ vrf }} description {{ description }}
set routing-instances {{ vrf }} instance-type {{ instance_type }}
set routing-instances {{ vrf }} protocols {{ protocol }}{{ignore('.*')}} 
</group>

<group name="vrf**.{{ vrf }}**.interfaces*" method="table" itemize="interface">
set routing-instances {{ vrf }} interface {{ interface }}
</group>

<group name="bgp**.neighbors**.{{ neighbor_ip }}**" method="table">
set protocols bgp group {{ neighbor_group }} neighbor {{ neighbor_ip }}{{ignore('.*')}} 
</group>
'''
        parser = ttp(data=show_output, template=ttp_template)
        parser.parse()
        results = parser.result()
        return results

    def parse_show_interfaces_media(self, show_output):

        ttp_template = '''
<group name="show_interfaces">
Physical interface: {{interface}}, {{admin}}, Physical link is {{oper}}
</group>
'''
        parser = ttp(data=show_output, template=ttp_template)
        parser.parse()
        results = parser.result()
        return results


    def parse_show_interfaces_logical(self, show_output):

        ttp_template = '''
<group name="show_interfaces" method="table">
    Flags: {{flag}}{{ignore('.*')}}
</group>
'''
        parser = ttp(data=show_output, template=ttp_template)
        parser.parse()
        results = parser.result()
        return results

    def parse_poll_data(self, show_output):
        ttp_template = '''
<group name="remote_pe_up" method="table">
    {{remote_id| exclude("connection-site")}}             {{type}} {{state | equal('Up') | count(var="pe_up", globvar="pe_up_glob")}}{{ignore('.*')}}	
</group>

<group name="mac_count" method="table" default="0">
   {{mac | exclude("MAC") | exclude("address") | count(var="mac_count", globvar="mac_count_glob") }}{{ignore('.*')}}
</group>

<group name="bgp_state" method="table"  default="Cannot_Parse">
  Type: External    State: {{state}}{{ignore('.*')}}
</group>

<group name="arp_count"  default="0">
{{ ether_addr | MAC | count(var="arp_count", globvar="arp_count_glob") }}{{ignore('.*')}}
</group>

<vars name="counters">
pe_up = 0
mac_count = 0
arp_count = 0
</vars>
'''

        parser = ttp(data=show_output, template=ttp_template)
        parser.parse()
        results = parser.result()
        return results


###################################### Class Block
class _MXSignatureMatcher:
    
    routing_instance_name = ""
    bgp_neighbor_ip = ""

    profile_mx_bgp_physical = {
    "term_circuit_name"                          : "internet",
    "term_interface_name_period"                 : "period_no",
    "term_physical_interface_tagging"            : "untagged",
    "term_physical_interface_encapsulation"      : "none",
    "term_logical_unit_0_family"                 : "inet",
    "term_logical_unit_encapsulation"            : "__IQNORE__",
    "term_routing_instance_type"                 : "__IQNORE__",
    "term_routing_instance_protocol"             : "__IQNORE__",
    "term_bgp_neighbor"                          : "check",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }

    profile_mx_bgp_logical = {
    "term_circuit_name"                          : "internet",
    "term_interface_name_period"                 : "period_yes",
    "term_physical_interface_tagging"            : "tagged",
    "term_physical_interface_encapsulation"      : "__IQNORE__",
    "term_logical_unit_0_family"                 : "__IQNORE__",
    "term_logical_unit_encapsulation"            : "none",
    "term_routing_instance_type"                 : "__IQNORE__",
    "term_routing_instance_protocol"             : "__IQNORE__",
    "term_bgp_neighbor"                          : "check",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }
#flexible-ethernet-services,vlan-vpls",

    profile_mx_bgp_irb_vpls_physical = {
    "term_circuit_name"                          : "internet",
    "term_interface_name_period"                 : "period_no",
    "term_physical_interface_tagging"            : "untagged",
    "term_physical_interface_encapsulation"      : "ethernet-vpls",
    "term_logical_unit_0_family"                 : "vpls",
    "term_logical_unit_encapsulation"            : "__IQNORE__",
    "term_routing_instance_type"                 : "__IQNORE__",
    "term_routing_instance_protocol"             : "__IQNORE__",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }

    profile_mx_bgp_irb_vpls_logical = {
    "term_circuit_name"                          : "internet",
    "term_interface_name_period"                 : "period_yes",
    "term_physical_interface_tagging"            : "tagged",
    "term_physical_interface_encapsulation"      : "flexible-ethernet-services,vlan-vpls",
    "term_logical_unit_0_family"                 : "__IQNORE__",
    "term_logical_unit_encapsulation"            : "vlan-vpls",
    "term_routing_instance_type"                 : "__IQNORE__",
    "term_routing_instance_protocol"             : "__IQNORE__",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }

    profile_mx_static_physical = {
    "term_circuit_name"                          : "internet",
    "term_interface_name_period"                 : "period_no",
    "term_physical_interface_tagging"            : "untagged",
    "term_physical_interface_encapsulation"      : "none",
    "term_logical_unit_0_family"                 : "inet",
    "term_logical_unit_encapsulation"            : "__IQNORE__",
    "term_routing_instance_type"                 : "__IQNORE__",
    "term_routing_instance_protocol"             : "__IQNORE__",
    "term_bgp_neighbor"                          : "none",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }
    
    profile_mx_static_logical = {
    "term_circuit_name"                          : "internet",
    "term_interface_name_period"                 : "period_yes",
    "term_physical_interface_tagging"            : "tagged",
    "term_physical_interface_encapsulation"      : "flexible-ethernet-services,vlan-vpls",
    "term_logical_unit_0_family"                 : "__IQNORE__",
    "term_logical_unit_encapsulation"            : "none",
    "term_routing_instance_type"                 : "__IQNORE__",
    "term_routing_instance_protocol"             : "__IQNORE__",
    "term_bgp_neighbor"                          : "none",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }

    profile_mx_vpls_physical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_no",
    "term_physical_interface_tagging"            : "untagged",
    "term_physical_interface_encapsulation"      : "ethernet-vpls",
    "term_logical_unit_0_family"                 : "vpls",
    "term_logical_unit_encapsulation"            : "__IQNORE__",
    "term_routing_instance_type"                 : "vpls",
    "term_routing_instance_protocol"             : "vpls",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }

    profile_mx_vpls_logical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_yes",
    "term_physical_interface_tagging"            : "tagged",
    "term_physical_interface_encapsulation"      : "flexible-ethernet-services,vlan-vpls",
    "term_logical_unit_0_family"                 : "__IQNORE__",
    "term_logical_unit_encapsulation"            : "vlan-vpls",
    "term_routing_instance_type"                 : "vpls",
    "term_routing_instance_protocol"             : "vpls",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }

    profile_mx_l2vpn_physical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_no",
    "term_physical_interface_tagging"            : "untagged",
    "term_physical_interface_encapsulation"      : "ethernet-ccc",
    "term_logical_unit_0_family"                 : "ccc",
    "term_logical_unit_encapsulation"            : "__IQNORE__",
    "term_routing_instance_type"                 : "l2vpn",
    "term_routing_instance_protocol"             : "l2vpn",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }

    profile_mx_l2vpn_logical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_yes",
    "term_physical_interface_tagging"            : "tagged",
    "term_physical_interface_encapsulation"      : "flexible-ethernet-services,vlan-ccc",
    "term_logical_unit_0_family"                 : "__IQNORE__",
    "term_logical_unit_encapsulation"            : "vlan-ccc",
    "term_routing_instance_type"                 : "l2vpn",
    "term_routing_instance_protocol"             : "l2vpn",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "__IQNORE__"
    }
    
    profile_mx_elan_evpl_hairpin_physical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_no",
    "term_physical_interface_tagging"            : "untagged",
    "term_physical_interface_encapsulation"      : "ethernet-vpls",
    "term_logical_unit_0_family"                 : "vpls",
    "term_logical_unit_encapsulation"            : "__IQNORE__",
    "term_routing_instance_type"                 : "vpls",
    "term_routing_instance_protocol"             : "none",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "elan,evpl"
    }

    profile_mx_elan_evpl_hairpin_logical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_yes",
    "term_physical_interface_tagging"            : "tagged",
    "term_physical_interface_encapsulation"      : "flexible-ethernet-services,vlan-vpls",
    "term_logical_unit_0_family"                 : "__IQNORE__",
    "term_logical_unit_encapsulation"            : "vlan-vpls",
    "term_routing_instance_type"                 : "vpls",
    "term_routing_instance_protocol"             : "none",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "1",
    "term_netcracker_circuit_type"               : "elan,evpl"
    }

    profile_mx_eline_hairpin_physical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_no",
    "term_physical_interface_tagging"            : "untagged",
    "term_physical_interface_encapsulation"      : "ethernet-vpls",
    "term_logical_unit_0_family"                 : "vpls",
    "term_logical_unit_encapsulation"            : "__IQNORE__",
    "term_routing_instance_type"                 : "vpls",
    "term_routing_instance_protocol"             : "none",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "2",
    "term_netcracker_circuit_type"               : "eline"
    }

    profile_mx_eline_hairpin_logical = {
    "term_circuit_name"                          : "ethernet",
    "term_interface_name_period"                 : "period_yes",
    "term_physical_interface_tagging"            : "tagged",
    "term_physical_interface_encapsulation"      : "flexible-ethernet-services,vlan-vpls",
    "term_logical_unit_0_family"                 : "__IQNORE__",
    "term_logical_unit_encapsulation"            : "vlan-vpls",
    "term_routing_instance_type"                 : "vpls",
    "term_routing_instance_protocol"             : "none",
    "term_bgp_neighbor"                          : "__IQNORE__",
    "term_interface_count"                       : "2",
    "term_netcracker_circuit_type"               : "eline"
    }


    def match_circuit_signature(self, circuit_name):
    
        debug = _Debug()
        console_message = "Circuit Signature Matcher"
        debug.console_message(2, console_message, "circuit_signature_matcher()")

        # check signature profile        
        result = self._is_signature_mx_vpls_logical(circuit_name)
        if result == "Match":
            return "mx_vpls_logical"

        # check signature profile        
        result = self._is_signature_mx_static_logical(circuit_name)
        if result == "Match":
            return "mx_static_logical"    

        # check signature profile        
        result = self._is_signature_mx_bgp_logical(circuit_name)
        if result == "Match":
            return "mx_bgp_logical"    

        # check signature profile        
        result = self._is_signature_mx_eline_hairpin(circuit_name,)
        if result == "Match":
            return "mx_eline_hairpin"

        # check signature profile        
        result = self._is_signature_mx_elan_evpl_hairpin_logical(circuit_name)
        if result == "Match":
            return "mx_elan_evpl_hairpin_logical"

        # check signature profile        
        result = self._is_signature_mx_l2vpn_logical(circuit_name)
        if result == "Match":
            return "mx_l2vpn_logical"

        # check signature profile        
        #result = self._is_signature_mx_bgp_irb_vpls_logical(circuit_name)
        #if result == "Match":
        #    return "mx_bgp_irb_vpls_logical"

        # check signature profile        
        result = self._is_signature_mx_vpls_physical(circuit_name)
        if result == "Match":
            return "mx_vpls_physical"

        # check signature profile        
        result = self._is_signature_mx_static_physical(circuit_name)
        if result == "Match":
            return "mx_static_physical"    

        # check signature profile        
        result = self._is_signature_mx_bgp_physical(circuit_name)
        if result == "Match":
            return "mx_bgp_physical"    

        # check signature profile        
        result = self._is_signature_mx_elan_evpl_hairpin_physical(circuit_name)
        if result == "Match":
            return "mx_elan_evpl_hairpin_physical"

        # check signature profile        
        result = self._is_signature_mx_l2vpn_physical(circuit_name)
        if result == "Match":
            return "mx_l2vpn_physical"

        # check signature profile        
        #result = self._is_signature_mx_bgp_irb_vpls_physical(circuit_name)
        #if result == "Match":
        #    return "mx_bgp_irb_vpls_physical"

        # no match
        console_message = "Circuit did not map to a signature profile"
        debug.console_message(2, console_message, "circuit_signature_matcher()")
        
        # update circuit table with no match
        console_message = "Saving circuit type \"No Match\" to circuit table"
        debug.console_message(2, console_message, "_circuit_signature_matcher()")
        circuit_table = _CircuitTable()
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","No Match")
        
        return "No Match"

    def _is_signature_mx_bgp_physical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_bgp_physical\""
        debug.console_message(4, console_message, "_is_signature_mx_bgp_physical()")

        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]

        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_bgp_physical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_bgp_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_bgp_physical()")
        
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_bgp_physical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_bgp_physical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_bgp_physical")

            return "Match"        
        
        # no match
        console_message = "No Match for \"mx_bgp_physical\""
        debug.console_message(6, console_message, "_is_signature_mx_bgp_physical()")
        return "No Match"

    def _is_signature_mx_bgp_logical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_bgp_logical\""
        debug.console_message(4, console_message, "_is_signature_mx_bgp_logical()")

        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]

        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_bgp_logical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_bgp_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_bgp_logical()")
        
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_bgp_logical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_bgp_logical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_bgp_logical")

            return "Match"        
        
        # no match
        console_message = "No Match for \"mx_bgp_logical\""
        debug.console_message(6, console_message, "_is_signature_mx_bgp_logical()")
        return "No Match"

    def _is_signature_mx_bgp_irb_vpls_physical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_bgp_irb_vpls_physical\""
        debug.console_message(4, console_message, "_is_signature_mx_bgp_irb_vpls_physical()")

        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]

        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_bgp_irb_vpls_physical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_bgp_irb_vpls_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_bgp_irb_vpls_physical()")
        
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_bgp_irb_vpls_physical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_bgp_irb_vpls_physical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_bgp_irb_vpls_physical")

            return "Match"        
        
        # no match
        console_message = "No Match for \"mx_bgp_irb_vpls_physical\""
        debug.console_message(6, console_message, "_is_signature_mx_bgp_irb_vpls_physical()")
        return "No Match"

    def _is_signature_mx_bgp_irb_vpls_logical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_bgp_irb_vpls_logical\""
        debug.console_message(4, console_message, "_is_signature_mx_bgp_irb_vpls_logical()")

        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]

        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_bgp_irb_vpls_logical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_bgp_irb_vpls_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_bgp_irb_vpls_logical()")
        
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_bgp_irb_vpls_logical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_bgp_irb_vpls_logical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_bgp_irb_vpls_logical")

            return "Match"        
        
        # no match
        console_message = "No Match for \"mx_bgp_irb_vpls_logical\""
        debug.console_message(6, console_message, "_is_signature_mx_bgp_irb_vpls_logical()")
        return "No Match"

    def _is_signature_mx_static_physical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_static_physical\""
        debug.console_message(4, console_message, "_is_signature_mx_static_physical()")

        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]

        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_static_physical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_static_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_static_physical()")
        
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_static_physical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_static_physical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_static_physical")

            return "Match"        
        
        # no match
        console_message = "No Match for \"mx_static_physical\""
        debug.console_message(6, console_message, "_is_signature_mx_static_physical()")
        return "No Match"

    def _is_signature_mx_static_logical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_static_logical\""
        debug.console_message(4, console_message, "_is_signature_mx_static_logical()")

        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]

        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_static_logical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_static_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_static_logical()")
        
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_static_logical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_static_logical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_static_logical")

            return "Match"        
        
        # no match
        console_message = "No Match for \"mx_static_logical\""
        debug.console_message(6, console_message, "_is_signature_mx_static_logical()")
        return "No Match"

    def _is_signature_mx_vpls_physical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_vpls_physical\""
        debug.console_message(4, console_message, "_is_signature_mx_vpls_physical()")
        
        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_vpls_physical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_vpls_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_vpls_physical()")
            
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_vpls_physical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_vpls_physical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_vpls_physical")
            return "Match"        

        # no match
        if result == "No Match":
            console_message = "No Match for \"mx_vpls_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_vpls_physical()")
            return "No Match"

    def _is_signature_mx_vpls_logical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_vpls_logical\""
        debug.console_message(4, console_message, "_is_signature_mx_vpls_logical()")
        
        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_vpls_logical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_vpls_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_vpls_logical()")
            
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_vpls_logical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_vpls_logical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_vpls_logical")
            return "Match"        

        # no match
        if result == "No Match":
            console_message = "No Match for \"mx_vpls_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_vpls_logical()")
            return "No Match"


    def _is_signature_mx_l2vpn_physical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_l2vpn_physical\""
        debug.console_message(4, console_message, "_is_signature_mx_l2vpn_physical()")
        
        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_l2vpn_physical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_l2vpn_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_l2vpn_physical()")
            
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_l2vpn_physical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_l2vpn_physical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_l2vpn_physical")
            return "Match"        

        # no match
        if result == "No Match":
            console_message = "No Match for \"mx_l2vpn_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_l2vpn_physical()")
            return "No Match"
    def _is_signature_mx_l2vpn_logical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_l2vpn_logical\""
        debug.console_message(4, console_message, "_is_signature_mx_l2vpn_logical()")
        
        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_l2vpn_logical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_l2vpn_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_l2vpn_logical()")
            
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_l2vpn_logical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_l2vpn_logical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_l2vpn_logical")
            return "Match"        

        # no match
        if result == "No Match":
            console_message = "No Match for \"mx_l2vpn_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_l2vpn_logical()")
            return "No Match"

    def _is_signature_mx_elan_evpl_hairpin_physical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_elan_evpl_hairpin_physical\""
        debug.console_message(4, console_message, "_is_signature_mx_elan_evpl_hairpin_physical()")
        
        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_elan_evpl_hairpin_physical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_elan_evpl_hairpin_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_elan_evpl_hairpin_physical()")
            
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_elan_evpl_hairpin_physical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_elan_evpl_hairpin_physical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_elan_evpl_hairpin_physical")
            return "Match"        

        # no match
        if result == "No Match":
            console_message = "No Match for \"mx_elan_evpl_hairpin_physical\""
            debug.console_message(6, console_message, "_is_signature_mx_elan_evpl_hairpin_physical()")
            return "No Match"

    def _is_signature_mx_elan_evpl_hairpin_logical(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_elan_evpl_hairpin_logical\""
        debug.console_message(4, console_message, "_is_signature_mx_elan_evpl_hairpin_logical()")
        
        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # run match checker
        result = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_elan_evpl_hairpin_logical, interface1)
        
        # match
        if result == "Match":
            console_message = "Match for \"mx_elan_evpl_hairpin_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_elan_evpl_hairpin_logical()")
            
            # save circuit type to circuit table
            circuit_table = _CircuitTable()
            console_message = "Saving circuit type \"mx_elan_evpl_hairpin_logical\" to circuit table"
            debug.console_message(6, console_message, "_is_signature_mx_elan_evpl_hairpin_logical()")
            circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_elan_evpl_hairpin_logical")
            return "Match"        

        # no match
        if result == "No Match":
            console_message = "No Match for \"mx_elan_evpl_hairpin_logical\""
            debug.console_message(6, console_message, "_is_signature_mx_elan_evpl_hairpin_logical()")
            return "No Match"

    def _is_signature_mx_eline_hairpin(self, circuit_name):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_eline_hairpin\""
        debug.console_message(4, console_message, "_is_signature_mx_eline_hairpin()")
        
        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        
        # no match if interface count is not 2
        if len(interface_list) != 2:
            console_message = "No Match - Interface count needs to equal 2"
            debug.console_message(4, console_message, "_is_signature_mx_eline_hairpin()")
            return "No Match"

        # init variables
        interface1 = interface_list[0]
        interface2 = interface_list[1]
        int1_routing_instance = ""
        int2_routing_instance = ""

        # check signature against interface 1 physical
        int1_phy, int1_routing_instance = self._is_signature_mx_eline_hairpin_check_int_phy(circuit_name, interface1, "1")
        
        # if no match on physical check logical
        if int1_phy == "No Match":
            int1_log, int1_routing_instance = self._is_signature_mx_eline_hairpin_check_int_log(circuit_name, interface1, "1")
            
            # no match on physical or logical
            if int1_log == "No Match":
                console_message = "Interface 1 was not a match for \"mx_eline_hairpin_physical\" or \"mx_eline_hairpin_logical\""
                debug.console_message(4, console_message, "_is_signature_mx_eline_hairpin()")
                return "No Match"
        
        # check signature against interface 2 physical
        int2_phy, int2_routing_instance = self._is_signature_mx_eline_hairpin_check_int_phy(circuit_name, interface2, "2")
        
        # if no match on physical check logical
        if int2_phy == "No Match":
            int2_log, int2_routing_instance = self._is_signature_mx_eline_hairpin_check_int_log(circuit_name, interface2, "2")
            
            # no match on physical or logical
            if int2_log == "No Match":
                console_message = "Interface 2 was not a match for \"mx_eline_hairpin_physical\" or \"mx_eline_hairpin_logical\""
                debug.console_message(4, console_message, "_is_signature_mx_eline_hairpin()")
                return "No Match"       

        # routing instance check
        if int1_routing_instance != int2_routing_instance:
            console_message = "No Match - Interfaces are not in the same routing instance"
            debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin()")
            return "No Match"                    

        if int1_routing_instance == int2_routing_instance:
            console_message = "Match - Interfaces are part of the same routing instance"
            debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin()")

        # match
        console_message = "Match for \"mx_eline_hairpin\""
        debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin()")
    
        # save circuit type to circuit table
        circuit_table = _CircuitTable()
        console_message = "Saving circuit type \"mx_eline_hairpin\" to circuit table"
        debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin()")
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"service_type","mx_eline_hairpin")
        return "Match"

    def _is_signature_mx_eline_hairpin_check_int_phy(self, circuit_name, interface_name, interface_number):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_eline_hairpin_physical\" against interface {}".format(interface_number)
        debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin_check_int_phy()")
        int_phy = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_eline_hairpin_physical, interface_name)        

        if int_phy == "Match":
            console_message = "Interface {} is match for \"mx_eline_hairpin_physical\"".format(interface_number)
            debug.console_message(6, console_message, "__is_signature_mx_eline_hairpin_check_int_phy()")

            int_routing_instance = _MXSignatureMatcher.routing_instance_name
            console_message = "Interface {} is part of routing instance \"{}\"".format(interface_number, int_routing_instance)
            debug.console_message(6, console_message, "__is_signature_mx_eline_hairpin_check_int_phy()")
            return "Match", int_routing_instance

        if int_phy == "No Match":
            console_message = "Interface {} is not a match for \"mx_eline_hairpin_physical\"".format(interface_number)
            debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin_check_int_phy()")
            return "No Match", "No Match"

    def _is_signature_mx_eline_hairpin_check_int_log(self, circuit_name, interface_name, interface_number):
        
        debug = _Debug()
        console_message = "Checking signature profile \"mx_eline_hairpin_logical\" against interface {}".format(interface_number)
        debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin_check_int_log()")
        int_log = self._check_terms(circuit_name, _MXSignatureMatcher.profile_mx_eline_hairpin_logical, interface_name)

        if int_log == "Match":
            console_message = "Interface {} is match for \"mx_eline_hairpin_logical\"".format(interface_number)
            debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin_check_int_log")

            int_routing_instance = _MXSignatureMatcher.routing_instance_name
            console_message = "Interface {} is part of routing instance \"{}\"".format(interface_number, int_routing_instance)
            debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin_check_int_log")
            return "Match", int_routing_instance

        if int_log == "No Match":
            console_message = "Interface {} is not a match for \"mx_eline_hairpin_logical\"".format(interface_number)
            debug.console_message(6, console_message, "_is_signature_mx_eline_hairpin_check_int_log")
            return "No Match", "No Match"



    def _check_terms(self, circuit_name, signature_profile, interface):

        # if physical interface then create logical interface name
        if "." not in interface:
            physical_interface = interface
            logical_interface  = interface + ".0"
 
        # if logical interface then create physical interface name
        if "." in interface:
            logical_interface  = interface
            split = interface.split(".")
            physical_interface = split[0]
        
        # check term
        result = self._check_term_circuit_name(circuit_name, signature_profile)
        if result == "No Match":
            return "No Match"        

        # check term
        result = self._check_term_interface_name_period(signature_profile, interface)
        if result == "No Match":
            return "No Match"        

        # check term
        result = self._check_term_physical_interface_tagging(signature_profile, physical_interface)
        if result == "No Match":
            return "No Match"
        
        # check term   
        result = self._check_term_physical_interface_encapsulation(signature_profile, physical_interface)
        if result == "No Match":
            return "No Match"

        # check term   
        result = self._check_term_logical_unit_0_family(signature_profile, logical_interface)
        if result == "No Match":
            return "No Match"

        # check term   
        result = self._check_term_logical_unit_encapsulation(signature_profile, logical_interface)
        if result == "No Match":
            return "No Match"

        # check term   
        result = self._check_term_routing_instance_type(signature_profile, logical_interface)
        if result == "No Match":
            return "No Match"

        # check term   
        result = self._check_term_routing_instance_protocol(signature_profile, logical_interface)
        if result == "No Match":
            return "No Match"

        # check term   
        result = self._check_term_bgp_neighbor(signature_profile, logical_interface)
        if result == "No Match":
            return "No Match"
        
        # check term   
        result = self._check_term_interface_count(signature_profile, circuit_name)
        if result == "No Match":
            return "No Match"

        # check term   
        result = self._check_term_netcracker_circuit_type(signature_profile, circuit_name)
        if result == "No Match":
            return "No Match"
        
        # all terms have matched
        return "Match"
        
    def _check_term_circuit_name(self, circuit_name, signature_profile):

        debug = _Debug()
        console_message = "Checking term \"term_circuit_name\""
        debug.console_message(6, console_message, "_check_term_circuit_name()")

        # term input is iqnore
        if signature_profile['term_circuit_name'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_circuit_name'])
            debug.console_message(8, console_message, "_check_term_circuit_name()")
            return "__IQNORE__"

        # term input is ethernet
        if signature_profile['term_circuit_name'] == "ethernet":
            console_message = "Term input is \"{}\"".format(signature_profile['term_circuit_name'])
            debug.console_message(8, console_message, "_check_term_circuit_name()")
            
            if "enet" not in circuit_name.lower() and "et" not in circuit_name.lower():
                console_message = "No Match"
                debug.console_message(8, console_message, "_check_term_circuit_name()")
                return "No Match"
           
            if "enet" in circuit_name.lower():
                console_message = "Match - Found \"enet\" in circuit name"
                debug.console_message(8, console_message, "_check_term_circuit_name()")
                return "Match"
            
            if "et" in circuit_name.lower() and "inet".lower() not in circuit_name:
                console_message = "Match - Found \"et\" in circuit name"
                debug.console_message(8, console_message, "_check_term_circuit_name()")           
                return "Match"

        # term input is internet
        if signature_profile['term_circuit_name'] == "internet":
            console_message = "Term input is \"{}\"".format(signature_profile['term_circuit_name'])
            debug.console_message(8, console_message, "_check_term_circuit_name()")

            if "inet" in circuit_name.lower():
                console_message = "Match - Found \"inet\" in circuit name"
                debug.console_message(8, console_message, "_check_term_circuit_name()")
                return "Match"
            
            if "ip" in circuit_name.lower():
                console_message = "Match - Found \"ip\" in circuit name"
                debug.console_message(8, console_message, "_check_term_circuit_name()")    
                return "Match"
                
        # no match
        console_message = "No Match - Input term is not ethernet or internet"
        debug.console_message(8, console_message, "_check_term_circuit_name()")    
        return "No Match"
    
    def _check_term_interface_name_period(self, signature_profile, interface):

        debug = _Debug()
        console_message = "Checking term \"term_interface_name_period\""
        debug.console_message(6, console_message, "_check_term_interface_name_period()")
        
        # term input is iqnore
        if signature_profile['term_interface_name_period'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_interface_name_period'])
            debug.console_message(8, console_message, "_check_term_interface_name_period()")
            return "__IQNORE__"

        # term input is period_yes
        if signature_profile['term_interface_name_period'] == "period_yes":
            console_message = "Term input is \"{}\"".format(signature_profile['term_interface_name_period'])
            debug.console_message(8, console_message, "_check_term_interface_name_period()")
            
            if "." in interface:
                console_message = "Match - Period found in interface name"
                debug.console_message(8, console_message, "_check_term_interface_name_period()")
                return "Match"
            
            if "." not in interface:
                console_message = "No Match - Period not found in interface name"
                debug.console_message(8, console_message, "_check_term_interface_name_period()")
                return "No Match"

        # term input is period_no
        if signature_profile['term_interface_name_period'] == "period_no":
            console_message = "Term input is \"{}\"".format(signature_profile['term_interface_name_period'])
            debug.console_message(8, console_message, "_check_term_interface_name_period()")
            
            if "." in interface:
                console_message = "No Match - Period found in interface name"
                debug.console_message(8, console_message, "_check_term_interface_name_period()")
                return "No Match"
            
            if "." not in interface:
                console_message = "Match - Period not found in interface name"
                debug.console_message(8, console_message, "_check_term_interface_name_period()")
                return "Match"
    
    def _check_term_physical_interface_tagging(self, signature_profile, interface):
        
        interface_mapper = _MXInterfaceMapper()
        
        debug = _Debug()
        console_message = "Checking term \"term_physical_interface_tagging\""
        debug.console_message(6, console_message, "_check_term_physical_interface_tagging()")
        
        # term input is iqnore
        if signature_profile['term_physical_interface_tagging'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_physical_interface_tagging'])
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")
            return "__IQNORE__"

        # check for vlan-tagging
        vlan_tagging = interface_mapper.interface_polls[interface]['vlan-tagging']
        if vlan_tagging == "Not Configured":
            console_message = "vlan-tagging is not configured"
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")

        if vlan_tagging == True:
            console_message = "vlan-tagging is configured"
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")

        # check for flexible-vlan-tagging
        flexible_vlan_tagging = interface_mapper.interface_polls[interface]['flexible-vlan-tagging']
        if flexible_vlan_tagging == "Not Configured":
            console_message = "flexible-vlan-tagging is not configured"
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")

        if flexible_vlan_tagging == True:
            console_message = "flexible-vlan-tagging is configured"
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")
    
        # term input is tagged
        if signature_profile['term_physical_interface_tagging'] == "tagged":
            console_message = "Term input is \"{}\"".format(signature_profile['term_physical_interface_tagging'])
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")

            if vlan_tagging == True or flexible_vlan_tagging == True:
                console_message = "Match - Interface configured as tagging"
                debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")
                return "Match"
            
            console_message = "No Match"
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")
            return "No Match"
            
        # term input is untagged
        if signature_profile['term_physical_interface_tagging'] == "untagged":
            console_message = "Term input is \"{}\"".format(signature_profile['term_physical_interface_tagging'])
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging")

            if vlan_tagging == "Not Configured" and flexible_vlan_tagging == "Not Configured":
                console_message = "Match - Interface configured as untagged"
                debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")
                return "Match"

            console_message = "No Match"
            debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")
            return "No Match"
            
        # no match
        console_message = "No Match - Term input is not tagged or untagged"
        debug.console_message(8, console_message, "_check_term_physical_interface_tagging()")
        return "No Match"
    
    def _check_term_physical_interface_encapsulation(self, signature_profile, interface):
        
        interface_mapper = _MXInterfaceMapper()
        
        debug = _Debug()
        console_message = "Checking term \"term_physical_interface_encapsulation\""
        debug.console_message(6, console_message, "_check_term_physical_interface_encapsulation()")
        
        # term input is iqnore
        if signature_profile['term_physical_interface_encapsulation'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_physical_interface_encapsulation'])
            debug.console_message(8, console_message, "_check_term_physical_interface_encapsulation()")
            return "__IQNORE__"

        # term input is none
        if signature_profile['term_physical_interface_encapsulation'] == "none":
            console_message = "Term input is \"{}\"".format(signature_profile['term_physical_interface_encapsulation'])
            debug.console_message(8, console_message, "_check_term_physical_interface_encapsulation()")
 
            if interface_mapper.interface_polls[interface]['encapsulation'] == "Not Configured":
                console_message = "Match - Physical interface encapsulation is not configured"
                debug.console_message(8, console_message, "_check_term_physical_interface_encapsulation()")
                return "Match"
 
            if interface_mapper.interface_polls[interface]['encapsulation'] != "Not Configured":
                console_message = "Not Match - Physical interface encapsulation is configured"
                debug.console_message(8, console_message, "_check_term_physical_interface_encapsulation()")
                return "No Match"
 
        # term input is value
        if signature_profile['term_physical_interface_encapsulation'] != "none":
            console_message = "Term input is \"{}\"".format(signature_profile['term_physical_interface_encapsulation'])
            debug.console_message(8, console_message, "_check_term_physical_interface_encapsulation()")
 
            # break out input capsulation types
            split = signature_profile['term_physical_interface_encapsulation'].split(",")
            
            # loop through input encapsulation types 
            for encap in split:
                if interface_mapper.interface_polls[interface]['encapsulation'] == encap:
                    console_message = "Match - Physical interface encapsulation is configured as {}".format(encap)
                    debug.console_message(8, console_message, "_check_term_physical_interface_encapsulation()")
                    return "Match"
        
            # no match
            console_message = "No Match - Physical interface encapsulation is not configured as {}".format(signature_profile['term_physical_interface_encapsulation'])
            debug.console_message(8, console_message, "_check_term_physical_interface_encapsulation()")
            return "No Match"
 
    def _check_term_logical_unit_0_family(self, signature_profile, interface):
        
        interface_mapper = _MXInterfaceMapper()
        
        debug = _Debug()
        console_message = "Checking term \"term_logical_unit_0_family\""
        debug.console_message(6, console_message, "term_logical_unit_0_family()")
        
        # term input is iqnore
        if signature_profile['term_logical_unit_0_family'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_logical_unit_0_family'])
            debug.console_message(8, console_message, "_check_term_logical_unit_0_family()")
            return "__IQNORE__"

        console_message = "Term input is \"{}\"".format(signature_profile['term_logical_unit_0_family'])
        debug.console_message(8, console_message, "_check_term_logical_unit_0_family()")

        # not configured
        if interface_mapper.interface_polls[interface]['family'] == "Not Configured":
            console_message = "No Match - Unit 0 family is not configured"
            debug.console_message(8, console_message, "_check_term_logical_unit_0_family()")
            return "No Match"

        # match
        if interface_mapper.interface_polls[interface]['family'] == signature_profile['term_logical_unit_0_family']:
            console_message = "Match - Unit 0 family is set to \"{}\"".format(signature_profile['term_logical_unit_0_family'])
            debug.console_message(8, console_message, "_check_term_logical_unit_0_family()")
            return "Match"

        # no match
        if interface_mapper.interface_polls[interface]['family'] != signature_profile['term_logical_unit_0_family']:
            console_message = "No Match - Unit 0 family is set to \"{}\"".format(interface_mapper.interface_polls[interface]['family'])
            debug.console_message(8, console_message, "_check_term_logical_unit_0_family()")
            return "No Match"

    def _check_term_logical_unit_encapsulation(self, signature_profile, interface):
        
        interface_mapper = _MXInterfaceMapper()
        
        debug = _Debug()
        console_message = "Checking term \"term_logical_unit_encapsulation\""
        debug.console_message(6, console_message, "_check_term_logical_unit_encapsulation()")
        
        # term input is iqnore
        if signature_profile['term_logical_unit_encapsulation'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_logical_unit_encapsulation'])
            debug.console_message(8, console_message, "_check_term_logical_unit_encapsulation()")
            return "__IQNORE__"

        # term input is none
        if signature_profile['term_logical_unit_encapsulation'] == "none":
            console_message = "Term input is \"{}\"".format(signature_profile['term_logical_unit_encapsulation'])
            debug.console_message(8, console_message, "_check_term_logical_unit_encapsulation()")
 
            if interface_mapper.interface_polls[interface]['encapsulation'] == "Not Configured":
                console_message = "Match - Logical unit escapulsation is not configured"
                debug.console_message(8, console_message, "_check_term_logical_unit_encapsulation()")
                return "Match"
            
            if interface_mapper.interface_polls[interface]['encapsulation'] != "Not Configured":
                console_message = "No Match - Logical unit escapulsation is configured as {}".format(interface_mapper.interface_polls[interface]['encapsulation'] )
                debug.console_message(8, console_message, "_check_term_logical_unit_encapsulation()")
                return "No Match"
 
        # term input is value
        if signature_profile['term_logical_unit_encapsulation'] != "none":
            console_message = "Term input is \"{}\"".format(signature_profile['term_logical_unit_encapsulation'])
            debug.console_message(8, console_message, "_check_term_logical_unit_encapsulation()")
 
            if interface_mapper.interface_polls[interface]['encapsulation'] == signature_profile['term_logical_unit_encapsulation']:
                console_message = "Match - Logical unit encaspulation configured as {}".format(signature_profile['term_logical_unit_encapsulation'])
                debug.console_message(8, console_message, "_check_term_logical_unit_encapsulation()")
                return "Match"

            if interface_mapper.interface_polls[interface]['encapsulation'] != signature_profile['term_logical_unit_encapsulation']:
                console_message = "No Match - Logical unit encapsulation is not configured as {}".format(signature_profile['term_logical_unit_encapsulation'])
                debug.console_message(8, console_message, "_check_term_logical_unit_encapsulation")
                return "No Match"
        
    def _check_term_routing_instance_type(self, signature_profile, interface):
        
        interface_mapper = _MXInterfaceMapper()
        
        debug = _Debug()
        console_message = "Checking term \"term_routing_instance_type\""
        debug.console_message(6, console_message, "_check_term_routing_instance_type()")
        
        # term input is iqnore
        if signature_profile['term_routing_instance_type'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_routing_instance_type'])
            debug.console_message(8, console_message, "_check_term_routing_instance_type()")
            return "__IQNORE__"

        # map interface to routing instance
        routing_instance_name = self._map_routing_instance( interface )
        
        # could not map interface to routing instance
        if routing_instance_name == False:
            console_message = "No Match"
            debug.console_message(8, console_message, "_check_term_routing_instance_type()")
            return "No Match"

        # 
        console_message = "Term input is \"{}\"".format(signature_profile['term_routing_instance_type'])
        debug.console_message(8, console_message, "_check_term_routing_instance_type()")

        # if routing instance type is not configured
        mx_circuit_processer = _MXCircuitProcessor()
        if 'instance_type' not in mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]:
            console_message = "No Match - Routing instance type is not configured"
            debug.console_message(8, console_message, "_check_term_routing_instance_type()")
            return "No Match"
   
        # term input is value
        if mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]['instance_type'] == signature_profile['term_routing_instance_type']:
            console_message = "Match - Routing instanace type is set to \"{}\"".format(signature_profile['term_routing_instance_type'])
            debug.console_message(8, console_message, "_check_term_routing_instance_type()")
            return "Match"
        
        if mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]['instance_type'] != signature_profile['term_routing_instance_type']:
            console_message = "No Match - Routing instance type is not configured as {}".format(signature_profile['term_routing_instance_type'])
            debug.console_message(8, console_message, "_check_term_routing_instance_type")
            return "No Match"
        
    def _check_term_routing_instance_protocol(self, signature_profile, interface):
        
        interface_mapper = _MXInterfaceMapper()
        
        debug = _Debug()
        console_message = "Checking term \"term_routing_instance_protocol\""
        debug.console_message(6, console_message, "_check_term_routing_instance_protocol()")
        
        # term input is iqnore
        if signature_profile['term_routing_instance_protocol'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_routing_instance_protocol'])
            debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
            return "__IQNORE__"

        # map interface to routing instance
        routing_instance_name = self._map_routing_instance( interface )
        
        # if no routing instances are configured on router
        if routing_instance_name == False:
            console_message = "No Match - No routing instances configured on router"
            debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
            return "No Match"
        
        mx_circuit_processer = _MXCircuitProcessor()
        console_message = "Term input is \"{}\"".format(signature_profile['term_routing_instance_protocol'])
        debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
   
        # term input is none
        if signature_profile['term_routing_instance_protocol'] == "none":

            if 'protocol' not in mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]:
                console_message = "Match - Routing instance protocol is not configured"
                debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
                return "Match"

            if 'protocol' in mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]:
                console_message = "No Match - Routing instance protocol is configured as \"{}\"".format(mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]['protocol'])
                debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
                return "No Match"
            
        # term input is value
        if signature_profile['term_routing_instance_protocol'] != "none":
 
            if 'protocol' not in mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]:
                console_message = "No Match - Routing instance protocol is not configured"
                debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
                return "No Match"

            if mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]['protocol'] != signature_profile['term_routing_instance_protocol']:
                console_message = "Match - Routing instanace protocol is set to \"{}\"".format(mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]['protocol'])
                debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
                return "No Match"

            if mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]['protocol'] == signature_profile['term_routing_instance_protocol']:
                console_message = "Match - Routing instanace protocol is set to \"{}\"".format(mx_circuit_processer.parsed_configuration[0][0]['vrf'][routing_instance_name]['protocol'])
                debug.console_message(8, console_message, "_check_term_routing_instance_protocol()")
                return "Match"

    def _check_term_bgp_neighbor(self, signature_profile, interface):
        
        interface_mapper = _MXInterfaceMapper()
        mx_circuit_processer = _MXCircuitProcessor()
        
        debug = _Debug()
        console_message = "Checking term \"term_bgp_neighbor\""
        debug.console_message(6, console_message, "_check_term_routing_instance_protocol()")
       
        # term input is iqnore
        if signature_profile['term_bgp_neighbor'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_bgp_neighbor'])
            debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")
            return "__IQNORE__"
        
        console_message = "Term input is \"{}\"".format(signature_profile['term_bgp_neighbor'])
        debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")

        # get interface ip information
        interface_ip = interface_mapper.interface_polls[interface]['ip']
        interface_mask = interface_mapper.interface_polls[interface]['mask']
        interface_ip_address = interface_ip + "/" + interface_mask
        
        # no bgp configuration
        if 'bgp' not in mx_circuit_processer.parsed_configuration[0][0]:
            console_message = "No Match - No BGP neighbors configured on router"
            debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")
            return "No Match"

        # term input is none
        if signature_profile['term_bgp_neighbor'] == "none":

            # loop through all bgp neighbors
            for neighbor in mx_circuit_processer.parsed_configuration[0][0]['bgp']['neighbors']:
    
                # get neighbor ip information
                neighbor_ip = neighbor
                neighbor_mask = interface_mask
                neighbor_ip_address = neighbor_ip + "/" + neighbor_mask

                # formailze interface and neighbor ip's
                a = ip_network(interface_ip_address, strict = False).network_address 
                b = ip_network(neighbor_ip_address, strict = False).network_address
    
                # if a bgp neighbor is found then return no match
                if a == b:
                    console_message = "No Match - Found BGP neighbor {}".format(neighbor_ip)
                    debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")
                    return "No Match"
            
            # if no bgp neighbor is found then match
            console_message = "Match - Did not find a BGP neighbor"
            debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")
            return "Match"

        # term input is check
        if signature_profile['term_bgp_neighbor'] == "check":

            # loop through all bgp neighbors
            for neighbor in mx_circuit_processer.parsed_configuration[0][0]['bgp']['neighbors']:
    
                # get neighbor ip information
                neighbor_ip = neighbor
                neighbor_mask = interface_mask
                neighbor_ip_address = neighbor_ip + "/" + neighbor_mask

                # formailze interface and neighbor ip's
                a = ip_network(interface_ip_address, strict = False).network_address 
                b = ip_network(neighbor_ip_address, strict = False).network_address
                
                # if a bgp neighbor is found then return match
                if a == b:
                    console_message = "Match - Found BGP neighbor {}".format(neighbor_ip)
                    debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")
                    
                    # store neighbor IP for use by poller
                    _MXSignatureMatcher.bgp_neighbor_ip = neighbor_ip
                    
                    return "Match"
                    
            # if no bgp neighbor is found then no match
            console_message = "No Match - Did not find a BGP neighbor"
            debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")
            return "No Match"

        # no match
        console_message = "No Match - Term input is not none or check"
        debug.console_message(8, console_message, "_check_term_term_bgp_neighbor()")
        return "No Match"

    def _check_term_interface_count(self, signature_profile, circuit_name):

        debug = _Debug()
        console_message = "Checking term \"term_interface_count\""
        debug.console_message(6, console_message, "_check_term_interface_count()")
        
        # term input is iqnore
        if signature_profile['term_interface_count'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_interface_count'])
            debug.console_message(8, console_message, "_check_term_interface_count()")
            return "__IQNORE__"
        
        console_message = "Term input is \"{}\"".format(signature_profile['term_interface_count'])
        debug.console_message(8, console_message, "_check_term_interface_count()")
        
        # get interface list
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])

        # match
        if len(interface_list) == int(signature_profile['term_interface_count']):
            console_message = "Match - Interface count is \"{}\"".format(signature_profile['term_interface_count'])
            debug.console_message(8, console_message, "_check_term_interface_count()")
            return "Match"
        
        # no match
        if len(interface_list) != int(signature_profile['term_interface_count']):
            console_message = "No Match - Interface count is \"{}\"".format(len(interface_list))
            debug.console_message(8, console_message, "_check_term_interface_count()")
            return "No Match"

    def _check_term_netcracker_circuit_type(self, signature_profile, circuit_name):

        debug = _Debug()
        console_message = "Checking term \"term_netcracker_circuit_type\""
        debug.console_message(6, console_message, "_check_term_interface_count()")
        
        # term input is iqnore
        if signature_profile['term_netcracker_circuit_type'] == "__IQNORE__":
            console_message = "Term input is \"{}\"".format(signature_profile['term_netcracker_circuit_type'])
            debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")
            return "__IQNORE__"
        
        console_message = "Term input is \"{}\"".format(signature_profile['term_netcracker_circuit_type'])
        debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")

        console_message = "Sending query to NSS gRPC Microserices at : {}".format(CircuitCheck.grpc_server)
        debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")

        # open connection to nss grpc microservices
        nss_grpc_channel = grpc.insecure_channel(CircuitCheck.grpc_server)
        nss_grpc_stub = CircuitServiceStub(nss_grpc_channel)

        try:
            response = nss_grpc_stub.GetCircuit(
                GetCircuitRequest(circuit_id="{}".format(circuit_name))
            )
        except Exception as e:

            console_message = "Received following error from NSS gRPC Microserices : "
            debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")
            debug.console_blank_line()

            console_message = "{}".format(e)
            debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")
            debug.console_blank_line()

            console_message = "No Match - Netcracker circuit type could not be determined for \"{}\"".format(signature_profile['term_netcracker_circuit_type'])
            debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")
            return "No Match"

        # convert response to lower case string
        response_str = str(response).lower()
        
        # break out input values types
        split = signature_profile['term_netcracker_circuit_type'].split(",")
        
        # loop through input values 
        for value in split:
                if value in response_str:
                    console_message = "Match - Netcracker circuit type matches \"{}\"".format(value)
                    debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")
                    return "Match"
        
        console_message = "No Match - Netcracker circuit type does not match \"{}\"".format(signature_profile['term_netcracker_circuit_type'])
        debug.console_message(8, console_message, "_check_term_netcracker_circuit_type()")
        return "No Match"

    def _map_routing_instance(self, interface_name):

        mx_circuit_processer = _MXCircuitProcessor()

        debug = _Debug()
        console_message = "Routing Instance Mapper"
        debug.console_message(8, console_message, "_map_routing_instance()")

        # if there are no routing instances then return
        if 'vrf' not in mx_circuit_processer.parsed_configuration[0][0]:
            console_message = "No routing instances configured on router"
            debug.console_message(10, console_message, "_map_routing_instance()")
            return False
      
        # loop through routing instances on router
        for vrf in mx_circuit_processer.parsed_configuration[0][0]['vrf']:
            
            # if routing instance has no interfaces then continue to next
            if 'interfaces' not in mx_circuit_processer.parsed_configuration[0][0]['vrf'][vrf]:
                continue
            
            # loop through interface in routing instance
            for interface in mx_circuit_processer.parsed_configuration[0][0]['vrf'][vrf]['interfaces']:
                
                # if interface is found in routing instance return routing instance name
                if interface == interface_name:
                    
                    console_message = "Interface \"{}\" is part of routing instance \"{}\"".format(interface_name, vrf)
                    debug.console_message(10, console_message, "_map_routing_instance()")
                    
                    # save routing instance name for poller
                    _MXSignatureMatcher.routing_instance_name = vrf
                    return vrf
            
        # interface was not found in a routing instance
        console_message = "Interface \"{}\" was not found in any routing instance".format(interface_name)
        debug.console_message(10, console_message, "_map_routing_instance()")
        return False

###################################### Class Block
class _MXPoller:
    
    def poll_mx_circuit(self, circuit_name, circuit_type):
    
        debug = _Debug()
        console_message = "MX Circuit Poller"
        debug.console_message(2, console_message, "poll_mx_circuit()")

        if circuit_type == "mx_bgp_physical" or circuit_type == "mx_bgp_logical":
            self._poll_mx_bgp( circuit_name)
            
        if circuit_type == "mx_static_physical" or circuit_type == "mx_static_logical":
            self._poll_mx_static( circuit_name)

        if circuit_type == "mx_vpls_physical" or circuit_type == "mx_vpls_logical":
            self._poll_mx_vpls( circuit_name)
            
        if circuit_type == "mx_l2vpn_physical" or circuit_type == "mx_l2vpn_logical":
            self._poll_mx_l2vpn( circuit_name)
            
        if circuit_type == "mx_eline_hairpin":
            self._poll_mx_eline_haprin( circuit_name)

        if circuit_type == "mx_elan_evpl_hairpin_physical" or circuit_type == "mx_elan_evpl_hairpin_logical":
            self._poll_mx_elan_evpl_haprin( circuit_name)

    def _poll_mx_bgp_irb_vpls( self, circuit_name):
        
        debug = _Debug()
        console_message = "Poll mx_bgp_irb_vpls"
        debug.console_message(4, console_message, "poll_mx_bgp_irb_vpls()")
        
        # show vpls connections
        # grab remote pe ip
        # ssh to remote ip
        # show ip bgp neighbor
        # parse result

        mx_connect = _MXConnect()
       
        # run show commands
        cmd1 = "show bgp neighbor {}".format(_MXSignatureMatcher.bgp_neighbor_ip)
        cmd1_output = mx_connect.run_command(cmd1)
        
        # merge device name, command, and output for storage in circuit table
        checker = CircuitCheck()
        cmd1_merge = checker.device_name + "> " + cmd1 + "\n" + cmd1_output
        
        # parse output
        parsed_cmd1 = mx_connect.parse_poll_data(cmd1_merge)

        # save data
        neighbor_state = parsed_cmd1[0][0]['bgp_state']['state']
       
        # console messages
        console_message = "BGP Neighbor State: {}".format(neighbor_state)
        debug.console_message(6, console_message, "poll_mx_bgp_irb_vpls")

        # save data to circuit table
        circuit_table = _CircuitTable()

        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_bgp_irb_show_neighbor_state",cmd1_merge)
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_bgp_irb_neighbor_state",neighbor_state)

    def _poll_mx_bgp( self, circuit_name):
        
        debug = _Debug()
        console_message = "Poll mx_bgp"
        debug.console_message(4, console_message, "poll_mx_bgp()")

        mx_connect = _MXConnect()
       
        # run show commands
        cmd1 = "show bgp neighbor {}".format(_MXSignatureMatcher.bgp_neighbor_ip)
        cmd1_output = mx_connect.run_command(cmd1)
        
        cmd1_output = cmd1_output.translate(cmd1_output.maketrans({"'":  r"''"}))
        
        # merge device name, command, and output for storage in circuit table
        checker = CircuitCheck()
        cmd1_merge = checker.device_name + "> " + cmd1 + "\n" + cmd1_output
        
        # parse output
        parsed_cmd1 = mx_connect.parse_poll_data(cmd1_merge)

        # save data
        neighbor_state = parsed_cmd1[0][0]['bgp_state']['state']
       
        # console messages
        console_message = "BGP Neighbor State: {}".format(neighbor_state)
        debug.console_message(6, console_message, "_poll_mx_bgp()")

        # save data to circuit table
        circuit_table = _CircuitTable()

        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_bgp_show_neighbor_state",cmd1_merge)
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_bgp_neighbor_state",neighbor_state)

    def _poll_mx_static( self, circuit_name):
        
        debug = _Debug()
        console_message = "Poll mx_static"
        debug.console_message(4, console_message, "poll_mx_static()")

        mx_connect = _MXConnect()

        # get interface list mapped to circuit
        circuit_table = _CircuitTable()
        result_json = circuit_table.get_circuit_table_auto_run_mode(circuit_name, "mx_circuit_interfaces" )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
       
        # run show commands
        cmd1 = "show arp interface {} no-resolve".format(interface1)
        cmd1_output = mx_connect.run_command(cmd1)
        
        # merge device name, command, and output for storage in circuit table
        checker = CircuitCheck()
        cmd1_merge = checker.device_name + "> " + cmd1 + "\n" + cmd1_output
        
        # parse output
        parsed_cmd1 = mx_connect.parse_poll_data(cmd1_merge)

        # save data
        arp_count = parsed_cmd1[0][0]['counters']['arp_count']
       
        # console messages
        console_message = "ARP Count: {}".format(arp_count)
        debug.console_message(6, console_message, "_poll_mx_static()")

        # save data to circuit table
        circuit_table = _CircuitTable()

        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_static_show_arp_count",cmd1_merge)
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_static_arp_count",arp_count)

    def _poll_mx_vpls( self, circuit_name):
        
        debug = _Debug()
        console_message = "Poll mx_vpls"
        debug.console_message(4, console_message, "poll_mx_vpls()")

        mx_connect = _MXConnect()

        # run show commands
        cmd1 = "show vpls connections instance {}".format(_MXSignatureMatcher.routing_instance_name)
        cmd2 = "show vpls mac-table instance {}".format(_MXSignatureMatcher.routing_instance_name)
        cmd1_output = mx_connect.run_command(cmd1)
        cmd2_output = mx_connect.run_command(cmd2)
        
        # merge device name, command, and output for storage in circuit table
        checker = CircuitCheck()
        cmd1_merge = checker.device_name + "> " + cmd1 + "\n" + cmd1_output
        cmd2_merge = checker.device_name + "> " + cmd2 + "\n" + cmd2_output
        
        # parse output
        parsed_cmd1 = mx_connect.parse_poll_data(cmd1_merge)
        parsed_cmd2 = mx_connect.parse_poll_data(cmd2_merge)
        
        # save data
        remote_pe = parsed_cmd1[0][0]['counters']['pe_up']
        mac_count = parsed_cmd2[0][0]['counters']['mac_count']
        
        # console messages
        console_message = "VPLS Remote PE's Up : {}".format(remote_pe)
        debug.console_message(6, console_message, "_poll_mx_vpls()")

        console_message = "VPLS Mac Count : {}".format(mac_count)
        debug.console_message(6, console_message, "_poll_mx_vpls()")

        # save data to circuit table
        circuit_table = _CircuitTable()

        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_vpls_show_number_remote_pe_up",cmd1_merge)
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_vpls_show_mac_count",cmd2_merge) 
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_vpls_number_remote_pe_up",remote_pe)
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_vpls_mac_count",mac_count)
   
    def _poll_mx_l2vpn( self, circuit_name):
        
        debug = _Debug()
        console_message = "Poll mx_l2vpn"
        debug.console_message(4, console_message, "poll_mx_l2vpn()")

        mx_connect = _MXConnect()

        # run show commands
        cmd1 = "show l2vpn connections instance {}".format(_MXSignatureMatcher.routing_instance_name)
        cmd1_output = mx_connect.run_command(cmd1)
        
        # merge device name, command, and output for storage in circuit table
        checker = CircuitCheck()
        cmd1_merge = checker.device_name + "> " + cmd1 + "\n" + cmd1_output

        # parse output
        parsed_cmd1 = mx_connect.parse_poll_data(cmd1_merge)
        
        # save data
        remote_pe = parsed_cmd1[0][0]['counters']['pe_up']
        
        # console messages
        console_message = "l2vpn Remote PE's Up : {}".format(remote_pe)
        debug.console_message(6, console_message, "_poll_mx_l2vpn()")

        # save data to circuit table
        circuit_table = _CircuitTable()
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_l2vpn_show_number_remote_pe_up",cmd1_merge)
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_l2vpn_number_remote_pe_up",remote_pe)

    def _poll_mx_eline_haprin( self, circuit_name):
        
        debug = _Debug()
        console_message = "Poll mx_eline_hairpin"
        debug.console_message(4, console_message, "poll_mx_eline_hairpin()")

        mx_connect = _MXConnect()

        # run show commands
        cmd1 = "show vpls mac-table instance {}".format(_MXSignatureMatcher.routing_instance_name)
        cmd1_output = mx_connect.run_command(cmd1)
        
        # merge device name, command, and output for storage in circuit table
        checker = CircuitCheck()
        cmd1_merge = checker.device_name + "> " + cmd1 + "\n" + cmd1_output
        
        # parse output
        parsed_cmd1 = mx_connect.parse_poll_data(cmd1_merge)
        
        # save data
        mac_count = parsed_cmd1[0][0]['counters']['mac_count']
        
        # console messages
        console_message = "VPLS Mac Count : {}".format(mac_count)
        debug.console_message(6, console_message, "_poll_mx_eline_hairpin()")

        # save data to circuit table
        circuit_table = _CircuitTable()

        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_hairpin_eline_show_mac_count",cmd1_merge) 
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_hairpin_eline_mac_count",mac_count)

    def _poll_mx_elan_evpl_haprin( self, circuit_name):
        
        debug = _Debug()
        console_message = "Poll mx_elan_evpl_hairpin"
        debug.console_message(4, console_message, "poll_mx_elan_evpl_hairpin()")

        mx_connect = _MXConnect()

        # run show commands
        cmd1 = "show vpls mac-table instance {}".format(_MXSignatureMatcher.routing_instance_name)
        cmd1_output = mx_connect.run_command(cmd1)
        
        # merge device name, command, and output for storage in circuit table
        checker = CircuitCheck()
        cmd1_merge = checker.device_name + "> " + cmd1 + "\n" + cmd1_output
        
        # parse output
        parsed_cmd1 = mx_connect.parse_poll_data(cmd1_merge)
        
        # save data
        mac_count = parsed_cmd1[0][0]['counters']['mac_count']
        
        # console messages
        console_message = "VPLS Mac Count : {}".format(mac_count)
        debug.console_message(6, console_message, "_poll_mx_elan_evpl_hairpin()")

        # save data to circuit table
        circuit_table = _CircuitTable()

        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_hairpin_elan_evpl_show_mac_count",cmd1_merge) 
        circuit_table.update_circuit_table(CircuitCheck.user_run_mode, circuit_name,"mx_hairpin_elan_evpl_mac_count",mac_count)

###################################### Class Block
class _Reporter:
    
    complete_report = ""
    output_diff_report = ""
    report_subject_line = ""
    per_circuit_diff_html_table_rows = ""
    diff_output_html_rows = ""
    
    all_circuit_diff_table_data = {
        "precheck"                  : {
            "interfaces_up"         : 0,
            "bgp_up"                : 0,
            "mac_count"             : 0,
            "arp_count"             : 0,
            "remote_pe"             : 0 
        },
        
        "postcheck"                 : {
            "interfaces_up"         : 0,
            "bgp_up"                : 0,
            "mac_count"             : 0,
            "arp_count"             : 0,
            "remote_pe"             : 0
        }
    }
    
    per_circuit_diff_sorted = {
                                "BGP"                : [],
                                "Static"             : [],
                                "VPLS"               : [],
                                "L2VPN"              : [],
                                "BGP_IRB"            : [],
                                "ELINE Hairpin"      : [],
                                "ELAN/EVPL Hairpin"  : []
    }

    per_circuit_diff_row_template = {
        "cid"         : "",
        "precheck"    : {
                            "signature"             : "",
                            "device_name"           : "",
                            "interface1_name"       : "",
                            "interface1_state"      : "",
                            "interface2_name"       : "",
                            "interface2_state"      : "",
                            "poll_1"                : "",
                            "poll_2"                : "",
                            "poll_1_show_output"    : "",
                            "poll_2_show_output"    : "",
                            "int1_show_output"      : "",
                            "int2_show_output"      : "",
                            "poll_1_header"         : "",
                            "poll_2_header"         : ""
                            
                        },
        "postcheck"    : {
                            "signature"             : "",
                            "device_name"           : "",
                            "interface1_name"       : "",
                            "interface1_state"      : "",
                            "interface2_name"       : "",
                            "interface2_state"      : "",
                            "poll_1"                : "",
                            "poll_2"                : "",
                            "poll_1_show_output"    : "",
                            "poll_2_show_output"    : "",
                            "int1_show_output"      : "",
                            "int2_show_output"      : "",
                            "poll_1_header"         : "",
                            "poll_2_header"         : ""
                        }               
        }
 
    per_circuit_diff_html_table_header = '''
<table border=1>
  <thead>
    <tr>
      <th style="text-align: center">CID</th>
      <th style="text-align: center">Signature</th>
      <th style="text-align: center">Router</th>
      <th style="text-align: center">Interface</th>
      <th style="text-align: center">Poll 1</th>
      <th style="text-align: center">Poll 2</th>
      <th style="text-align: center"></th>
      <th style="text-align: center">Signature</th>
      <th style="text-align: center">Router</th>
      <th style="text-align: center">Interface</th>
      <th style="text-align: center">Poll 1</th>
      <th style="text-align: center">Poll 2</th>
    </tr>
  </thead>
  <tbody>
'''  

    per_circuit_diff_html_table_close = '''
  </tbody>
</table>
'''

    diff_output_head = '''
<head>
    <meta http-equiv="Content-Type"
          content="text/html; charset=utf-8" />
    <title></title>
    <style type="text/css">
        table.diff {font-family:Courier; border:medium;}
        .diff_header {background-color:#e0e0e0}
        td.diff_header {text-align:right}
        .diff_next {background-color:#c0c0c0}
        .diff_add {background-color:#aaffaa}
        .diff_chg {background-color:#ffff77}
        .diff_sub {background-color:#ffaaaa}
    </style>
</head>                
'''

    diff_output_circuit_footer = '''
</td>
</tr>
</table>
<br>
'''

    diff_output_footer = '''
</tbody>
</table>
'''

    def generate_report(self):

        # define headers
        message_header = "<h2>Messages</h2>"
        all_circuit_header = "<h2>All Circuit Diff</h2>"
        per_circuit_header = "<h2>Per Circuit Diff</h2>"
        output_diff_header = "<h2>Output Diff</h2>"

        debug = _Debug()
        console_message = "Report Generation"
        debug.console_message(0, console_message, "generate_report()")
        
        # build subject line
        _Reporter.report_subject_line = self._build_subject_line()

        # build message section
        message_section_html = self._build_message_section()
        
        # if login failed then end report at message section
        if message_section_html == "Login Failed":
            html = message_header + _MXConnect.error_message
            _Reporter.complete_report = html
            return
        
        # if resolve failed then end report at message section
        if message_section_html == "Resolve Failed":
            html = message_header + _Debug.error_message
            _Reporter.complete_report = html
            return
        
        # build all circuit diff section
        all_circuit_diff_html = self._build_all_circuit_diff_section()
        
        # build per circuit diff section
        per_circuit_diff_html = self._build_per_circuit_diff_section()
        
        # build out diff section
        #output_diff_html = self._build_output_diff_section()
        _Reporter.output_diff_report = output_diff_header + self._build_output_diff_section()
        
        # add blank line to debug
        debug.console_blank_line()
         
        #combine sections
        html = message_header + message_section_html
        html = html + all_circuit_header + all_circuit_diff_html
        html = html + per_circuit_header + per_circuit_diff_html
        #html = html + output_diff_header + output_diff_html
        
        # save report
        _Reporter.complete_report = html
        
    def _build_subject_line(self):

        debug = _Debug()
        
        console_message = "Build subject line"
        debug.console_message(2, console_message, "_build_subject_line()")
        
        run_mode = CircuitCheck.user_run_mode.capitalize()
        device_name = CircuitCheck.device_name
        
        str = "{} ({}) ciruits on {}".format(run_mode.upper(), CircuitCheck.circuit_count, device_name)

        console_message = "Subject line: {}".format(str)
        debug.console_message(4, console_message, "_build_subject_line()")

        return str
    
    def _build_message_section(self):

        circuit_table = _CircuitTable()
        debug = _Debug()
        message_section = ""

        console_message = "Build message section"
        debug.console_message(2, console_message, "_build_message_section()")
        
        # check for unable to login to device
        if _MXConnect.login_status == "Login Failed":
            return "Login Failed"
        
        # check for unable to resolve
        if _Debug.error_type == "Resolve Failed":
            return "Resolve Failed"
        
        # loop through circuit list check for no interface map or no signature match
        for circuit_name in CircuitCheck.user_circuit_list:
            
            # check if no hypen in circuit name
            if "-" not in circuit_name:
                message = "004 : {} : {} : No hypen in circuit name".format(CircuitCheck.user_run_mode, circuit_name)
                message_section = message_section + message + "<br>"
                continue  

            # check if no precheck
            result = circuit_table.was_circuit_prechecked(circuit_name)
            if CircuitCheck.user_run_mode == "postcheck" and result == "no":
                message = "003 : {} : Please precheck circuit before postcheck".format(circuit_name)
                message_section = message_section + message + "<br>"
                continue  
            
            # check if interface was no match
            result, message = self._check_no_match_interface(circuit_name)
            if result == "No Match":
                message_section = message_section + message + "<br>"
                continue

            # check if signature was no match
            result, message = self._check_no_match_signature(circuit_name)
            if result == "No Match":
                message_section = message_section + message + "<br>"

        # return message
        return message_section

    def _build_all_circuit_diff_section(self):

        debug = _Debug()
        console_message = "Build all circuit diff section"
        debug.console_message(2, console_message, "_build_all_circuit_diff()")
        
        self._build_all_circuit_diff_section_get_info()
        html = self._build_all_circuit_diff_table()
        return html

    def _build_output_diff_section(self):

        debug = _Debug()
        console_message = "Build output diff section"
        debug.console_message(2, console_message, "_build_output_diff_section()")
       
        html = _Reporter.diff_output_head
        html = html + _Reporter.diff_output_html_rows
        html = html + _Reporter.diff_output_footer
        return html

    def _build_per_circuit_diff_section(self):
        
        circuit_table = _CircuitTable()
        debug = _Debug()
        console_message = "Build per circuit diff section"
        debug.console_message(2, console_message, "_build_per_circuit_diff()")
        
        # loop through circuit list add data from database into dictionary
        for circuit_name in CircuitCheck.user_circuit_list:
    
            # skip if no hypen in circuit name
            if "-" not in circuit_name:
                continue
    
            # skip circuit if no precheck
            result = circuit_table.was_circuit_prechecked(circuit_name)
            if CircuitCheck.user_run_mode == "postcheck" and result == "no":
                continue  
            
            # skip interface if interface was not mapped
            result, message = self._check_no_match_interface(circuit_name)
            if result == "No Match":
                continue

            # skip interface if signature was not matched
            result, message = self._check_no_match_signature(circuit_name)
            if result == "No Match":
                continue
            
            # add circuit's precheck data to row template
            self._build_per_circuit_diff_get_data( circuit_name, "precheck" )
        
            # add circuit's postcheck data to row template
            if CircuitCheck.user_run_mode == "postcheck":
                self._build_per_circuit_diff_get_data( circuit_name, "postcheck" )
                
            # append template to sorted row list based on precheck signature
            _Reporter.per_circuit_diff_sorted[_Reporter.per_circuit_diff_row_template['precheck']['signature']].append(copy.deepcopy(_Reporter.per_circuit_diff_row_template))
            
            self._build_per_circuit_diff_row_precheck_side(circuit_name)
            self._build_per_circuit_diff_row_postcheck_side(circuit_name)
            
            self._build_output_diff_row(circuit_name)
    
            # reset row template
            _Reporter.per_circuit_diff_row_template['cid'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['signature'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['device_name'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['interface1_name'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['interface1_state'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['interface2_name'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['interface2_state'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['poll_1'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['poll_2'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['poll_1_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['poll_2_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['int1_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['int2_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['poll_1_header'] = ""
            _Reporter.per_circuit_diff_row_template['precheck']['poll_2_header'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['signature'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['device_name'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['interface1_name'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['interface1_state'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['interface2_name'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['interface2_state'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['poll_1'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['poll_2'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['poll_1_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['poll_2_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['int1_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['int2_show_output'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['poll_1_header'] = ""
            _Reporter.per_circuit_diff_row_template['postcheck']['poll_2_header'] = ""
            
            
        return _Reporter.per_circuit_diff_html_table_header + _Reporter.per_circuit_diff_html_table_rows + _Reporter.per_circuit_diff_html_table_close

    def _build_output_diff_row(self, circuit_name):
        
        signature = _Reporter.per_circuit_diff_row_template['precheck']['signature']
        html_diff_poll_1 = ""
        html_diff_poll_2 = ""
        html_command_head1 = ""
        html_command_head2 = ""
        html_command_head3 = ""
        
        # generate html for circuit header
        html_circuit_head = self._build_output_diff_circuit_head( signature, circuit_name )
        
        # generate html for show interface
        html_command_head1 = self._build_output_diff_circuit_command("Show Interface")
        precheck_output = _Reporter.per_circuit_diff_row_template['precheck']['int1_show_output']
        postcheck_output = _Reporter.per_circuit_diff_row_template['postcheck']['int1_show_output']
        precheck_output = precheck_output.splitlines()
        postcheck_output = postcheck_output.splitlines()
    
        diff = difflib.HtmlDiff(wrapcolumn=60)
        html_diff_show_int = diff.make_table(precheck_output, postcheck_output, "Precheck", "Postcheck")

        # generate html for poll 1
        html_command_head2 = _Reporter.per_circuit_diff_row_template['precheck']['poll_1_header']
        precheck_output = _Reporter.per_circuit_diff_row_template['precheck']['poll_1_show_output']
        postcheck_output = _Reporter.per_circuit_diff_row_template['postcheck']['poll_1_show_output']

        if precheck_output != "":
            precheck_output = precheck_output.splitlines()
            postcheck_output = postcheck_output.splitlines()
            diff = difflib.HtmlDiff(wrapcolumn=60)
            html_diff_poll_1 = diff.make_table(precheck_output, postcheck_output, "Precheck", "Postcheck")
        
        # generate html for poll 2
        html_command_head3 = _Reporter.per_circuit_diff_row_template['precheck']['poll_2_header']
        precheck_output = _Reporter.per_circuit_diff_row_template['precheck']['poll_2_show_output']

        if precheck_output != "":        
            postcheck_output = _Reporter.per_circuit_diff_row_template['postcheck']['poll_2_show_output']
            precheck_output = precheck_output.splitlines()
            postcheck_output = postcheck_output.splitlines()
            diff = difflib.HtmlDiff(wrapcolumn=60)
            html_diff_poll_2 = diff.make_table(precheck_output, postcheck_output, "Precheck", "Postcheck")
        
        # combined htmls
        html_row = html_circuit_head
        html_row = html_row + html_command_head1
        html_row = html_row + html_diff_show_int
        html_row = html_row + html_command_head2
        html_row = html_row + html_diff_poll_1
        html_row = html_row + html_command_head3
        html_row = html_row + html_diff_poll_2
        html_row = html_row + _Reporter.diff_output_circuit_footer
        
        #
        _Reporter.diff_output_html_rows = _Reporter.diff_output_html_rows + html_row

    def _build_output_diff_circuit_head(self, signature, circuit_name):

        html_circuit_head = '''
<table border=1>
  <thead>
    <tr>
      <th style="text-align: center">{} - {}</th>

    </tr>
  </thead>
  <tbody>
'''.format( signature, circuit_name)

        return html_circuit_head

    def _build_output_diff_circuit_command(self, command):
        
        html = '''
<tr>
    <td style="text-align: center">{}               
'''.format(command)

        return html
        
    def _build_per_circuit_diff_row_precheck_side(self, circuit_name):

        html_color_red = "; color: red"
        html_color_green = "; color: green"
        
        # set interface 1 color
        int1_color_precheck = ""
        if _Reporter.per_circuit_diff_row_template['precheck']['interface1_state'] == "Up":
            int1_color_precheck = html_color_green

        if _Reporter.per_circuit_diff_row_template['precheck']['interface1_state'] != "Up":
            int1_color_precheck = html_color_red

        # if eline hairpin build interface 2 html
        int2_html = ""
        if _Reporter.per_circuit_diff_row_template['precheck']['signature'] == "ELINE Hairpin":

            # set interface 2 color
            int2_color_precheck = ""
            if _Reporter.per_circuit_diff_row_template['precheck']['interface2_state'] == "Up":
                int2_color_precheck = "green"

            if _Reporter.per_circuit_diff_row_template['precheck']['interface2_state'] != "Up":
                int2_color_precheck = "red"

            # create html string for interface 2
            int2_html = "<br><font color=\"{}\">{}</font>".format(int2_color_precheck, _Reporter.per_circuit_diff_row_template['precheck']['interface2_name'])
        
        # create html string for row
        html = '''
<tr>
<td style="text-align: left">{}</td>
<td style="text-align: left">{}</td>
<td style="text-align: left">{}</td>
<td style="text-align: left{}">{}{}</td>
<td style="text-align: left">{}</td>
<td style="text-align: left">{}</td>
<td></td>
'''.format(     _Reporter.per_circuit_diff_row_template['cid'],
                _Reporter.per_circuit_diff_row_template['precheck']['signature'],
                _Reporter.per_circuit_diff_row_template['precheck']['device_name'],
                int1_color_precheck,
                _Reporter.per_circuit_diff_row_template['precheck']['interface1_name'],
                int2_html,
                _Reporter.per_circuit_diff_row_template['precheck']['poll_1'],
                _Reporter.per_circuit_diff_row_template['precheck']['poll_2']
)
        
        # append row to table
        _Reporter.per_circuit_diff_html_table_rows = _Reporter.per_circuit_diff_html_table_rows + html

    def _build_per_circuit_diff_row_postcheck_side(self, circuit_name):

        html_color_red = "; color: red"
        html_color_green = "; color: green"

        # set interface 1 color for postcheck
        int1_color_postcheck = ""
        if _Reporter.per_circuit_diff_row_template['postcheck']['interface1_state'] == "Up":
            int1_color_postcheck = html_color_green

        if _Reporter.per_circuit_diff_row_template['postcheck']['interface1_state'] != "Up":
            int1_color_postcheck = html_color_red

        # if eline hairpin build interface 2 html
        int2_html = ""
        if _Reporter.per_circuit_diff_row_template['postcheck']['signature'] == "ELINE Hairpin":

            # set interface 2 color
            int2_color_postcheck = ""
            if _Reporter.per_circuit_diff_row_template['postcheck']['interface2_state'] == "Up":
                int2_color_postcheck = "green"

            if _Reporter.per_circuit_diff_row_template['postcheck']['interface2_state'] != "Up":
                int2_color_postcheck = "red"

            # create html string for interface 2
            int2_html = "<br><font color=\"{}\">{}</font>".format(int2_color_postcheck, _Reporter.per_circuit_diff_row_template['precheck']['interface2_name'])

        # set poll 1 color to red it different from precheck
        poll1_color_postcheck = ""
        if _Reporter.per_circuit_diff_row_template['precheck']['poll_1'] != _Reporter.per_circuit_diff_row_template['postcheck']['poll_1']:
            poll1_color_postcheck = html_color_red

        # set poll 2 color to red it different from precheck
        poll2_color_postcheck = ""
        if _Reporter.per_circuit_diff_row_template['precheck']['poll_2'] != _Reporter.per_circuit_diff_row_template['postcheck']['poll_2']:
            poll2_color_postcheck = html_color_red

        # set signature color to red if different from precheck
        signature_color_postcheck = ""
        if _Reporter.per_circuit_diff_row_template['precheck']['signature'] != _Reporter.per_circuit_diff_row_template['postcheck']['signature']:
            signature_color_postcheck = html_color_red
        
        # create html string for row
        html = '''
<td style="text-align: left{}">{}</td>
<td style="text-align: left">{}</td>
<td style="text-align: left{}">{}{}</td>
<td style="text-align: left{}">{}</td>
<td style="text-align: left{}">{}</td>
</tr>
'''.format(
                signature_color_postcheck,
                _Reporter.per_circuit_diff_row_template['postcheck']['signature'],
                _Reporter.per_circuit_diff_row_template['postcheck']['device_name'],
                int1_color_postcheck,
                _Reporter.per_circuit_diff_row_template['postcheck']['interface1_name'],
                int2_html,
                poll1_color_postcheck,
                _Reporter.per_circuit_diff_row_template['postcheck']['poll_1'],
                poll2_color_postcheck,
                _Reporter.per_circuit_diff_row_template['postcheck']['poll_2']
)
        # append row to table
        _Reporter.per_circuit_diff_html_table_rows = _Reporter.per_circuit_diff_html_table_rows + html

    def _build_per_circuit_diff_get_data( self, circuit_name, run_mode ):

        circuit_table = _CircuitTable()
      
        # get signature
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "service_type", run_mode )
        circuit_type = result.fetchone()[0]
        
        # get device name
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "device_name", run_mode )
        device_name = result.fetchone()[0]
        
        # get interface 1 name
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]

        # get interface 1 state
        if run_mode == "precheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
            run_id = result.fetchone()[0]
        
        if run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
            run_id = result.fetchone()[0]
        
        run_table = _RunTable()
        col_name = "mx_interface_polls_" + run_mode
        interface_polls_json = run_table.get_run_table(run_id, col_name)
        
        interface_polls = json.loads(interface_polls_json.fetchone()[0])
        interface1_state = interface_polls[interface1]['state']
        interface1_show_output = interface_polls[interface1]['show_output']

        # add data to common fields
        _Reporter.per_circuit_diff_row_template['cid'] = circuit_name
        _Reporter.per_circuit_diff_row_template[run_mode]['device_name'] = device_name
        _Reporter.per_circuit_diff_row_template[run_mode]['interface1_name'] = interface1
        _Reporter.per_circuit_diff_row_template[run_mode]['interface1_state'] = interface1_state
        _Reporter.per_circuit_diff_row_template[run_mode]['int1_show_output'] = interface1_show_output
        
        # add data to poll fields based on signature
        if circuit_type == "mx_bgp_physical" or circuit_type == "mx_bgp_logical":
            
            # poll data for per circuit diff
            _Reporter.per_circuit_diff_row_template[run_mode]['signature'] = "BGP"
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_bgp_neighbor_state", run_mode )
            bgp_state = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1'] = bgp_state

            # show capture for output diff
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_bgp_show_neighbor_state", run_mode )
            show_output = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_show_output'] = show_output
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_header'] = "Show BGP Neighbor"
          
        if circuit_type == "mx_vpls_physical" or circuit_type == "mx_vpls_logical":

            # poll data for per circuit diff
            _Reporter.per_circuit_diff_row_template[run_mode]['signature'] = "VPLS"
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_vpls_number_remote_pe_up", run_mode )
            remote_pe = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1'] = "PE=" + remote_pe
            
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_vpls_mac_count", run_mode )
            mac_count = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_2'] = "MAC=" + mac_count
            
            # show capture for output diff
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_vpls_show_number_remote_pe_up", run_mode )
            show_output = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_show_output'] = show_output
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_header'] = "Show VPLS Connections"

            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_vpls_show_mac_count", run_mode )
            show_output = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_2_show_output'] = show_output
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_2_header'] = "Show VPLS MAC Table"

        if circuit_type == "mx_l2vpn_phyical" or circuit_type == "mx_l2vpn_logical":

            # poll data for per circuit diff
            _Reporter.per_circuit_diff_row_template[run_mode]['signature'] = "L2VPN"
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_l2vpn_number_remote_pe_up", run_mode )
            remote_pe = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1'] = "PE=" + remote_pe

            # show capture for output diff
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_l2vpn_show_number_remote_pe_up", run_mode )
            show_output = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_show_output'] = show_output
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_header'] = "Show L2VPN Connections"


        if circuit_type == "mx_static_physical" or circuit_type == "mx_static_logical":

            # poll data for per circuit diff
            _Reporter.per_circuit_diff_row_template[run_mode]['signature'] = "Static"
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_static_arp_count", run_mode )
            arp_count = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1'] = "ARP=" + arp_count

            # show capture for output diff
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_static_show_arp_count", run_mode )
            show_output = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_show_output'] = show_output
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_header'] = "Show ARP"

        if circuit_type == "mx_elan_evpl_hairpin_physical" or circuit_type == "mx_elan_evpl_hairpin_logical":

            # poll data for per circuit diff
            _Reporter.per_circuit_diff_row_template[run_mode]['signature'] = "ELAN/EVPL Hairpin"
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_hairpin_elan_evpl_mac_count", run_mode )
            mac_count = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1'] = "MAC=" + mac_count            

            # show capture for output diff
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_hairpin_elan_evpl_show_mac_count", run_mode )
            show_output = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_show_output'] = show_output
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_header'] = "Show VPLS MAC Table"

        if circuit_type == "mx_eline_hairpin":

            # poll data for per circuit diff
            _Reporter.per_circuit_diff_row_template[run_mode]['signature'] = "ELINE Hairpin"
            self._get_mx_eline_hairpin_data(circuit_name, run_mode)
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_hairpin_eline_mac_count", run_mode )
            mac_count = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1'] = "MAC=" + mac_count    

            # show capture for output diff
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_hairpin_eline_show_mac_count", run_mode )
            show_output = result.fetchone()[0]
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_show_output'] = show_output
            _Reporter.per_circuit_diff_row_template[run_mode]['poll_1_header'] = "Show VPLS MAC Table"
            
            # get interface 2 name and state if eline hairpin
            interface2 = interface_list[1]
            
            # get interface 2 state
            if run_mode == "precheck":
                result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
                run_id = result.fetchone()[0]
            
            if run_mode == "postcheck":
                result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
                run_id = result.fetchone()[0]
            
            run_table = _RunTable()
            col_name = "mx_interface_polls_" + run_mode
            interface_polls_json = run_table.get_run_table(run_id, col_name)
            
            interface_polls = json.loads(interface_polls_json.fetchone()[0])
            interface2_state = interface_polls[interface2]['state']
            interface2_show_output = interface_polls[interface2]['show_output']
            
            _Reporter.per_circuit_diff_row_template[run_mode]['interface2_name'] = interface2
            _Reporter.per_circuit_diff_row_template[run_mode]['interface2_state'] = interface2_state           

            # show capture for output diff
            _Reporter.per_circuit_diff_row_template[run_mode]['int2_show_output'] = interface2_show_output
            
        if circuit_type == "mx_bgp_irb_vpls_physical" or circuit_type == "mx_bgp_irb_vpls_logical":
            a = 1
            
    def _build_all_circuit_diff_table(self):

        html_color_red = "; color: red"
        html_color_green = "; color: green"
        interface_postcheck_color = ""
        bgp_postcheck_color = ""
        mac_count_postcheck_color = ""
        arp_count_postcheck_color = ""
        remote_pe_postcheck_color = ""
            
        # set postchecks if run mode is postcheck and polls different from precheck
        if CircuitCheck.user_run_mode == "postcheck":
            if _Reporter.all_circuit_diff_table_data['precheck']['interfaces_up'] != _Reporter.all_circuit_diff_table_data['postcheck']['interfaces_up']:
                interface_postcheck_color = html_color_red   

            if _Reporter.all_circuit_diff_table_data['precheck']['bgp_up'] != _Reporter.all_circuit_diff_table_data['postcheck']['bgp_up']:
                bgp_postcheck_color = html_color_red    
            
            # set postcheck mac count to red if different then precheck
            if _Reporter.all_circuit_diff_table_data['precheck']['mac_count'] != _Reporter.all_circuit_diff_table_data['postcheck']['mac_count']:
                mac_count_postcheck_color = html_color_red    
            
            # set postcheck arp count to red if different then precheck
            if _Reporter.all_circuit_diff_table_data['precheck']['arp_count'] != _Reporter.all_circuit_diff_table_data['postcheck']['arp_count']:
                arp_count_postcheck_color = html_color_red    
            
            # set postcheck remote pe to red if different then precheck
            if _Reporter.all_circuit_diff_table_data['precheck']['remote_pe'] != _Reporter.all_circuit_diff_table_data['postcheck']['remote_pe']:
                mac_count_postcheck_color = html_color_red    


        html = '''
<table border=1>
  <thead>
    <tr>
      <th style="text-align: center">Data</th>
      <th style="text-align: center">Precheck</th>
      <th style="text-align: center">Postcheck</th>
    </tr>
  </thead>
  <tbody>

<tr>
<td style="text-align: center">Interfaces Up</td>
<td style="text-align: center">{}</td>
<td style="text-align: center{}">{}</td>
</tr>

<tr>
<td style="text-align: center">BGP Up</td>
<td style="text-align: center">{}</td>
<td style="text-align: center{}">{}</td>
</tr>

<tr>
<td style="text-align: center">MAC Count</td>
<td style="text-align: center">{}</td>
<td style="text-align: center{}">{}</td>
</tr>

<tr>
<td style="text-align: center">ARP Count</td>
<td style="text-align: center">{}</td>
<td style="text-align: center{}">{}</td>
</tr>

<tr>
<td style="text-align: center">Remote PE Up</td>
<td style="text-align: center">{}</td>
<td style="text-align: center{}">{}</td>
</tr>

  </tbody>
</table>
'''.format(
        _Reporter.all_circuit_diff_table_data['precheck']['interfaces_up'],
        interface_postcheck_color,
        _Reporter.all_circuit_diff_table_data['postcheck']['interfaces_up'],
        _Reporter.all_circuit_diff_table_data['precheck']['bgp_up'],
        bgp_postcheck_color,
        _Reporter.all_circuit_diff_table_data['postcheck']['bgp_up'],
        _Reporter.all_circuit_diff_table_data['precheck']['mac_count'],
        mac_count_postcheck_color,
        _Reporter.all_circuit_diff_table_data['postcheck']['mac_count'],
        _Reporter.all_circuit_diff_table_data['precheck']['arp_count'],
        arp_count_postcheck_color,
        _Reporter.all_circuit_diff_table_data['postcheck']['arp_count'],
        _Reporter.all_circuit_diff_table_data['precheck']['remote_pe'],
        remote_pe_postcheck_color,
        _Reporter.all_circuit_diff_table_data['postcheck']['remote_pe']
)

        return html

    def _build_all_circuit_diff_section_get_info(self):

        circuit_table = _CircuitTable()

        # loop through circuit list
        for circuit_name in CircuitCheck.user_circuit_list:
   
            # skip if no hypen in circuit name
            if "-" not in circuit_name:
                continue
            
            # skip circuit if no precheck
            result = circuit_table.was_circuit_prechecked(circuit_name)
            if CircuitCheck.user_run_mode == "postcheck" and result == "no":
                continue  
   
            # skip interface if interface was not mapped
            result, message = self._check_no_match_interface(circuit_name)
            if result == "No Match":
                continue

            # skip interface if signature was not matched
            result, message = self._check_no_match_signature(circuit_name)
            if result == "No Match":
                continue
            
            # get circuit type precheck
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "service_type", "precheck" )
            circuit_type = result.fetchone()[0]

            # get precheck status information and add to tally dictionary
            self._build_all_circuit_diff_section_get_info_run_mode(circuit_name, circuit_type, "precheck")

            # get postcheck status information and add to tally dictionary
            if CircuitCheck.user_run_mode == "postcheck":

                # get circuit type postcheck
                result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "service_type", "postcheck" )
                circuit_type = result.fetchone()[0]

                self._build_all_circuit_diff_section_get_info_run_mode(circuit_name, circuit_type, "postcheck")
            

    def _build_all_circuit_diff_section_get_info_run_mode( self, circuit_name, circuit_type, run_mode):

        if circuit_type == "mx_vpls_physical" or circuit_type == "mx_vpls_logical":
            self._get_mx_vpls_data(circuit_name, run_mode)

        if circuit_type == "mx_static_physical" or circuit_type == "mx_static_logical":
            self._get_mx_static_arp_count(circuit_name, run_mode)

        if circuit_type == "mx_bgp_physical" or circuit_type == "mx_bgp_logical":
            self._get_mx_bgp_status(circuit_name, run_mode)

        if circuit_type == "mx_eline_hairpin":
            self._get_mx_eline_hairpin_data(circuit_name, run_mode)

        if circuit_type == "mx_elan_evpl_hairpin_physical" or circuit_type == "mx_elan_evpl_hairpin_logical":
            self._get_mx_elan_evpl_hairpin_data(circuit_name, run_mode)

        if circuit_type == "mx_l2vpn_phyical" or circuit_type == "mx_l2vpn_logical":
            self._get_mx_l2vpn_data(circuit_name, run_mode)

        if circuit_type == "mx_bgp_irb_vpls":
            a = 1

    def _get_mx_bgp_status(self, circuit_name, run_mode):

        circuit_table = _CircuitTable()
        
        # get circuit interface 1
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # get interface 1 status
        interface1_state = _MXInterfaceMapper.interface_polls[interface1]['state']
        
        # if up increse tally
        if interface1_state == "Up":
            _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] + 1
       
        # get bgp state
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_bgp_neighbor_state", run_mode )
        bgp_state = result.fetchone()[0]
        
        # if established increse tally
        if bgp_state == "Established":
            _Reporter.all_circuit_diff_table_data[run_mode]['bgp_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['bgp_up'] + 1

    def _get_mx_static_arp_count(self, circuit_name, run_mode):

        circuit_table = _CircuitTable()
        
        # get circuit interface 1
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # get interface 1 status
        if run_mode == "precheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
            run_id = result.fetchone()[0]
        
        if run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
            run_id = result.fetchone()[0]
        
        run_table = _RunTable()
        col_name = "mx_interface_polls_" + run_mode
        interface_polls_json = run_table.get_run_table(run_id, col_name)
        
        interface_polls = json.loads(interface_polls_json.fetchone()[0])
        interface1_state = interface_polls[interface1]['state']
        
        # if up increse tally
        if interface1_state == "Up":
            _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] + 1
       
        # get arp count
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_static_arp_count", run_mode )
        arp_count = result.fetchone()[0]
        
        # increse tally
        _Reporter.all_circuit_diff_table_data[run_mode]['arp_count'] = _Reporter.all_circuit_diff_table_data[run_mode]['arp_count'] + int(arp_count)


    def _get_mx_vpls_data(self, circuit_name, run_mode):

        circuit_table = _CircuitTable()
        
        # get circuit interface 1
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # get interface 1 status
        if run_mode == "precheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
            run_id = result.fetchone()[0]
        
        if run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
            run_id = result.fetchone()[0]
        
        run_table = _RunTable()
        col_name = "mx_interface_polls_" + run_mode
        interface_polls_json = run_table.get_run_table(run_id, col_name)
        interface_polls = json.loads(interface_polls_json.fetchone()[0])
        interface1_state = interface_polls[interface1]['state']
        
        # if up increse tally
        if interface1_state == "Up":
            _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] + 1
       
        # get vpls remote pe up
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_vpls_number_remote_pe_up", run_mode )
        remote_pe = result.fetchone()[0]

        # get vpls mac count
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_vpls_mac_count", run_mode )
        mac_count = result.fetchone()[0]

        # increase tallys
        _Reporter.all_circuit_diff_table_data[run_mode]['remote_pe'] = _Reporter.all_circuit_diff_table_data[run_mode]['remote_pe'] + int(remote_pe)
        _Reporter.all_circuit_diff_table_data[run_mode]['mac_count'] = _Reporter.all_circuit_diff_table_data[run_mode]['mac_count'] + int(mac_count)

    def _get_mx_l2vpn_data(self, circuit_name, run_mode):

        circuit_table = _CircuitTable()
        
        # get circuit interface 1
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # get interface 1 status
        if run_mode == "precheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
            run_id = result.fetchone()[0]
        
        if run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
            run_id = result.fetchone()[0]
        
        run_table = _RunTable()
        col_name = "mx_interface_polls_" + run_mode
        interface_polls_json = run_table.get_run_table(run_id, col_name)
        
        interface_polls = json.loads(interface_polls_json.fetchone()[0])
        interface1_state = interface_polls[interface1]['state']
        
        # if up increse tally
        if interface1_state == "Up":
            _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] + 1
       
        # get l2vpn remote pe up
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_l2vpn_number_remote_pe_up", run_mode )
        remote_pe = result.fetchone()[0]

        # increase tallys
        _Reporter.all_circuit_diff_table_data[run_mode]['remote_pe'] = _Reporter.all_circuit_diff_table_data[run_mode]['remote_pe'] + int(remote_pe)

    def _get_mx_elan_evpl_hairpin_data(self, circuit_name, run_mode):

        circuit_table = _CircuitTable()
        
        # get circuit interface 1
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # get interface 1 status
        if run_mode == "precheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
            run_id = result.fetchone()[0]
        
        if run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
            run_id = result.fetchone()[0]
        
        run_table = _RunTable()
        col_name = "mx_interface_polls_" + run_mode
        interface_polls_json = run_table.get_run_table(run_id, col_name)
        
        interface_polls = json.loads(interface_polls_json.fetchone()[0])
        interface1_state = interface_polls[interface1]['state']
        
        # if up increse tally
        if interface1_state == "Up":
            _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] + 1
       
        # get vpls mac count
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_hairpin_elan_evpl_mac_count", run_mode )
        mac_count = result.fetchone()[0]

        # increase tallys
        _Reporter.all_circuit_diff_table_data[run_mode]['mac_count'] = _Reporter.all_circuit_diff_table_data[run_mode]['mac_count'] + int(mac_count)

    def _get_mx_eline_hairpin_data(self, circuit_name, run_mode):

        circuit_table = _CircuitTable()
        
        # get circuit interface 1
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface1 = interface_list[0]
        
        # get interface 1 status
        if run_mode == "precheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
            run_id = result.fetchone()[0]
        
        if run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
            run_id = result.fetchone()[0]
        
        run_table = _RunTable()
        col_name = "mx_interface_polls_" + run_mode
        interface_polls_json = run_table.get_run_table(run_id, col_name)
        
        interface_polls = json.loads(interface_polls_json.fetchone()[0])
        interface1_state = interface_polls[interface1]['state']
        
        # if up increse tally
        if interface1_state == "Up":
            _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] + 1
            
        # get circuit interface 2
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", run_mode )
        interface_list = json.loads(result_json.fetchone()[0])
        interface2 = interface_list[1]
        
        # get interface 1 status
        if run_mode == "precheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "precheck" )
            run_id = result.fetchone()[0]
        
        if run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "run_table_row_id_last", "postcheck" )
            run_id = result.fetchone()[0]
        
        run_table = _RunTable()
        col_name = "mx_interface_polls_" + run_mode
        interface_polls_json = run_table.get_run_table(run_id, col_name)
        
        interface_polls = json.loads(interface_polls_json.fetchone()[0])
        interface2_state = interface_polls[interface1]['state']
        
        # if up increse tally
        if interface2_state == "Up":
            _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] = _Reporter.all_circuit_diff_table_data[run_mode]['interfaces_up'] + 1
            
        # get vpls mac count
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_hairpin_eline_mac_count", run_mode )
        mac_count = result.fetchone()[0]

        # increase tallys
        _Reporter.all_circuit_diff_table_data[run_mode]['mac_count'] = _Reporter.all_circuit_diff_table_data[run_mode]['mac_count'] + int(mac_count)
        
    def _check_no_match_interface(self, circuit_name):
        
        debug = _Debug()
        circuit_table = _CircuitTable()

        # check if circuit interface could not be mapped on precheck

        # get first interface mapped to circuit
        result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", "precheck" )
        interface_list = json.loads(result_json.fetchone()[0])
        
        # skip circuit if interface could not be mapped
        if len(interface_list) == 0:
            console_message = "001 : Precheck : Interface Mapper : \"{}\" : No interface description containing circuit name was found".format(circuit_name)
            debug.console_message(4, console_message, "_build_message_section_no_interface_match()")
            return "No Match", console_message
        
        # check if circuit interface could not be mapped on postcheck
        if CircuitCheck.user_run_mode == "postcheck":
            result_json = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "mx_circuit_interfaces", "postcheck" )
            interface_list = json.loads(result_json.fetchone()[0])
            
            # skip circuit if interface could not be mapped
            if len(interface_list) == 0:
                console_message = "001 : Postcheck : Interface Mapper : \"{}\" : No interface description containing circuit name was found".format(circuit_name)
                debug.console_message(4, console_message, "_build_message_section_no_interface_match()")
                return "No Match", console_message
        
        # return match if circuit interface was mapped
        return "Match", ""
        
    def _check_no_match_signature(self, circuit_name):
        
        debug = _Debug()
        circuit_table = _CircuitTable()

        # check if circuit signature could not be mapped on precheck
        result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "service_type", "precheck" )
        circuit_type = result.fetchone()[0]
        
        if circuit_type == "No Match":
            console_message = "002 : Precheck : Signature Matcher : \"{}\" : Circuit did not match a signature profile see debug log for details".format(circuit_name)
            debug.console_message(4, console_message, "_build_message_section_no_signature_match()")
            return "No Match", console_message
        
        # check if circuit signature could not be mapped on postcheck
        if CircuitCheck.user_run_mode == "postcheck":
            result = circuit_table.get_circuit_table_manual_run_mode(circuit_name, "service_type", "postcheck" )
            circuit_type = result.fetchone()[0]

            if circuit_type == "No Match":
                console_message = "002 : Postcheck : Signature Matcher : \"{}\" : Circuit did not match a signature profile see debug log for details".format(circuit_name)
                debug.console_message(4, console_message, "_build_message_section_no_signature_match()")
                return "No Match", console_message

        # return match if circuit signature was matched
        return "Match", ""

###################################### Class Block
class _SQLDatabase:

    database_connection = None
    database_cursor     = None
    
    def open_sql_database(self):
        
        # build circuit databae filename from user id
        CircuitCheck.full_file_name_database = CircuitCheck.user_id + CircuitCheck.suffix_database

        # debug messages
        debug = _Debug()
        console_message = "Opening connection to SQL database"
        debug.console_message(0, console_message, "open_sql_database()")
        
        console_message = "{}".format(os.path.abspath(CircuitCheck.full_file_name_database))
        debug.console_message(2, console_message, "open_sql_database()")
        
        # create new database or open existing file
        _SQLDatabase.database_connection = sqlite3.connect(CircuitCheck.full_file_name_database)
        _SQLDatabase.database_cursor = _SQLDatabase.database_connection.cursor()

        console_message = "Connection successfully opened"
        debug.console_message(2, console_message, "open_sql_database()")

###################################### Class Block
class _RunTable:
      
    table_columns = """
    user_run_mode,
    user_email_address,
    user_circuit_list,
    device_name,
    device_model,
    time,
    date,
    mx_interface_polls_precheck,
    mx_interface_polls_postcheck    
    """
    
    current_row_id = None

    def create_table_if_not_exist(self):
        
        # create run table if it does not exist
        sql_create_table = "CREATE TABLE IF NOT EXISTS run_table (row_id INTEGER PRIMARY KEY,{});".format(_RunTable.table_columns)    
        sqldatabase = _SQLDatabase()
        sqldatabase.database_cursor.execute(sql_create_table)
        
        # debug message
        debug = _Debug()
        console_message = "Create run table if it does not exist"
        debug.console_message(0, console_message, "create_table_if_not_exist()")
       
    def create_new_row(self, user_circuit_list, user_run_mode, device_name, user_email_address, device_model):
     
        # get date and time
        now = datetime.now()
        date = now.strftime("%y-%m-%d")
        time = now.strftime("%H:%M:%S")

        # encode circuit list into json for sql database
        user_circuit_list_json = json.dumps(user_circuit_list)

        # create run table if it does not exist
        sql_create_row = "INSERT INTO run_table ({}) VALUES ('{}','{}','{}','{}','{}','{}','{}','{}','{}');".format( _RunTable.table_columns,
                                                                                                                user_run_mode,
                                                                                                                user_email_address,
                                                                                                                user_circuit_list_json,
                                                                                                                device_name,
                                                                                                                device_model,
                                                                                                                time,
                                                                                                                date,
                                                                                                                "",
                                                                                                                "")
       
        sqldatabase = _SQLDatabase()
        sqldatabase.database_cursor.execute(sql_create_row)
        _RunTable.current_row_id = sqldatabase.database_cursor.lastrowid
        sqldatabase.database_connection.commit()

        # debug message
        debug = _Debug()
        console_message = "Added new row to run table ID {}".format(_RunTable.current_row_id)
        debug.console_message(0, console_message, "create_new_row()")

    def get_run_table_row_id(self):
        return _RunTable.current_row_id
    
    def update_run_table(self, colunm_name, new_value):
        sql_update_colunm_value = "UPDATE run_table SET {} = '{}';".format(colunm_name,new_value)
        sqldatabase = _SQLDatabase()
        sqldatabase.database_cursor.execute(sql_update_colunm_value)
        sqldatabase.database_connection.commit()
        
    def get_run_table(self, row_id, colunm_name):
        
        sqldatabase = _SQLDatabase()
        sql = "SELECT {} FROM run_table WHERE row_id = {};".format(colunm_name, row_id)
        result = sqldatabase.database_cursor.execute(sql)
        return result
                    
###################################### Class Block
class _CircuitTable:
    
    table_columns = """
run_table_row_id_last_precheck,
run_table_row_id_last_postcheck,
circuit_name,
service_type_precheck,
service_type_postcheck,
device_name_precheck,
device_name_postcheck,
device_model_precheck,
device_model_postcheck,
mx_circuit_interfaces_precheck,
mx_circuit_interfaces_postcheck,
mx_bgp_neighbor_state_precheck,
mx_bgp_show_neighbor_state_precheck,
mx_bgp_neighbor_state_postcheck,
mx_bgp_show_neighbor_state_postcheck,
mx_bgp_irb_neighbor_state_precheck,
mx_bgp_irb_show_neighbor_state_precheck,
mx_bgp_irb_neighbor_state_postcheck,
mx_bgp_irb_show_neighbor_state_postcheck,
mx_static_arp_count_precheck,
mx_static_show_arp_count_precheck,
mx_static_arp_count_postcheck,
mx_static_show_arp_count_postcheck,
mx_vpls_number_remote_pe_up_precheck,
mx_vpls_show_number_remote_pe_up_precheck,
mx_vpls_number_remote_pe_up_postcheck,
mx_vpls_show_number_remote_pe_up_postcheck,
mx_vpls_mac_count_precheck,
mx_vpls_show_mac_count_precheck,
mx_vpls_mac_count_postcheck,
mx_vpls_show_mac_count_postcheck,
mx_l2vpn_number_remote_pe_up_precheck,
mx_l2vpn_show_number_remote_pe_up_precheck,
mx_l2vpn_number_remote_pe_up_postcheck,
mx_l2vpn_show_number_remote_pe_up_postcheck,
mx_hairpin_eline_mac_count_precheck,
mx_hairpin_eline_show_mac_count_precheck,
mx_hairpin_eline_mac_count_postcheck,
mx_hairpin_eline_show_mac_count_postcheck,
mx_hairpin_elan_evpl_mac_count_precheck,
mx_hairpin_elan_evpl_show_mac_count_precheck,
mx_hairpin_elan_evpl_mac_count_postcheck,
mx_hairpin_elan_evpl_show_mac_count_postcheck
"""
        
    def create_table_if_not_exist(self):
        
        # create circuit table if it does not exist
        sql_create_table = "CREATE TABLE IF NOT EXISTS circuit_table (row_id INTEGER PRIMARY KEY,{});".format(_CircuitTable.table_columns)
        sqldatabase = _SQLDatabase()  
        sqldatabase.database_cursor.execute(sql_create_table)

        # debug message
        debug = _Debug()
        console_message = "Create circuit table if it does not exist"
        debug.console_message(0, console_message, "create_table_if_not_exist()")

    def add_circuit_to_table(self,circuit_name):
        
        # create new row with no values
        sql_create_row = "INSERT INTO circuit_table DEFAULT VALUES;"
        sqldatabase = _SQLDatabase()  
        sqldatabase.database_cursor.execute(sql_create_row)
        sqldatabase.database_connection.commit()

        # update circuit name field
        last_row_id = sqldatabase.database_cursor.lastrowid
        sql_update_circuit_id = "UPDATE circuit_table SET circuit_name = '{}' WHERE row_id = {};".format(circuit_name,last_row_id)
        sqldatabase.database_cursor.execute(sql_update_circuit_id)
        sqldatabase.database_connection.commit()
        
        # debug message
        debug = _Debug()
        console_message = "Added circuit to database"
        debug.console_message(2, console_message, "add_circuit_to_table()")
        
    def is_circuit_in_circuit_table(self, circuit_name):
        
        debug = _Debug()
        
        # check if circuit exist in table
        sql_query = "SELECT circuit_name FROM circuit_table WHERE circuit_name LIKE '{}';".format(circuit_name)
        sqldatabase = _SQLDatabase()
        result = sqldatabase.database_cursor.execute(sql_query)
        
        # return the result
        if result.fetchone() == None:
            
            # debug message
            console_message = "Circuit was not found in database"
            debug.console_message(2, console_message, "is_circuit_in_circuit_table()")
            return "no"
       
        else:

            # debug message
            console_message = "Circuit was found in database"
            debug.console_message(2, console_message, "is_circuit_in_circuit_table()")
            return "yes"

    def was_circuit_prechecked(self, circuit_id):

        #debug = _Debug()
        #console_message = "Checking if circuit \"{}\" was prechecked".format(circuit_id)
        #debug.console_message(2, console_message, "was_circuit_prechecked()")
        
        # check if circuit has been prechecked
        sql_query = "SELECT run_table_row_id_last_precheck FROM circuit_table WHERE circuit_name LIKE '{}';".format(circuit_id)
        sqldatabase = _SQLDatabase()
        result = sqldatabase.database_cursor.execute(sql_query)
          
        # if run_id_last_precheck is None then the circuit has not been prechecked
        if result.fetchone()[0] == None:
            #console_message = "Circuit was not prechecked"
            #debug.console_message(4, console_message, "was_circuit_prechecked()")
            return "no"
        else:
            #console_message = "Circuit was prechecked"
            #debug.console_message(4, console_message, "was_circuit_prechecked()")
            return "yes"        
        
    def update_circuit_table(self, user_run_mode, circuit_name, colunm_name, new_value):
        
        # update provided colunm with provided value
        # and appended runmode to provided colunm_name as seen here
        # example:
        #   router_name --> router_name_precheck
        #   router_name --> router_name_postcheck
        sql_update_colunm_value = "UPDATE circuit_table SET {}_{} = '{}' WHERE circuit_name = '{}';".format(colunm_name,user_run_mode,new_value,circuit_name)
        sqldatabase = _SQLDatabase()
        sqldatabase.database_cursor.execute(sql_update_colunm_value)
        sqldatabase.database_connection.commit()
        
    def get_circuit_table_auto_run_mode(self, circuit_name, colunm_name):
        sqldatabase = _SQLDatabase()
        circuit_check = CircuitCheck()
        user_run_mode = circuit_check.user_run_mode
        sql = "SELECT {}_{} FROM circuit_table WHERE circuit_name LIKE '{}';".format(colunm_name, user_run_mode, circuit_name)
        result = sqldatabase.database_cursor.execute(sql)
        return result

    def get_circuit_table_manual_run_mode(self, circuit_name, colunm_name, run_mode):
        sqldatabase = _SQLDatabase()
        sql = "SELECT {}_{} FROM circuit_table WHERE circuit_name LIKE '{}';".format(colunm_name, run_mode, circuit_name)
        result = sqldatabase.database_cursor.execute(sql)
        return result

              
###################################### Class Block
class _Debug:
    
    line_number = 0
    debug_log_email_attachment = ""

    error_type = ""
    error_message = ""

    def console_message(self, indent, message_text, method_name):
        
        # construct message
        message = "{:0>5}{} {} - {}".format(_Debug.line_number, ' '*indent, message_text, method_name)
        _Debug.line_number = _Debug.line_number + 1
        
        # print to screen
        print( message )

        # add to debug log email attachment
        _Debug.debug_log_email_attachment = _Debug.debug_log_email_attachment + message + '\n'
    
    def console_blank_line(self):
        
        # print to screen
        print()

        # add to debug log email attachment
        _Debug.debug_log_email_attachment = _Debug.debug_log_email_attachment + '\n'
    
    def skip_circuit(self, circuit_name, skip_message, skip_method, skip_action):
        a = 1
        
###################################### Main Block
def main():
    
    circuit_check = CircuitCheck()
    circuit_check.run_circuit_check_utility()
    
   
###################################### Entry Point
if __name__=="__main__":
    main()