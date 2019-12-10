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
            return redirect(url_for("index"))
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
    #execute query to get all the groups to which the current user belongs
    cursor = connection.cursor()
    closeFriendsGroupNameQuery = "SELECT DISTINCT groupName FROM belongto WHERE member_username = %s OR groupOwner =%s"
    cursor.execute(closeFriendsGroupNameQuery, (user, user))
    groups = cursor.fetchall()
    return render_template("upload.html", groups=groups)

@app.route("/followers", methods=["GET"])
@login_required
def followers():
    #Manage Follows and Unfollow use this func
    user = session["username"]
    #execute query to get all the followers of current user
    with connection.cursor() as cursor:
        query = "SELECT * FROM follow WHERE username_followed = %s"
        cursor.execute(query, (user))
    myFollowers = cursor.fetchall()
    #execute query to get all the users followed by current user
    with connection.cursor() as cursor:
        query = "SELECT * FROM follow WHERE username_follower = %s"
        cursor.execute(query,(user))
    following = cursor.fetchall()
    return render_template("followers.html", myFollowers=myFollowers, following=following)


@app.route("/addFollower", methods=["GET","POST"])
@login_required
def add_follower():
    #Manage follows uses this func
    user = session["username"]
    requestData = request.form
    followusername = requestData["followusername"]
    #check if the username that user wants to follow exists
    with connection.cursor() as cursor:
        query = "SELECT * FROM person WHERE username = %s"
        cursor.execute(query, (followusername))
    data = cursor.fetchone()
    #if user wants to follow themself, raise a flag
    if user==followusername:
        flag=1
    else:
        flag=0

    with connection.cursor() as cursor:
        query = "SELECT * FROM follow WHERE username_followed = %s"
        #execute query to get all followers of user, that user has accepted
        cursor.execute(query, (user))
        myFollowers = cursor.fetchall()
        num_followers = len(myFollowers)
    with connection.cursor() as cursor:
        query = "SELECT * FROM follow WHERE username_follower = %s"
        #execute query to get all usernames that user is following
        cursor.execute(query,(user))
        following = cursor.fetchall()
        num_following = len(following)
        cursor.execute(query, (user))
    if data and (flag==0):
        #if user entered a valid username
        with connection.cursor() as cursor:
            #check if the request already exists
            query = "SELECT * FROM follow WHERE username_followed=%s AND username_follower=%s"
            cursor.execute(query,(followusername,user))
            existing_request=cursor.fetchall()
            if existing_request and existing_request[0]['followstatus']==0:
                message= "Request already sent!"
            elif existing_request and existing_request[0]['followstatus']==1:
                message= "Following Already!"
            else:
                #otherwise insert into the follow table the usernames of the user as follower and the user to follow
                query = "INSERT INTO follow (username_followed, username_follower, followstatus) VALUES (%s, %s, %s)"
                cursor.execute(query, (followusername, user, 0))
                message = "Follow request sent!"
    elif flag==1:
        #if user wants to follow themselves
        message= "Enter a valid username"
    else:
        #entered a username that did not exist
        if followusername:
            message = "Enter a valid username"
        else:
            #user did not enter anything at all
            message=""

    #while loop to keep getting data from the checkboxes where followers have requested to follow the user
    i = 1
    while i<=num_followers:
        username_follower = request.form.get((str(i) + "A"))
        #if checkbox was marked, query to update the follow table row with a followstatus=1
        if username_follower:
            with connection.cursor() as cursor:
                query = "UPDATE follow SET followstatus = '1' WHERE follow.username_followed = %s AND follow.username_follower = %s"
                cursor.execute(query, ( user, username_follower))
        i += 1

    # while loop to keep getting data from the checkboxes where followers have requested to follow the user
    i = 1
    while i<=num_followers:
        username_follower = request.form.get((str(i) + "D"))
        # if checkbox was marked, query to delete from following table
        if username_follower:
            with connection.cursor() as cursor:
                query = "DELETE FROM follow WHERE username_followed = %s AND username_follower = %s"
                cursor.execute(query, (user, username_follower))
        i += 1

    # while loop to keep getting data from the checkboxes where followers are following a user
    i = 1
    while i<=num_following:
        username_followed = request.form.get((str(i) + "U"))
        # if checkbox was marked, query to delete from following table (to unfollow a following user)
        if username_followed:
            with connection.cursor() as cursor:
                query = "DELETE FROM follow WHERE username_followed = %s AND username_follower = %s"
                cursor.execute(query, (username_followed, user))
        i += 1

    # while loop to keep getting data from the checkboxes where followers are following a user
    i = 1
    while i<=num_following:
        requestData = request.form
        username_followed = request.form.get((str(i) + "F"))
        # if checkbox was marked, query to delete from following table (to cancel a sent request)
        if username_followed:
            with connection.cursor() as cursor:
                query = "DELETE FROM follow WHERE username_followed = %s AND username_follower = %s"
                cursor.execute(query, (username_followed, user))
        i += 1
    with connection.cursor() as cursor:
        query = "SELECT * FROM follow WHERE username_followed = %s"
        cursor.execute(query, (user))
        myFollowers = cursor.fetchall()
    with connection.cursor() as cursor:
        query = "SELECT * FROM follow WHERE username_follower = %s"
        cursor.execute(query,(user))
        following = cursor.fetchall()
    return render_template("followers.html", message=message, myFollowers=myFollowers, following=following)

@app.route("/groups", methods=["GET"])
@login_required
def groups():
    user = session["username"]
    with connection.cursor() as cursor:
        query = "SELECT * FROM friendgroup WHERE groupOwner=%s"
        cursor.execute(query, (user))
        groups = cursor.fetchall()
    return render_template("groups.html", groups=groups)

@app.route("/friendGroups",methods=["GET", "POST"])
@login_required
def friend_groups():
    user = session["username"]
    requestData = request.form
    groupNameC = requestData["groupNameC"]
    description = requestData["description"]
    if groupNameC:
        with connection.cursor() as cursor:
            query = "SELECT * FROM friendgroup WHERE groupOwner = %s AND groupName = %s"
            cursor.execute(query, (user, groupNameC))
            data = cursor.fetchall()
        if data:
            groupCreated = "Group Already Exists"
        else:
            with connection.cursor() as cursor:
                query = "INSERT INTO friendgroup (groupOwner, groupName, description) VALUES (%s, %s, %s)"
                cursor.execute(query, (user, groupNameC, description))
                query = "INSERT INTO belongto (member_username, groupOwner, groupName) VALUES (%s, %s, %s)"
                cursor.execute(query, (user, user, groupNameC))
                groupCreated = "Group Successfully Created!"

    with connection.cursor() as cursor:
        query = "SELECT * FROM friendgroup WHERE groupOwner=%s"
        cursor.execute(query, (user))
        groups = cursor.fetchall()
    return render_template("groups.html", groups=groups, groupCreated = groupCreated)

@app.route("/addFriend", methods=["GET", "POST"])
@login_required
def add_friend():
    user = session["username"]
    requestData = request.form
    groupName = requestData["groupName"]
    friend = requestData["friend"]
    with connection.cursor() as cursor:
        query = "SELECT * FROM person WHERE username = %s"
        cursor.execute(query, (friend))
    data = cursor.fetchone()
    if data:
        with connection.cursor() as cursor:
            query= "SELECT * FROM belongto WHERE groupOwner=%s AND groupName=%s AND member_username=%s"
            cursor.execute(query, (user, groupName, friend))
            data=cursor.fetchall()
            if data:
                userAdded = "User Already Belongs to the Selected Group!"
            else:
                with connection.cursor() as cursor:
                    query = "INSERT INTO belongto (groupOwner, groupName, member_username) VALUES (%s, %s, %s)"
                    print(groupName)
                    cursor.execute(query, (user, groupName, friend))
                    userAdded = "User Successfully Added to the Group!"
    else:
        userAdded = "No Such Username Exists!"
    with connection.cursor() as cursor:
        query = "SELECT * FROM friendgroup WHERE groupOwner=%s"
        cursor.execute(query, (user))
        groups = cursor.fetchall()
    return render_template("groups.html", groups = groups, userAdded = userAdded)
@app.route("/search", methods=["GET"])
@login_required
def search():
    return render_template("search.html")

@app.route("/searchImage", methods=["GET", "POST"])
@login_required
def search_image():
    user = session["username"]
    requestData=request.form
    photoPoster = requestData["photoPoster"]
    try:
        cursor = connection.cursor()
        query = "DROP VIEW myphotos, mygroups, myfollows"
        cursor.execute(query)
        cursor.close()
    except:
        pass
    # Query for photos of the people you follow
    cursor = connection.cursor()
    queryFollow = "CREATE VIEW myfollows AS SELECT DISTINCT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM photo JOIN follow ON (photo.photoPoster=username_followed) WHERE username_follower=%s AND allFollowers=%s AND photoPoster = %s AND followstatus=%s"
    cursor.execute(queryFollow, (user, "1", photoPoster, "1"))
    cursor.close()

    # Query for photos of the people of the close friend groups that you are in
    cursor = connection.cursor()
    queryGroups = "CREATE VIEW mygroups AS SELECT DISTINCT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM photo NATURAL JOIN sharedwith NATURAL JOIN belongto WHERE member_username=%s AND photoPoster = %s"
    cursor.execute(queryGroups, (user, photoPoster))
    cursor.close()

    if user==photoPoster:
        # Query for photos that the user posted
        cursor = connection.cursor()
        querySelf = "CREATE VIEW myphotos AS SELECT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM Photo WHERE photoPoster=%s"
        cursor.execute(querySelf, (user))
        cursor.close()
    else:
        cursor = connection.cursor()
        querySelf = "CREATE VIEW myphotos AS SELECT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM Photo WHERE photoPoster=%s"
        cursor.execute(querySelf, ("NULL"))
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

    #Query for getting comments of photos
    cursor=connection.cursor()
    commentQuery = "SELECT username, photoID, words FROM comment"
    cursor.execute(commentQuery)
    comments = cursor.fetchall()
    cursor.close()
    message = "Here are images posted by "+photoPoster+":"
    return render_template("search.html", photos=data, taggedUsers=taggedUsers, likes=likes, comments=comments, message=message)

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
    queryFollow = "CREATE VIEW myfollows AS SELECT DISTINCT photoID, timestamp, filepath, allFollowers, caption, photoPoster FROM photo JOIN follow ON (photo.photoPoster=username_followed) WHERE username_follower=%s AND allFollowers=%s AND followstatus=%s"
    cursor.execute(queryFollow, (user, "1", "1"))
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

    #Query for getting comments of photos
    cursor=connection.cursor()
    commentQuery = "SELECT username, photoID, words FROM comment"
    cursor.execute(commentQuery)
    comments = cursor.fetchall()
    cursor.close()

    return render_template("images.html", photos=data, taggedUsers=taggedUsers, likes=likes, comments=comments)


@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    #FROM THE TEMPLATE
    if request.form:
        requestData = request.form
        username = requestData["username"]
        #added salt as cs3083
        plaintextPasword = requestData["password"]+'cs3083'
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        message = "Incorrect username or password."
        return render_template("index.html", message=message)

    message = "An unknown error has occurred. Please try again."
    return render_template("index.html", message=message)


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    #FROM THE TEMPLATE
    if request.form:
        requestData = request.form
        username = requestData["username"]
        #Added salt as cs3083
        plaintextPasword = requestData["password"]+'cs3083'
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]

        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('index.html', error=error)
        error="User Successfully Registered!"
        return render_template("index.html", error=error)

    error = "An error has occurred. Please try again."
    return render_template("index.html", error=error)


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")


@app.route("/uploadImage", methods=["GET","POST"])
@login_required
def upload_image():
    user = session["username"]
    cursor = connection.cursor()
    closeFriendsGroupNameQuery = "SELECT DISTINCT groupName FROM belongto WHERE member_username = %s OR groupOwner =%s"
    cursor.execute(closeFriendsGroupNameQuery, (user, user))
    groups = cursor.fetchall()
    num_groups = len(groups)
    image_file = request.files.get("imageToUpload", "")
    if image_file:
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        requestData = request.form
        caption = requestData["caption"]
        #check if all followers selected or not
        if request.form.get("visible"):
            visible = "1"
        else:
            visible = "0"
        query = "INSERT INTO photo (timestamp, filePath, photoPoster, caption, allFollowers ) VALUES (%s, %s, %s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, user, caption, visible))

        i=1
        while i<=num_groups:
            #if all followers, no need to go over close friend groups
            if visible=="1":
                break
            group = request.form.get(str(i))
            if group:
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
                cursor.execute(query, (str(owner[0]['groupOwner']), str(group), id[0]['photoID']))
            i += 1

        message = "Image Successfully Uploaded."

        return render_template("upload.html", message=message, groups=groups)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message, groups=groups)

@app.route("/like", methods=["GET","POST"])
@login_required
def like():
    if request.form:
        requestData = request.form
        user = session["username"]
        photoID = requestData["photoID"]
        rating = requestData["rating"]
        #set appro[riate rating as 0,1,2,3,4,5
        if rating not in ["0","1","2","3","4","5"]:
            flash("Enter a valid rating!")
            return redirect(url_for('images'))
        query = "SELECT username,photoID FROM likes WHERE username=%s AND photoID=%s"
        with connection.cursor() as cursor:
            cursor.execute(query,(user,photoID))
            data = cursor.fetchall()
            cursor.close()
        #if did not have a like from before, just insert the new like rating
        if len(data)==0:
            query = "INSERT INTO likes (username, photoID, liketime, rating) VALUES (%s, %s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(query, (user, photoID, time.strftime('%Y-%m-%d %H:%M:%S'), rating))
            return redirect(url_for('images'))
        #had a like from before, delete previous rating and insert new rating
        else:
            query = "DELETE FROM likes WHERE username=%s AND photoID=%s"
            with connection.cursor() as cursor:
                cursor.execute(query, (user, photoID))
            query = "INSERT INTO likes (username, photoID, liketime, rating) VALUES (%s, %s, %s, %s)"
            with connection.cursor() as cursor:
                cursor.execute(query, (user, photoID, time.strftime('%Y-%m-%d %H:%M:%S'), rating))
            return redirect(url_for('images'))

    return render_template("images.html", username=session["username"])

@app.route("/comment", methods=["GET","POST"])
@login_required
def comment():
    if request.form:
        requestData=request.form
        user = session["username"]
        photoID=requestData["photoID"]
        #words is the comment typed
        words = requestData["words"]
        with connection.cursor() as cursor:
            #insert the data entered into the comments table
            query = "INSERT INTO comment (username, photoID, commenttime, words) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (user, photoID,time.strftime('%Y-%m-%d %H:%M:%S'), words ))
    return redirect(url_for('images'))


if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()