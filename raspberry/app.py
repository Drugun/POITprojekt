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
    #A = 1
    count = 0   
    persistEnabled = False    
    #dataList = []       
    while True:
        #if args:
        #  A = dict(args).get('A')
        #socketio.sleep(1)
        #count += 1
        #out = float(A)*math.sin(count/10)
        #out2 = float(A)*math.cos(count/10)
        x = ser.readline().decode("ascii")
        print(x)
        starti = x.find('++')
        endi = x.find('+', starti)
        if starti != -1 and endi != -1:
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
            #dataDict = {
            #  "t": time.time(),
            #  "x": count,
            #  "y": out}
            #dataList.append(dataDict)
            if(persistEnabled):
                db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
                cursor = db.cursor()
                cursor.execute("INSERT INTO poit (time, temperature, humidity, light) VALUES (%s, %s, %s, %s)",(timenow, tmp, hum, lig))
                db.commit()
                cursor.close()
                outfile.write(str(timenow) + ";" + str(tmp) + ";" + str(hum) + ";" + str(lig) + "\r\n")
        
            socketio.emit('my_response', {'serial': x, 'time': timenow, 'tmp' : tmp, 'hum' : hum, 'lig' : lig}, namespace='/test')  

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
        subres = line.split(';')
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
  
@socketio.on('my_event', namespace='/test')
def test_message(message):   
    #session['receive_count'] = session.get('receive_count', 0) + 1 
    #session['A'] = message['value']   
    ser.write(bytes("##RLS#" + str(message['value']) + "#\n"))
    print("RLS set to: " + str(message['value']))
    #print(message['value'])
    #print(session['A'])
    #emit('my_response', {'data': message['value'], 'count': session['receive_count']})
    
@socketio.on('persistStart_request', namespace='/test')
def startPersist():   
    global persistEnabled, outfile
    outfile.close()
    outfile = open(r'./persist.txt',"a+") 
    #outfile.write("Session log - " + str(datetime.datetime.now()) + "\r\n")
    persistEnabled = True
    print("Persisting started")
    
@socketio.on('persistStop_request', namespace='/test')
def stopPersist():   
    global persistEnabled, outfile
    outfile.close()
    persistEnabled = False
    print("Persisting stopped")
    
 
@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    #session['receive_count'] = session.get('receive_count', 0) + 1
    #emit('my_response',{'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()
    #global persistEnabled, outfile
    #outfile.close()
    #persistEnabled = False

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())
    #emit('my_response', {'data': 'Connected', 'count': 0})

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
