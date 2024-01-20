import socket
import logging
import time
from datetime import datetime
import json
import random

def client_program():
    host = "host.docker.internal"
    #host = socket.gethostname()
    port = 5000
    waiting_time = 15
    time.sleep(waiting_time)

    # create log file
    logging.basicConfig(filename='output_crane.log', level=logging.DEBUG)

    # create connection to server
    client_socket = socket.socket()
    client_socket.connect((host, port))
    client_name = 'crane'
    print(client_name + ' nach connect')

    # declare error message variables
    error_msg_occupied = 'ERROR: Compartment is already occupied.'
    error_msg_empty = 'ERROR: Compartment is empty.'

    # declare request message
    request = {
        'message': 'Request for transport'
    }
    request.update( {'timestamp' : currentTime()} )
    json_send = json.dumps(request)

    # test connection between server and client
    client_socket.send(client_name.encode())
    print(client_name + ' send '+ str(client_name))
    data = client_socket.recv(1024).decode()
    print(client_name + ' recv '+ str(data))

    if data == 'crane':

        for x in range(10):
            # send message (request, error or transport confirmation) to server
            client_socket.send(json_send.encode())
            print(client_name + ' send '+ str(json_send))

            timestamp_1 = currentTime()

            # receive message from server
            json_recv = client_socket.recv(1024).decode()
            msg_recv = json.loads(json_recv)
            print(client_name + ' recv '+ str(msg_recv))

            timestamp_2 = currentTime()
            print(timestamp_1[18:], timestamp_2[18:])#, int(timestamp_2[:-6])-int(timestamp_1[:-6])

            # check if received message is a transport order
            if msg_recv['message'] == 'Move to':
                origin = msg_recv['from']
                destination = msg_recv['to']
                id = msg_recv['id']
                y = msg_recv['y']
                x = msg_recv['x']
                direction = msg_recv['direction']

                # generate inbound error: assigned compartment already contains an item
                random_number = random.randint(1, 10)
                print(random_number)
                if random_number <= 1 and origin == 'Inbound_place' and destination == 'Warehouse':
                   print(error_msg_occupied)
                   # declare occupied error message
                   msg_send = {
                       'message' : 'Occupied',
                       'id' : id,
                       'y' : y,
                       'x' : x,
                       'direction' : direction,
                   }
                # generate outbound error: assigned compartment does not contain item
                elif random_number <= 1 and origin == 'Warehouse' and destination == 'Outbound_place':
                   print(error_msg_empty)
                   # declare empty error message
                   msg_send = {
                       'message' : 'Empty',
                       'id' : id,
                       'y' : y,
                       'x' : x,
                       'direction' : direction,
                   }
                # declare transport confirmation message
                else:
                    msg_send = {
                        'message' : 'Moved',
                        'from' : origin,
                        'to' : destination,
                        'id' : id,
                        'y' : y,
                        'x' : x,
                        'direction' : direction,
                    }
                # send message
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
