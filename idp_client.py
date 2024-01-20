from datetime import datetime
import logging
import socket
import time
import json
import random


def client_program():
    host = "host.docker.internal"
    #host = socket.gethostname()
    port = 5000
    waiting_time = 5
    time.sleep(waiting_time)

    # create log file
    logging.basicConfig(filename='output_idp_client.log', level=logging.DEBUG)

    # create connection to server
    client_socket = socket.socket()
    client_socket.connect((host, port))
    client_name = 'idp_client'
    print(client_name + ' nach connect')

    # test connection between server and client
    client_socket.send(client_name.encode())
    print(client_name + ' send '+ str(client_name))
    data_ackn = client_socket.recv(1024).decode()
    print(client_name + ' recv '+ str(data_ackn))

    # declare seat id variable
    id = '0000'

    if data_ackn == 'idp_client':

        for x in range(3):
            # generate a new seat data set and set it to server
            seatData = generateSeatData(id, x+1)
            seatData.update( {'timestamp' : currentTime()} )
            msg_send = seatData
            json_send = json.dumps(msg_send)
            client_socket.send(json_send.encode())
            print(client_name + ' send '+ str(json_send))
            # receive confirmation from server
            json_recv = client_socket.recv(1024).decode()
            msg_recv = json.loads(json_recv)
            print(client_name +  ' recv ' + str(msg_recv))

            # wait 15 seconds before generating the next seat data set
            time.sleep(15)

    # close connection to server
    print('vor conn close')
    client_socket.close()

# generate a seat data set
def generateSeatData(id, id_count):
    colors = ['black', 'brown', 'beige']
    types = ['front', 'back']
    weights = [25000, 27000]
    heights = [1000, 1050, 1100]
    lengths = [550, 600]
    widths = [500, 550]

    seatData = {
        'id': id + str(id_count),
        'color': random.choice(colors),
        'type': random.choice(types),
        'weight': random.choice(weights),
        'height': random.choice(heights),
        'length': random.choice(lengths),
        'width': random.choice(widths),
        'current_loc': 'IDP',
        'outbound_request' : 'false'
    }
    return seatData

# get current timestamp
def currentTime():
    return str(datetime.now())[:-7]

if __name__ == '__main__':
    client_program()
