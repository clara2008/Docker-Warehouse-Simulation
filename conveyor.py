import socket
import time
import json
import logging
from datetime import datetime


def client_program():
    host = "host.docker.internal"
    #host = socket.gethostname()
    port = 5000
    waiting_time = 10
    time.sleep(waiting_time)

    # create log file
    logging.basicConfig(filename='output_conveyor.log', level=logging.DEBUG)

    # create connection to server
    client_socket = socket.socket()
    client_socket.connect((host, port))
    client_name = 'conveyor'
    logging.debug(client_name + ' nach connect')

    # declare request message
    request = {
        'message': 'Request for transport'
    }
    request.update( {'timestamp' : currentTime()} )
    json_send = json.dumps(request)

    # test connection between server and client
    client_socket.send(client_name.encode())
    print(client_name + ' send ' + str(client_name))
    data = client_socket.recv(1024).decode()
    print(client_name + ' recv ' + str(data))

    if data == 'conveyor':

        for x in range(10):
            # send message (request or conveyance confirmation) to server
            client_socket.send(json_send.encode())
            print(client_name + ' send '+ str(json_send))

            # receive message from server
            json_recv = client_socket.recv(1024).decode()
            msg_recv = json.loads(json_recv)
            print(client_name + ' recv '+ str(msg_recv))

            # check if received message is a conveyance order
            if msg_recv['message'] == 'Move to':
                # declare and send conveyance confirmation message
                id = msg_recv['id']
                destination = msg_recv['to']
                msg_send = {
                    'message' : 'Moved',
                    'id' : id,
                    'to' : destination
                }
                msg_send.update( {'timestamp' : currentTime()} )
                json_send = json.dumps(msg_send)
                waiting_time = 5
            # check if received message is a no operation message
            elif msg_recv['message'] == 'No operation':
                # send another request message
                request.update( {'timestamp' : currentTime()} )
                json_send = json.dumps(request)
                waiting_time = 5
            # check if received message is a confirmation message
            elif msg_recv['message'] == 'Acknowledge':
                # send another request message
                request.update( {'timestamp' : currentTime()} )
                json_send = json.dumps(request)
                waiting_time = 0
            time.sleep(waiting_time)

    # close connection to server
    print('vor conn close')
    client_socket.close()  # close the connection

# get current timestamp
def currentTime():
    return str(datetime.now())

if __name__ == '__main__':
    client_program()
