import socket
import psycopg2
from datetime import datetime

def client_program():
    host = "host.docker.internal"
    #host = socket.gethostname()
    port = 5000

    # create connection to server
    client_socket = socket.socket()
    client_socket.connect((host, port))
    print('attacker nach connect')

    # delete data from warehouse table
    #deleteWarehouseData()

    # execute DoS query
    #dosAttack()

    # close connection to server
    print('vor conn close')
    client_socket.close()

# Denial of Service Attack
def dosAttack():

    # create connection to database
    db_conn = psycopg2.connect(
        database="postgres", user='postgres', password='docker', host='localhost', port= '5432'
        #database="postgres", user='postgres', password='docker', host='host.docker.internal', port= '5432'
    )

    # execute DoS query
    cursor = db_conn.cursor()
    #dos_query = "SELECT * FROM xyz"
    dos_query = "UPDATE xyz SET sp1 = 'asdf' "
    for x in range(1000):
        cursor.execute(dos_query)
        print(str(datetime.now()))


def deleteWarehouseData():
    # create connection to database
    db_conn = psycopg2.connect(
        #database="postgres", user='postgres', password='docker', host='localhost', port= '5432'
        database="postgres", user='postgres', password='docker', host='host.docker.internal', port= '5432'
    )

    # overwrite all assigned seat ids in the warehouse table
    cursor = db_conn.cursor()
    attacker_query = "UPDATE warehouse SET seat_id = NULL"
    cursor.execute(attacker_query)
    db_conn.commit()


if __name__ == '__main__':
    client_program()
