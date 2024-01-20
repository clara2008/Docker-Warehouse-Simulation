from datetime import datetime
import socket
import logging
import _thread
import time
import json
import psycopg2

def server_program():
    host = socket.gethostname()
    #host = '0.0.0.0'
    port = 5000
    # create logging file
    logging.basicConfig(filename='output_server.log', level=logging.DEBUG)

    mydatetime = str(datetime.now())[:-7]

    server_socket = socket.socket()
    server_socket.bind((host, port))

    server_socket.listen(1)

    # create and test database connection
    db_conn = psycopg2.connect(
        database="postgres", user='postgres', password='docker', host='host.docker.internal', port= '5432'
        #database="postgres", user='postgres', password='docker', host='localhost', port= '5432'
    )
    cursor = db_conn.cursor()
    query_conn_test = "SELECT * FROM transport_units"
    cursor.execute(query_conn_test)
    db_test = cursor.fetchone()

    # task for client at identification point
    def idp_task(threadName, con, addr):
       logging.debug(threadName)

       for x in range(3):
           # receive data stream from client
           json_recv = con.recv(1024).decode()
           msg_recv = json.loads(json_recv)

           # if data is not received, break
           if not msg_recv:
              break

           logging.debug(threadName + ' recv ' + str(msg_recv))

           # create new database record based on the received seat data
           cursor = db_conn.cursor() #kann weg
           myquery = "INSERT INTO transport_units (id, color, type, weight, height, length, width, current_loc, outbound_request) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
           values = (msg_recv['id'], msg_recv['color'], msg_recv['type'], msg_recv['weight'], msg_recv['height'], msg_recv['length'], msg_recv['width'], msg_recv['current_loc'], msg_recv['outbound_request'])
           cursor.execute(myquery, values)

           # save changes to database
           db_conn.commit()

           # send confirmation to client
           msg_send = {
                'message' : 'ID saved in DB',
                'id' : msg_recv['id'],
           }
           msg_send.update( {'timestamp' : currentTime()} )
           json_send = json.dumps(msg_send)
           con.send(json_send.encode())
           logging.debug(threadName + ' send ' + json_send) #evtl. msg_send statt json_send notwendig

       # close the connection to client
       con.close()

    # task for conveyor client
    def conveyor_task(threadName, con, addr):
       logging.debug(threadName)

       for x in range(10):
           # receive data stream from client
           json_recv = con.recv(1024).decode()
           msg_recv = json.loads(json_recv)  # Convert JSON string to dictionary

           # if data is not received, break
           if not msg_recv:
               break

           logging.debug(threadName + ' recv '+ str(msg_recv))

           # check if received message is a request message
           if msg_recv['message'] == 'Request for transport':
               # search database for seats waiting at the identification point that need to be conveyed
               cursor = db_conn.cursor()
               myquery = "SELECT id FROM transport_units WHERE current_loc = 'IDP'"
               cursor.execute(myquery)
               db_record = cursor.fetchone()

               # send 'no operation' back to conveyor if there are no seats at the identification point
               if not db_record:
                   msg_send = {
                        'message' : 'No operation'
                   }
                   msg_send.update( {'timestamp' : currentTime()} )

               # send conveyance order to conveyor if there is a seat waiting at the identification point
               else:
                   seat_id = db_record[0]
                   msg_send = {
                        'message': 'Move to',
                        'from': 'IDP',
                        'to': 'Inbound_place',
                        'id': seat_id,
                   }
                   msg_send.update( {'timestamp' : currentTime()} )
               json_send = json.dumps(msg_send)
               con.send(json_send.encode())
               logging.debug(threadName + ' send '+ str(json_send))

           # if message is not a request, it is the confirmation of a successful conveyance
           else:
               seat_id = str(msg_recv['id'])
               logging.debug('seat_id: ' + seat_id)

               # update datebase record by setting current location of seat to inbound_place
               cursor = db_conn.cursor()
               myquery = "UPDATE transport_units SET current_loc = 'Inbound_place' WHERE id=%s"
               cursor.execute(myquery, (seat_id,))

               # save changes in database
               db_conn.commit()

               # send confirmation to conveyor
               msg_send = {
                    'message': 'Acknowledge',
                    'id': seat_id
               }
               msg_send.update( {'timestamp' : currentTime()} )
               json_send = json.dumps(msg_send)
               # to do: ein send für if und else gemeinsam
               con.send(json_send.encode())
               logging.debug(threadName + ' send ' + str(json_send))

       # close connection to conveyor
       con.close()

    # task for crane client
    def crane_task(threadName, con, addr):
        logging.debug(threadName)

        for x in range(10):
            # receive data stream from client
            json_recv = con.recv(1024).decode()
            msg_recv = json.loads(json_recv)

            # if data is not received, break
            if not msg_recv:
                break

            logging.debug(threadName + ' recv '+ str(msg_recv))

            # check if received message is a request message
            if msg_recv['message'] == 'Request for transport':
                # search database for seats waiting for outbound
                cursor = db_conn.cursor()
                query_outbound = "SELECT id, y, x, direction FROM transport_units tu LEFT JOIN warehouse wh ON tu.id = wh.seat_id WHERE current_loc = 'WH' AND outbound_request = true"
                cursor.execute(query_outbound)
                db_record_outbound = cursor.fetchone()

                if db_record_outbound:
                    seat_id = db_record_outbound[0]
                    y = db_record_outbound[1]
                    x = db_record_outbound[2]
                    direction = db_record_outbound[3]
                    # check for compartment of outbound seat
                    if direction: #hier schöner machen
                        print('Seat found in WH')
                        # declare outbound order
                        msg_send = {
                            'message': 'Move to',
                            'from' : 'Warehouse',
                            'to' : 'Outbound_place',
                            'y' : y,
                            'x' : x,
                            'direction' : direction,
                            'id': seat_id
                        }
                    # if compartment of outbound seat cannot be found, save error to database and send no operation message to crane
                    else:
                        print('ERROR: Seat_id could not be found in warehouse.')
                        query_flag_tu = "UPDATE transport_units SET current_loc = 'WH error not found' WHERE id = %s"
                        cursor.execute(query_flag_tu, (seat_id,))
                        db_conn.commit()
                        msg_send = {
                            'message' : 'No operation'
                        }
                # if there is no seat waiting for outbound, check for inbound
                else:
                    # search database for seats waiting for inbound
                    query_inbound = "SELECT id FROM transport_units WHERE current_loc='Inbound_place'"
                    cursor.execute(query_inbound)
                    db_record_inbound = cursor.fetchone()

                    if db_record_inbound:
                        seat_id = db_record_inbound[0]
                        logging.debug('seat id: ' + seat_id)
                        # search database for empty compartment
                        query_inbound_compartment = "SELECT y, x, direction FROM warehouse WHERE seat_id IS NULL AND status IS NULL ORDER BY y, x"
                        cursor.execute(query_inbound_compartment)
                        db_record_compartment = cursor.fetchone()

                    #    if not db_record_compartment:
                    #    order = {
                    #         'type' : 'Wait'
                    #    }

                        y = db_record_compartment[0]
                        x = db_record_compartment[1]
                        direction = db_record_compartment[2]
                        # send inbound order to crane
                        msg_send = {
                            'message' : 'Move to',
                            'from' : 'Inbound_place',
                            'to' : 'Warehouse',
                            'y' : y,
                            'x' : x,
                            'direction' : direction,
                            'id': seat_id
                        }

                    # if there is no seat waiting for inbound, send no operation message
                    else:
                        msg_send = {
                            'message': 'No operation'
                        }
                msg_send.update( {'timestamp' : currentTime()} )
                json_send = json.dumps(msg_send)
                con.send(json_send.encode())
                print(threadName + ' send '+ str(json_send))

            # check if message is a transport confirmation
            elif msg_recv['message'] == 'Moved':
                id = str(msg_recv['id'])
                seat_y = msg_recv['y']
                seat_x = msg_recv['x']
                seat_direction = str(msg_recv['direction'])

                cursor = db_conn.cursor()
                # check if confirmation message concerns outbound
                if msg_recv['from'] == 'Warehouse' and msg_recv['to'] == 'Outbound_place':
                    # update current location of seat to outbound_place and flag compartment as empty
                    query_outbound_done = "UPDATE transport_units SET outbound_request = false, current_loc = 'Outbound_place' WHERE id = %s"
                    query_outbound_done_2 = "UPDATE warehouse SET seat_id = NULL WHERE y = %s AND x = %s AND direction = %s"
                    cursor.execute(query_outbound_done, (id,))
                    cursor.execute(query_outbound_done_2, (seat_y, seat_x, seat_direction))
                # check if confirmation message concerns inbound
                elif msg_recv['from'] == 'Inbound_place' and msg_recv['to'] == 'Warehouse':
                    # update current location of seat to warehouse and flag compartment as occupied
                    query_inbound_done = "UPDATE transport_units SET current_loc = 'WH' WHERE id=%s"
                    query_inbound_done_2 = "UPDATE warehouse SET seat_id = %s WHERE y = %s AND x = %s AND direction = %s"
                    cursor.execute(query_inbound_done, (id,))
                    cursor.execute(query_inbound_done_2, (id, seat_y, seat_x, seat_direction))

                # save changes to database
                db_conn.commit()

                # declare and send confirmation message
                msg_send = {
                    'message': 'Acknowledge',
                    'id': seat_id
                }
                msg_send.update( {'timestamp' : currentTime()} )
                json_send = json.dumps(msg_send)
                con.send(json_send.encode())
                print(threadName + ' send ' + str(json_send))

            # check if message is an empty error message
            elif msg_recv['message'] == 'Empty':
                print('ERROR: Compartment is empty.')
                seat_id = str(msg_recv['id'])
                seat_y = msg_recv['y']
                seat_x = msg_recv['x']
                seat_direction = str(msg_recv['direction'])
                # save empty error to database
                cursor = db_conn.cursor()
                query_flag_tu = "UPDATE transport_units SET current_loc = 'WH error empty' WHERE id = %s"
                query_wh_status = "UPDATE warehouse SET status = 'Error empty' WHERE seat_id = %s"
                cursor.execute(query_flag_tu, (seat_id,))
                cursor.execute(query_wh_status, (seat_id,))
                # save changes to databases
                db_conn.commit()

                # declare confirmation message
                msg_send = {
                    'message': 'Acknowledge',
                    'id': seat_id
                }
                msg_send.update( {'timestamp' : currentTime()} )
                json_send = json.dumps(msg_send)
                con.send(json_send.encode())
                print(threadName + ' send '+ str(json_send))

            # check if message is an occupied error message
            elif msg_recv['message'] == 'Occupied':
                print('ERROR: Compartment is already occupied.')
                id = str(msg_recv['id'])
                seat_id = str(msg_recv['id'])
                seat_y = msg_recv['y']
                seat_x = msg_recv['x']
                seat_direction = str(msg_recv['direction'])
                # save occupied error to database
                cursor = db_conn.cursor()
                query_wh_status = "UPDATE warehouse SET status = 'Error occupied' WHERE y = %s AND x = %s AND direction = %s"
                cursor.execute(query_wh_status, (seat_y, seat_x, seat_direction))
                # save changes to database
                db_conn.commit()
                # search database for another empty compartment
                query_alt_compartment = "SELECT y, x, direction FROM warehouse WHERE seat_id IS NULL AND status IS NULL ORDER BY y, x"
                cursor.execute(query_alt_compartment)
                db_record_compartment = cursor.fetchone()
                y = db_record_compartment[0]
                x = db_record_compartment[1]
                direction = db_record_compartment[2]
                # send transport message with new compartment coordinates
                msg_send = {
                    'message' : 'Move to',
                    'from' : 'Inbound_place',
                    'to' : 'Warehouse',
                    'y' : y,
                    'x' : x,
                    'direction' : direction,
                    'id': id
                }
                msg_send.update( {'timestamp' : currentTime()} )
                json_send = json.dumps(msg_send)
                con.send(json_send.encode())
                print(threadName + ' send '+ str(json_send))

        # close connection to crane
        con.close()


    logging.debug("vor start thread")

    while True:
        conn_counter = 0
        # accept new socket connection
        conn, address = server_socket.accept()
        logging.debug("Connection from: " + str(address) +" x " + str(conn))
        # test connection between server and client
        client_name = conn.recv(1024).decode()
        logging.debug('Server' + ' recv '+ str(client_name))
        conn.send(client_name.encode())
        logging.debug('Server' + ' send '+ str(client_name))
        if client_name == 'idp_client':
            _thread.start_new_thread(idp_task, ('idp_client', conn, address) )
        elif client_name == 'conveyor':
            _thread.start_new_thread(conveyor_task, ('conveyor', conn, address) )
        elif client_name == 'crane':
            _thread.start_new_thread(crane_task, ('crane', conn, address) )

# get current timestamp
def currentTime():
    return str(datetime.now())

if __name__ == '__main__':
    server_program()
