from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect    
import time
import random
import math
import MySQLdb
import configparser
import datetime
import serial

ser = serial.Serial("/dev/ttyUSB0", 9600)
ser.baudrate = 9600

async_mode = None

config = configparser.ConfigParser()
config.read(r'./config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
print(myhost)

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 

persistEnabled = False
outfile = open(r'./persist.txt',"a+") 

def background_thread(args):
    global persistEnabled
    persistEnabled = False    
    while True:
        x = ser.readline().decode("ascii").strip()
        print(x)
        starti = x.find('++')
        endi = x.find('+', starti+2)
        if starti != -1 and endi != -1:
            v = x.find('VAR')
            if v == -1:
                n1 = x.find(':')
                n2 = x.find(';')
                tmp = float(x[n1+1:n2])
                n1 = x.find(':', n2)
                n2 = x.find(';', n2+1)
                hum = float(x[n1+1:n2])
                n1 = x.find(':', n2)
                n2 = x.find('+', n2+1)
                lig = int(x[n1+1:n2])
                timenow = int(time.time())
                if(persistEnabled):
                    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
                    cursor = db.cursor()
                    cursor.execute("INSERT INTO poit (time, temperature, humidity, light) VALUES (%s, %s, %s, %s)",(timenow, tmp, hum, lig))
                    db.commit()
                    cursor.close()
                    outfile.write(str(timenow) + ";" + str(tmp) + ";" + str(hum) + ";" + str(lig) + "\r\n")
                socketio.emit('sensor_response', {'serial': x, 'time': timenow, 'tmp' : tmp, 'hum' : hum, 'lig' : lig}, namespace='/poit')  
            else:
                print(v)
                print(endi)
                print(x)
                print(x[v+4:endi])
                v = v + 4
                varresp = float(x[v:endi])
                socketio.emit('requested_setting_response', {'var': varresp, 'serial': x}, namespace='/poit')
        else:
            socketio.emit('serial_only_response', {'serial': x}, namespace='/poit')

@app.route('/')
def index():
    return render_template('tabs.html', async_mode=socketio.async_mode)
    
@app.route('/log')
def readLog():
    fo = open(r'./persist.txt',"r") 
    rows = fo.readlines()
    res = []
    res1 = []
    res2 = []
    res3 = []
    res4 = []
    subres = []
    for line in rows:
        if not (line.isspace() or line == ''):
            subres = line.strip().split(';')
            res1.append(int(subres[0])) 
            res2.append(float(subres[1]))
            res3.append(float(subres[2]))
            res4.append(int(subres[3])) 
    res.append(res1)
    res.append(res2)
    res.append(res3)
    res.append(res4)
    fo.close()
    return render_template('graph.html', data=res)

@app.route('/db')
def readDB():
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
    cursor = db.cursor()
    cursor.execute("SELECT * FROM poit")
    rows = cursor.fetchall()
    res = []
    res1 = []
    res2 = []
    res3 = []
    res4 = []
    for line in rows:
        res1.append(int(line[0])) 
        res2.append(float(line[1]))
        res3.append(float(line[2]))
        res4.append(int(line[3])) 
    res.append(res1)
    res.append(res2)
    res.append(res3)
    res.append(res4)
    return render_template('graph.html', data=res)
  
@socketio.on('input_request', namespace='/poit')
def serialInputRequest(message):   
    inp = "##" + str(message['name']) + "#" + str(message['value']) + "#\n"
    ser.write(bytes(inp, "ascii"))
    print(inp)
    
@socketio.on('persistStart_request', namespace='/poit')
def startPersist():   
    global persistEnabled, outfile
    outfile.close()
    outfile = open(r'./persist.txt',"a+") 
    persistEnabled = True
    print("Persisting started")
    
@socketio.on('persistStop_request', namespace='/poit')
def stopPersist():   
    global persistEnabled, outfile
    outfile.close()
    persistEnabled = False
    print("Persisting stopped")
    
 
@socketio.on('disconnect_request', namespace='/poit')
def disconnect_request():
    disconnect()

@socketio.on('connect', namespace='/poit')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())

@socketio.on('disconnect', namespace='/poit')
def test_disconnect():
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
