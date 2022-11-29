from flask import Flask,render_template,request,flash,redirect,url_for
import os
import sqlite3
import os.path
from collections import OrderedDict
from random import random
import random
import sys

app=Flask(__name__)
app.secret_key="123"
global hit ,miss, hitRate ,missRate ,policyy ,totalSize ,capacity 
hit = 0
miss = 0
hitRate = 0
missRate = 0
policyy = '0' #lru
totalSize = 0
capacity = 11000000
memcache = OrderedDict()
##############################################################
con=sqlite3.connect("database.db")
cur = con.cursor()
con.execute("create table if not exists images(key integer primary key,img TEXT)")
cur.execute("create table if not exists cache (id integer primary key AUTOINCREMENT,policyy integer,hitRate double,missRate double,capacity double,items integer)")
app.config['UPLOAD_FOLDER']="static/images" #the path for images folder
path = '.\\static\\images\\'
#########################################################################
@app.route("/upload",methods=['GET','POST'])
def upload():
    global miss, hit, policyy, hitRate, missRate, memcache, totalSize
    con = sqlite3.connect("database.db")
    con.row_factory = sqlite3.Row #convert the tuple to an useful object
    cur = con.cursor()
    cur.execute("select * from images")
    data = cur.fetchall()
      #######################################
    if request.method=='POST':
        key= request.form['key']
        imgpath = request.form['path']
        upload_image=request.files['upload_image']
        if upload_image.filename!='':
            filepath=os.path.join(app.config['UPLOAD_FOLDER'],upload_image.filename)
            upload_image.save(filepath)
            print(filepath) #in static folder path
            print(imgpath) #original path
            sizebytes = os.stat(path + upload_image.filename).st_size
            totalSize = totalSize + sizebytes
            print(f'The size is', sizebytes, 'bytes')
            con=sqlite3.connect("database.db")
            cur=con.cursor()
            cur.execute("SELECT key FROM images WHERE key = ?", [key])
            isNewKey = len(cur.fetchall()) == 0 #boolean
            if(isNewKey) :
             cur.execute("INSERT INTO images (key,img) VALUES(?,?)",(key,upload_image.filename))
             con.commit()
             flash("Image Uploaded Successfully ","success")
            else :
             if(key in memcache.keys()):
              totalSize = totalSize - os.stat(path + upload_image.filename).st_size#remove oldsize
              del memcache[key]
             cur.execute("UPDATE images SET img = ? WHERE key = ?", (upload_image.filename,key))
             flash("Image Updated Successfully for the already exist key","success")
             con.commit()
######################################################################
#This part in necessary to be like this, to be able to view the images immeaditly after
#uploading the images
            con = sqlite3.connect("database.db")
            con.row_factory=sqlite3.Row
            cur=con.cursor()
            cur.execute("select * from images")
            data=cur.fetchall()
            return render_template("upload.html",data=data) #for the new uploaded images
    return render_template("upload.html",data=data) #the first if (else), to view the
    #already uploaded image
################################################################################
@app.route('/delete_record/<string:id>')
def delete_record(id):
    try:
        con=sqlite3.connect("database.db")
        cur=con.cursor()
        cur.execute("delete from images where key=?",[id])
        con.commit()
        flash("Record Deleted Successfully","success")
    except:
        flash("Record Deleted Failed", "danger")
    finally:
        return redirect(url_for("upload"))
#################################################################################
@app.route('/display',methods=["GET","POST"])
def display():
        global miss, hit, policyy, hitRate, missRate, memcache, totalSize, con, cur     
        if request.method == 'POST':
         con=sqlite3.connect("database.db")
         cur=con.cursor()
         key= request.form.get('key')
         print('key:', key)
         if key in memcache.keys():
          image = memcache[key]
          if policyy !='1': #not random
            LRU(key)
          print("from mem")
          hit = hit +1
          hitRate = ( hit / (hit + miss))*100
          missRate = (miss / (hit + miss))*100
          return render_template("displayimage.html",image = image )
         else:
          cur.execute("SELECT key FROM images WHERE key = ?", [key])
          isNewKey = len(cur.fetchall()) == 0 #boolean
          if(isNewKey):
           return("No image for this key")
          else: 
            result = cur.execute("SELECT img FROM images WHERE key = ? ",[key])
            result = (result.fetchall())
            miss = miss +1
            missRate = ( (miss / (hit+miss))) *100
            hitRate = (( hit / (hit + miss))) *100
            memcache[key]=result[0][0]
            if policyy == '1':
                randompolicy(key) 
            else:
             totalSize = totalSize + os.stat(path + memcache[key]).st_size
             LRU(key)   
            print("result",result)
            print("added to mem and displayed from db")
            print("totalSize now is ",totalSize)
            return render_template("displayimage.html",image = result[0][0])
      
        else:
         return render_template("displayimage.html")
        
###############################################################################
@app.route('/keys') 
def viewkeys():
  data=get_keys()
  return render_template('keys.html',keys=data)
def get_keys():
 con=sqlite3.connect("database.db")
 cur=con.cursor()
 cur.execute("SELECT key FROM images")
 keys=cur.fetchall()
 keys=[str(val[0]) for val in keys]
 return keys
###############################################################################
@app.route("/config",methods=['GET','POST']) 
def config():
    global  policyy,capacity,memcache
    if request.method=='POST':
     capacity= int(request.form["capacity"]) * 1000000
     policyy= request.form['policyy']
    # removekey= request.form['removekey']
     con=sqlite3.connect("database.db")
     cur=con.cursor()
     cur.execute("UPDATE cache SET capacity = ? , policyy= ?  WHERE id = 1", (capacity, policyy ))
     con.commit()
    return render_template('config.html')
##################################################################################
@app.route('/cacheinfo') 
def cacheinfo():
    global miss, hit, policyy, hitRate, missRate, memcache, totalSize, capacity
    return render_template('cacheinfo.html', fullSpace = capacity, hitRate = hitRate, missRate = missRate)
###################################################################################
def LRU(key) :
        global capacity, totalSize,path
        memcache.move_to_end(key)
        if totalSize > capacity:
            val=  list(memcache.keys())[0]
            totalSize = totalSize - os.stat(path + memcache[val]).st_size
            memcache.popitem(last = False)
            print("LRU key is ",val,"and now it's out")
        #print("done by lru with capacity = ",capacity)
#################################################################################
def randompolicy(key):
        global capacity, totalSize,path
        totalSize = totalSize + os.stat(path + memcache[key]).st_size
        if totalSize> capacity:
          old_key = random.choice(list(memcache.keys()))
          totalSize = totalSize - os.stat(path + memcache[old_key]).st_size
          del memcache[old_key]
          print("old key is ", old_key)  
        print("done from random")
#################################################################################
def ClearAll():
    global capacity, totalSize
    memcache.clear()
    totalSize = capacity
##################################################################################


@app.route('/home')  
def home():
 return render_template('home.html')

@app.route('/')  
def viewhome():
 return render_template('home.html')
#############################################
def insertCacheTableData() :
    global policyy, hitRate, missRate, capacity, memcache
    con = sqlite3.connect("database.db")
    cur = con.cursor()    
    cur.execute("INSERT INTO cache (policyy,hitRate,missRate,capacity,items) VALUES(?,?,?,?,?)",(policyy, hitRate, missRate, capacity, len(memcache)))
    con.commit()
    con.close()
    
def deleteDatabase() :
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("DELETE from cache")
    con.commit()
    con.close()
###########################################################
if __name__ == '__main__':
    app.run(debug=True)
