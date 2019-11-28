from flask import Flask, render_template, request, session, redirect, url_for, send_file, flash
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="",
                             db="finstagram",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return dec


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])


@app.route("/upload", methods=["GET"])
@login_required
def upload():
    user = session["username"]
    cursor = connection.cursor()
    closeFriendsGroupNameQuery = "SELECT DISTINCT groupName FROM belongto WHERE member_username = %s OR groupOwner =%s"
    cursor.execute(closeFriendsGroupNameQuery, (user, user))
    groups = cursor.fetchall()
    return render_template("upload.html", groups=groups)


@app.route("/images", methods=["GET"])
@login_required
def images():
    user = session["username"]
    try:
        cursor = connection.cursor()
        query = "DROP VIEW myphotos, mygroups, myfollows, allphotos"
        cursor.execute(query)
        cursor.close()
    except:
        pass
    # Query for photos of the people you follow
    cursor = connection.cursor()
    queryFollow = "CREATE VIEW myfollows AS SELECT DISTINCT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM photo JOIN follow ON (photo.photoPoster=username_followed) WHERE username_follower=%s AND allFollowers=%s"
    cursor.execute(queryFollow, (user, 1))
    cursor.close()

    # Query for photos of the people of the close friend groups that you are in
    cursor = connection.cursor()
    queryGroups = "CREATE VIEW mygroups AS SELECT DISTINCT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM photo NATURAL JOIN sharedwith NATURAL JOIN belongto WHERE member_username=%s"
    cursor.execute(queryGroups, (user))
    cursor.close()

    # Query for photos that the user posted
    cursor = connection.cursor()
    querySelf = "CREATE VIEW myphotos AS SELECT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM Photo WHERE photoPoster=%s"
    cursor.execute(querySelf, (user))
    cursor.close()

    #Query that prints additional picture info
    cursor = connection.cursor()
    totalQuery = "SELECT * FROM mygroups UNION (SELECT * FROM myphotos) UNION (SELECT * FROM myfollows) ORDER BY timestamp DESC"
    cursor.execute(totalQuery)
    data = cursor.fetchall()
    cursor.close()

    #adding user names for each poster
    for dict in data:
        cursor = connection.cursor()
        query = "SELECT fname, lname FROM person WHERE username=%s"
        cursor.execute(query,(dict["photoPoster"]))
        names = cursor.fetchall()
        cursor.close()
        dict["fname"]=names[0]['fname']
        dict["lname"]=names[0]['lname']


    # Query that drops the created views
    cursor = connection.cursor()
    query = "DROP VIEW myphotos, mygroups, myfollows"
    cursor.execute(query)
    cursor.close()


    # Query for getting all the tagged users of the photos
    cursor = connection.cursor()
    taggedquery = "SELECT * FROM tagged JOIN photo ON (tagged.photoID = photo.photoID) NATURAL JOIN person"
    cursor.execute(taggedquery)
    taggedUsers = cursor.fetchall()
    cursor.close()



    # Query for getting likes of photos
    cursor = connection.cursor()
    likesQuery = "SELECT username, photoID,rating FROM likes"
    cursor.execute(likesQuery)
    likes = cursor.fetchall()
    cursor.close()
    return render_template("images.html", photos=data, taggedUsers=taggedUsers, likes=likes)


@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")


@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]+"cs3083"
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]+"cs3083"
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]

        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")


@app.route("/uploadImage", methods=["GET","POST"])
@login_required
def upload_image():
    if request.files:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        requestData = request.form
        caption = requestData["caption"]
        user = session["username"]
        if request.form.get("visible"):
            visible = "1"
        else:
            visible = "0"
        query = "INSERT INTO photo (timestamp, filePath, photoPoster, caption, allFollowers ) VALUES (%s, %s, %s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, user, caption, visible))
        i=1
        while request.form.get(str(i)):
            if visible=="1":
                break
            group = request.form.get(str(i))
            # getting groupOwner
            cursor=connection.cursor()
            query = "SELECT groupOwner from belongto where groupName = %s and member_username = %s or groupOwner = %s"
            cursor.execute(query, (group,user,user))
            owner = cursor.fetchall()
            # getting photoID
            query = "SELECT photoID FROM photo where photoPoster = %s ORDER BY photoID DESC LIMIT 1;"
            cursor.execute(query,(user))
            id = cursor.fetchall()
            # inserting into Share
            query = "INSERT INTO sharedwith VALUES(%s,%s,%s)"
            cursor.execute(query, (str(group), str(owner[0]['groupOwner']), id[0]['photoID']))
            i += 1

        message = "Image has been successfully uploaded."
        cursor = connection.cursor()
        closeFriendsGroupNameQuery = "SELECT DISTINCT groupName FROM belongto WHERE member_username = %s OR groupOwner =%s"
        cursor.execute(closeFriendsGroupNameQuery, (user,user))
        groups = cursor.fetchall()
        return render_template("upload.html", error=message, groups=groups)
    else:
        message = "Failed to upload image."

@app.route("/like", methods=["GET","POST"])
@login_required
def like():
    if request.form:
        requestData = request.form
        user = session["username"]
        photoID = requestData["photoID"]
        rating = requestData["rating"]
        if rating not in ["0","1","2","3","4","5"]:
            flash("Enter a valid rating!")
            return redirect(url_for('images'))
        query = "SELECT username,photoID FROM likes WHERE username=%s AND photoID=%s"
        with connection.cursor() as cursor:
            cursor.execute(query,(user,photoID))
            data = cursor.fetchall()
            cursor.close()
        if len(data)==0:
            query = "INSERT INTO likes (username, photoID, liketime, rating) VALUES (%s, %s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(query, (user, photoID, time.strftime('%Y-%m-%d %H:%M:%S'), rating))
            return redirect(url_for('images'))
        else:
            query = "DELETE FROM likes WHERE username=%s AND photoID=%s"
            with connection.cursor() as cursor:
                cursor.execute(query, (user, photoID))
            query = "INSERT INTO likes (username, photoID, liketime, rating) VALUES (%s, %s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(query, (user, photoID, time.strftime('%Y-%m-%d %H:%M:%S'), rating))
            return redirect(url_for('images'))

    return render_template("images.html", username=session["username"])


if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()